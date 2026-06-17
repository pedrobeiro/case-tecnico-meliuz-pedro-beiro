"""Interface Streamlit da aplicação de análise de cashback."""

from __future__ import annotations

import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ARQUIVO_ATUAL = Path(__file__).resolve()

if ARQUIVO_ATUAL.parent.name == "scripts":
    RAIZ_PROJETO = ARQUIVO_ATUAL.parent.parent
else:
    RAIZ_PROJETO = ARQUIVO_ATUAL.parent


if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(
        0,
        str(RAIZ_PROJETO),
    )


from scripts.integracao import Integracao
from scripts.llm_client import ErroComunicacaoLLM


PASTA_DADOS = (
    RAIZ_PROJETO
    / "data"
)

PASTA_SAIDA = (
    RAIZ_PROJETO
    / "outputs"
)

PASTA_UPLOADS = (
    PASTA_SAIDA
    / "uploads_temporarios"
)

PASTA_ASSETS = (
    RAIZ_PROJETO
    / "assets"
)

CAMINHO_LOGO = (
    PASTA_ASSETS
    / "logo_meliuz.png"
)

CAMINHO_HISTORICO = (
    PASTA_SAIDA
    / "acompanhamento_testes.csv"
)

URL_GOOGLE_SHEETS = (
    "https://docs.google.com/spreadsheets/d/"
    "1XggGi-xdwQ1WcOGQejSepJ9CXXuR4eYWv3kUAE_TDHM/"
    "edit?usp=sharing"
)


METRICAS = {
    "Compradores": "compradores",
    "Comissão": "comissao",
    "Cashback": "cashback",
    "Vendas totais": "vendas_totais",
    "Receita líquida": "receita_liquida",
    "Vendas por comprador": "vendas_por_comprador",
    "Comissão por comprador": "comissao_por_comprador",
    "Cashback por comprador": "cashback_por_comprador",
    "Receita líquida por comprador": (
        "receita_liquida_por_comprador"
    ),
    "Taxa de comissão": "taxa_comissao",
    "Taxa de cashback": "taxa_cashback",
    "Margem líquida": "margem_liquida",
}


NOMES_METRICAS = {
    valor: nome
    for nome, valor in METRICAS.items()
}


DESCRICOES_METRICAS = {
    "Compradores": (
        "Quantidade total de compradores."
    ),
    "Comissão": (
        "Comissão total recebida."
    ),
    "Cashback": (
        "Cashback total concedido."
    ),
    "Vendas totais": (
        "Valor total das vendas."
    ),
    "Receita líquida": (
        "Comissão menos cashback."
    ),
    "Vendas por comprador": (
        "Vendas totais divididas pelos compradores."
    ),
    "Comissão por comprador": (
        "Comissão dividida pelos compradores."
    ),
    "Cashback por comprador": (
        "Cashback dividido pelos compradores."
    ),
    "Receita líquida por comprador": (
        "Receita líquida dividida pelos compradores."
    ),
    "Taxa de comissão": (
        "Comissão dividida pelas vendas totais."
    ),
    "Taxa de cashback": (
        "Cashback dividido pelas vendas totais."
    ),
    "Margem líquida": (
        "Receita líquida dividida pelas vendas totais."
    ),
}


DESCRICOES_MODOS = {
    "Ranking": (
        "Compara os grupos usando uma métrica e um "
        "objetivo, ordenando os resultados e selecionando "
        "o grupo mais adequado ao critério."
    ),
    "Relatório geral": (
        "Apresenta uma visão consolidada das métricas de "
        "todos os grupos, sem selecionar um vencedor."
    ),
}


DESCRICOES_OBJETIVOS = {
    "Maximizar": (
        "Seleciona o grupo com o maior valor para a "
        "métrica escolhida."
    ),
    "Minimizar": (
        "Seleciona o grupo com o menor valor para a "
        "métrica escolhida."
    ),
}


METRICAS_MONETARIAS = {
    "comissao",
    "cashback",
    "vendas_totais",
    "receita_liquida",
    "vendas_por_comprador",
    "comissao_por_comprador",
    "cashback_por_comprador",
    "receita_liquida_por_comprador",
}


METRICAS_PERCENTUAIS = {
    "taxa_comissao",
    "taxa_cashback",
    "margem_liquida",
}


def configurar_pagina() -> None:
    """Configura a página e os estilos."""

    st.set_page_config(
        page_title="Analisador de Testes A/B",
        page_icon="📊",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1250px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .titulo-principal {
            font-size: 2.15rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .subtitulo-principal {
            color: #888888;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.12rem !important;
            line-height: 1.3 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            overflow-wrap: anywhere !important;
        }

        [data-testid="stMetricValue"] > div {
            font-size: 1.12rem !important;
            line-height: 1.3 !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            overflow-wrap: anywhere !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.76rem !important;
        }

        [data-testid="stMetric"] {
            min-height: 105px;
        }

        .nome-item-lateral {
            font-size: 0.91rem;
            font-weight: 650;
            margin-top: 0.85rem;
            margin-bottom: 0.12rem;
        }

        .descricao-item-lateral {
            color: #9a9a9a;
            font-size: 0.78rem;
            line-height: 1.35;
            margin-bottom: 0.35rem;
        }

        .autoria-lateral {
            color: #9a9a9a;
            font-size: 0.77rem;
            line-height: 1.35;
            margin-top: 0.35rem;
        }

        textarea {
            font-size: 0.95rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inicializar_estado() -> None:
    """Inicializa variáveis persistidas na sessão."""

    valores_padrao = {
        "resultado": None,
        "mostrar_formulario_manual": False,
        "erro_gemini": None,
        "pergunta_pendente": "",
        "arquivo_temporario": None,
        "confirmar_encerramento": False,
        "modo_manual": "Ranking",
    }

    for chave, valor in valores_padrao.items():
        if chave not in st.session_state:
            st.session_state[
                chave
            ] = valor


@st.cache_resource
def obter_integracao() -> Integracao:
    """Cria uma instância da integração."""

    return Integracao(
        pasta_dados=PASTA_DADOS,
        pasta_saida=PASTA_SAIDA,
        caminho_registro=CAMINHO_HISTORICO,
    )


def mostrar_cabecalho() -> None:
    """Mostra o título principal."""

    st.markdown(
        """
        <div class="titulo-principal">
            Analisador de Testes A/B de Cashback
        </div>

        <div class="subtitulo-principal">
            Envie uma solicitação em linguagem natural e/ou
            carregue um arquivo CSV para comparar as variantes
            do teste.
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_identificacao_lateral() -> None:
    """Mostra logo e autoria."""

    coluna_logo, coluna_texto = st.columns(
        [
            0.30,
            0.70,
        ],
        vertical_alignment="center",
    )

    with coluna_logo:
        if CAMINHO_LOGO.exists():
            st.image(
                str(
                    CAMINHO_LOGO
                ),
                width=62,
            )

        else:
            st.warning(
                "Logo não encontrado."
            )

    with coluna_texto:
        st.markdown(
            """
            <div class="autoria-lateral">
                Case técnico realizado por
                <strong>Pedro Moreira Beiro</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )


def mostrar_itens_laterais(
    itens: dict[str, str],
) -> None:
    """Mostra nomes e descrições na barra lateral."""

    for nome, descricao in itens.items():
        st.markdown(
            f"""
            <div class="nome-item-lateral">
                {nome}
            </div>

            <div class="descricao-item-lateral">
                {descricao}
            </div>
            """,
            unsafe_allow_html=True,
        )


def limpar_nome_arquivo(
    nome: str,
) -> str:
    """Remove caracteres inadequados do nome."""

    nome = Path(
        nome
    ).name

    nome = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        nome,
    )

    return (
        nome
        or "arquivo.csv"
    )


def salvar_upload_temporario(
    arquivo_enviado,
) -> Path | None:
    """Salva o upload em disco."""

    if arquivo_enviado is None:
        return None

    PASTA_UPLOADS.mkdir(
        parents=True,
        exist_ok=True,
    )

    nome_seguro = limpar_nome_arquivo(
        arquivo_enviado.name
    )

    identificador = uuid.uuid4().hex[
        :10
    ]

    caminho = (
        PASTA_UPLOADS
        / f"{identificador}_{nome_seguro}"
    )

    caminho.write_bytes(
        arquivo_enviado.getvalue()
    )

    return caminho


def remover_arquivo_temporario(
    caminho: str | Path | None,
) -> None:
    """Remove arquivo temporário."""

    if not caminho:
        return

    caminho = Path(
        caminho
    )

    try:
        if caminho.exists():
            caminho.unlink()

    except OSError:
        pass


def limpar_estado_analise() -> None:
    """Limpa o resultado da sessão."""

    remover_arquivo_temporario(
        st.session_state.get(
            "arquivo_temporario"
        )
    )

    st.session_state.resultado = None
    st.session_state.mostrar_formulario_manual = False
    st.session_state.erro_gemini = None
    st.session_state.pergunta_pendente = ""
    st.session_state.arquivo_temporario = None


def normalizar_grupo(
    grupo: Any,
) -> str:
    """Padroniza Grupo1 como Grupo 1."""

    texto = str(
        grupo
    ).strip()

    return re.sub(
        r"(?i)^grupo\s*(\d+)$",
        r"Grupo \1",
        texto,
    )


def formatar_moeda(
    valor: float | int,
) -> str:
    """Formata moeda no padrão brasileiro."""

    texto = f"{float(valor):,.2f}"

    texto = (
        texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {texto}"


def formatar_valor(
    metrica: str,
    valor: float | int | None,
) -> str:
    """Formata valor conforme a métrica."""

    if valor is None:
        return "Não disponível"

    if metrica in METRICAS_PERCENTUAIS:
        return (
            f"{float(valor) * 100:.2f}%"
            .replace(".", ",")
        )

    if metrica == "compradores":
        return (
            f"{int(round(float(valor))):,}"
            .replace(",", ".")
        )

    if metrica in METRICAS_MONETARIAS:
        return formatar_moeda(
            valor
        )

    return str(
        valor
    )


def executar_automaticamente(
    pergunta: str,
    arquivo_enviado,
) -> None:
    """Executa a análise usando o Gemini."""

    limpar_estado_analise()

    caminho_upload = salvar_upload_temporario(
        arquivo_enviado
    )

    st.session_state.arquivo_temporario = (
        str(
            caminho_upload
        )
        if caminho_upload is not None
        else None
    )

    st.session_state.pergunta_pendente = pergunta

    integracao = obter_integracao()

    with st.status(
        "Consultando o Gemini — tentativa 1/3",
        expanded=True,
    ) as status:

        def atualizar_tentativa(
            tentativa: int,
            total: int,
            etapa: str,
            codigo: int | None,
            espera: int | None,
        ) -> None:
            """Atualiza o indicador visual das tentativas."""

            if etapa == "iniciando":
                status.update(
                    label=(
                        "Consultando o Gemini — "
                        f"tentativa {tentativa}/{total}"
                    ),
                    state="running",
                )

            elif etapa == "aguardando":
                erro_texto = (
                    f"erro {codigo}"
                    if codigo is not None
                    else "falha de conexão"
                )

                status.write(
                    f"Tentativa {tentativa}/{total}: "
                    f"{erro_texto}. Nova tentativa em "
                    f"{espera} segundos."
                )

            elif etapa == "sucesso":
                status.update(
                    label=(
                        "Solicitação interpretada. "
                        "Analisando os dados..."
                    ),
                    state="running",
                )

            elif etapa in {
                "esgotado",
                "erro_definitivo",
            }:
                status.update(
                    label=(
                        "Não foi possível interpretar "
                        "a solicitação com o Gemini."
                    ),
                    state="error",
                )

        try:
            resultado = integracao.executar(
                pergunta=pergunta,
                arquivo_enviado=caminho_upload,
                callback_tentativa=atualizar_tentativa,
            )

            status.update(
                label="Análise concluída.",
                state="complete",
                expanded=False,
            )

            st.session_state.resultado = resultado
            st.session_state.mostrar_formulario_manual = False
            st.session_state.erro_gemini = None

            remover_arquivo_temporario(
                caminho_upload
            )

            st.session_state.arquivo_temporario = None

        except ErroComunicacaoLLM as erro:
            status.update(
                label=(
                    "Gemini indisponível. "
                    "Use a configuração manual abaixo."
                ),
                state="error",
                expanded=False,
            )

            st.session_state.resultado = None
            st.session_state.mostrar_formulario_manual = True
            st.session_state.erro_gemini = str(
                erro
            )

        except Exception:
            status.update(
                label="A análise foi interrompida.",
                state="error",
                expanded=False,
            )

            remover_arquivo_temporario(
                caminho_upload
            )

            st.session_state.arquivo_temporario = None

            raise


def executar_manualmente(
    modo: str,
    parceiro: str,
    metrica: str | None,
    direcao: str | None,
) -> None:
    """Executa a análise com parâmetros manuais."""

    integracao = obter_integracao()

    caminho_upload = st.session_state.get(
        "arquivo_temporario"
    )

    pergunta = st.session_state.get(
        "pergunta_pendente",
        "Consulta configurada manualmente.",
    )

    with st.status(
        "Executando a análise manual...",
        expanded=True,
    ) as status:
        resultado = integracao.executar_manual(
            pergunta=pergunta,
            modo=modo,
            parceiro=parceiro,
            metrica=metrica,
            direcao=direcao,
            arquivo_enviado=caminho_upload,
        )

        status.update(
            label="Análise concluída.",
            state="complete",
            expanded=False,
        )

    st.session_state.resultado = resultado
    st.session_state.mostrar_formulario_manual = False
    st.session_state.erro_gemini = None

    remover_arquivo_temporario(
        caminho_upload
    )

    st.session_state.arquivo_temporario = None


def mostrar_formulario_principal() -> None:
    """Mostra o formulário principal."""

    with st.form(
        "formulario_principal",
        clear_on_submit=False,
    ):
        pergunta = st.text_area(
            "Solicitação",
            placeholder=(
                "Exemplo: Qual grupo do Parceiro A deve ser "
                "escalado para maximizar as vendas totais?"
            ),
            height=120,
        )

        arquivo_enviado = st.file_uploader(
            "Arquivo CSV opcional",
            type=[
                "csv",
            ],
            help=(
                "Quando nenhum arquivo é enviado, o sistema "
                "procura o parceiro na pasta data."
            ),
        )

        executar = st.form_submit_button(
            "Executar análise",
            type="primary",
            width="stretch",
        )

    if executar:
        if not pergunta.strip():
            st.warning(
                "Digite uma solicitação antes de executar."
            )

            return

        try:
            executar_automaticamente(
                pergunta=pergunta.strip(),
                arquivo_enviado=arquivo_enviado,
            )

        except (
            ValueError,
            FileNotFoundError,
            RuntimeError,
        ) as erro:
            st.error(
                str(
                    erro
                )
            )

        except Exception as erro:
            st.error(
                "Ocorreu um erro inesperado durante a análise."
            )

            with st.expander(
                "Ver detalhe do erro"
            ):
                st.code(
                    f"{type(erro).__name__}: {erro}"
                )


def mostrar_formulario_manual() -> None:
    """Mostra o fallback manual após falha do Gemini."""

    if not st.session_state.mostrar_formulario_manual:
        return

    st.divider()

    st.error(
        "Não foi possível interpretar a solicitação com o Gemini."
    )

    if st.session_state.erro_gemini:
        with st.expander(
            "Ver erro retornado pela API"
        ):
            st.code(
                st.session_state.erro_gemini
            )

    st.info(
        "Selecione os parâmetros abaixo para continuar "
        "a análise sem depender da interpretação automática."
    )

    tipo_consulta = st.radio(
        "Tipo de consulta",
        options=[
            "Ranking",
            "Relatório geral",
        ],
        horizontal=True,
        key="modo_manual",
    )

    parceiro = st.selectbox(
        "Parceiro",
        options=[
            "Parceiro A",
            "Parceiro B",
            "Parceiro C",
        ],
        key="parceiro_manual",
    )

    metrica = None
    direcao = None

    if tipo_consulta == "Ranking":
        metrica_nome = st.selectbox(
            "Métrica",
            options=list(
                METRICAS.keys()
            ),
            key="metrica_manual",
        )

        direcao_nome = st.radio(
            "Objetivo",
            options=[
                "Maximizar",
                "Minimizar",
            ],
            horizontal=True,
            key="direcao_manual",
        )

        metrica = METRICAS[
            metrica_nome
        ]

        direcao = (
            "maximizar"
            if direcao_nome == "Maximizar"
            else "minimizar"
        )

    if st.button(
        "Executar com parâmetros manuais",
        type="primary",
        width="stretch",
    ):
        modo = (
            "ranking"
            if tipo_consulta == "Ranking"
            else "relatorio"
        )

        try:
            executar_manualmente(
                modo=modo,
                parceiro=parceiro,
                metrica=metrica,
                direcao=direcao,
            )

        except (
            ValueError,
            FileNotFoundError,
            RuntimeError,
        ) as erro:
            st.error(
                str(
                    erro
                )
            )

        except Exception as erro:
            st.error(
                "Ocorreu um erro inesperado durante "
                "a execução manual."
            )

            with st.expander(
                "Ver detalhe do erro"
            ):
                st.code(
                    f"{type(erro).__name__}: {erro}"
                )


def mostrar_resposta_natural(
    resultado: dict[str, Any],
) -> None:
    """Mostra a resposta final."""

    st.subheader(
        "Resultado da análise"
    )

    st.write(
        resultado.get(
            "resposta_natural",
            "A resposta final não foi gerada.",
        )
    )

    solicitacao = resultado.get(
        "solicitacao",
        {},
    )

    origem_interpretacao = solicitacao.get(
        "origem_interpretacao",
        "gemini",
    )

    origem_resposta = resultado.get(
        "origem_resposta_natural",
        "não identificada",
    )

    codigo_erro = resultado.get(
        "codigo_erro_resposta_natural"
    )

    nomes_origem = {
        "gemini": "Gemini",
        "manual": "Seleção manual",
        "local": "Resposta local",
        "fallback_local": "Resposta local",
    }

    texto_resposta = nomes_origem.get(
        origem_resposta,
        origem_resposta,
    )

    if (
        origem_resposta == "fallback_local"
        and codigo_erro is not None
    ):
        texto_resposta += (
            f" · erro {codigo_erro}"
        )

    st.caption(
        "Interpretação: "
        f"{nomes_origem.get(origem_interpretacao, origem_interpretacao)}"
        " · Resposta: "
        f"{texto_resposta}"
    )


def mostrar_resumo_ranking(
    resultado: dict[str, Any],
) -> None:
    """Mostra os indicadores do ranking."""

    resultado_base = resultado[
        "resultado_base"
    ]

    vencedor = resultado_base.get(
        "vencedor",
        {},
    )

    metrica = resultado_base.get(
        "metrica",
        "",
    )

    parceiro = resultado_base.get(
        "parceiro",
        "Não identificado",
    )

    grupo = normalizar_grupo(
        vencedor.get(
            "grupo",
            "Não identificado",
        )
    )

    valor = formatar_valor(
        metrica=metrica,
        valor=vencedor.get(
            "valor"
        ),
    )

    colunas = st.columns(
        4
    )

    colunas[0].metric(
        "Parceiro",
        parceiro,
    )

    colunas[1].metric(
        "Grupo selecionado",
        grupo,
    )

    colunas[2].metric(
        "Métrica",
        NOMES_METRICAS.get(
            metrica,
            metrica.replace(
                "_",
                " ",
            ).title(),
        ),
    )

    colunas[3].metric(
        "Resultado",
        valor,
    )


def mostrar_resumo_relatorio(
    resultado: dict[str, Any],
) -> None:
    """Mostra indicadores da consulta geral."""

    resultado_base = resultado[
        "resultado_base"
    ]

    parceiro = resultado_base.get(
        "parceiro",
        "Não identificado",
    )

    quantidade_grupos = resultado_base.get(
        "quantidade_grupos",
        0,
    )

    arquivo = resultado.get(
        "registro",
        {},
    ).get(
        "linha",
        {},
    ).get(
        "Arquivo",
        "Não identificado",
    )

    relatorio_validacao = resultado.get(
        "relatorio_validacao",
        {},
    )

    linhas_validas = (
        relatorio_validacao.get(
            "linhas_finais"
        )
        or "Não informado"
    )

    colunas = st.columns(
        4
    )

    colunas[0].metric(
        "Parceiro",
        parceiro,
    )

    colunas[1].metric(
        "Grupos analisados",
        quantidade_grupos,
    )

    colunas[2].metric(
        "Arquivo",
        arquivo,
    )

    colunas[3].metric(
        "Linhas válidas",
        linhas_validas,
    )


def mostrar_warnings(
    resultado: dict[str, Any],
) -> None:
    """Exibe os alertas."""

    resultado_warnings = resultado.get(
        "resultado_warnings"
    )

    st.subheader(
        "Alertas"
    )

    if not resultado_warnings:
        st.info(
            "A consulta geral não gera alertas de decisão."
        )

        return

    warnings = resultado_warnings.get(
        "warnings",
        [],
    )

    if not warnings:
        st.success(
            "Nenhum alerta foi identificado para o grupo selecionado."
        )

        return

    for warning in warnings:
        mensagem = warning.get(
            "mensagem",
            "Alerta sem descrição.",
        )

        if warning.get(
            "nivel"
        ) == "critico":
            st.error(
                f"CRÍTICO — {mensagem}"
            )

        else:
            st.warning(
                f"ATENÇÃO — {mensagem}"
            )


def mostrar_ranking(
    resultado: dict[str, Any],
) -> None:
    """Mostra a tabela de ranking."""

    resultado_base = resultado[
        "resultado_base"
    ]

    if resultado_base.get(
        "modo"
    ) != "ranking":
        return

    st.subheader(
        "Ranking dos grupos"
    )

    metrica = resultado_base.get(
        "metrica",
        "",
    )

    linhas = []

    for item in resultado_base.get(
        "ranking",
        [],
    ):
        linhas.append(
            {
                "Posição": item.get(
                    "posicao"
                ),
                "Grupo": normalizar_grupo(
                    item.get(
                        "grupo"
                    )
                ),
                "Valor": formatar_valor(
                    metrica,
                    item.get(
                        "valor"
                    ),
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(
            linhas
        ),
        hide_index=True,
        width="stretch",
    )


def mostrar_metricas_relatorio(
    resultado: dict[str, Any],
) -> None:
    """Mostra métricas da consulta geral."""

    resultado_base = resultado[
        "resultado_base"
    ]

    if resultado_base.get(
        "modo"
    ) != "relatorio":
        return

    st.subheader(
        "Métricas consolidadas"
    )

    linhas = []

    for grupo, conteudo in resultado_base.get(
        "resultados_grupos",
        {},
    ).items():
        metricas = conteudo.get(
            "metricas",
            {},
        )

        linhas.append(
            {
                "Grupo": normalizar_grupo(
                    grupo
                ),
                "Compradores": formatar_valor(
                    "compradores",
                    metricas.get(
                        "compradores"
                    ),
                ),
                "Vendas totais": formatar_valor(
                    "vendas_totais",
                    metricas.get(
                        "vendas_totais"
                    ),
                ),
                "Receita líquida": formatar_valor(
                    "receita_liquida",
                    metricas.get(
                        "receita_liquida"
                    ),
                ),
                "Margem líquida": formatar_valor(
                    "margem_liquida",
                    metricas.get(
                        "margem_liquida"
                    ),
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(
            linhas
        ),
        hide_index=True,
        width="stretch",
    )

def mostrar_status_registros(
    resultado: dict[str, Any],
) -> None:
    """Mostra o registro local e a sincronização remota."""

    st.subheader(
        "Registros e sincronização"
    )

    coluna_local, coluna_sheets = st.columns(
        2
    )

    registro_local = resultado.get(
        "registro",
        {},
    )

    linha_local = registro_local.get(
        "linha",
        {},
    )

    caminho_local = registro_local.get(
        "arquivo",
        str(
            CAMINHO_HISTORICO
        ),
    )

    with coluna_local:
        with st.container(
            border=True
        ):
            st.caption(
                "Registro local"
            )

            if linha_local:
                st.success(
                    "Concluído",
                    icon="✅",
                )

                st.write(
                    "A análise foi adicionada ao "
                    "histórico local."
                )

                if caminho_local:
                    st.caption(
                        "Arquivo: "
                        f"{Path(caminho_local).name}"
                    )

            else:
                st.warning(
                    "Não confirmado",
                    icon="⚠️",
                )

                st.write(
                    "A aplicação não retornou os dados "
                    "do registro local."
                )

    registro_sheets = resultado.get(
        "registro_google_sheets",
        {},
    )

    configurado = registro_sheets.get(
        "configurado",
        False,
    )

    sincronizado = registro_sheets.get(
        "sincronizado",
        False,
    )

    mensagem = registro_sheets.get(
        "mensagem",
        "",
    )

    codigo_http = registro_sheets.get(
        "codigo_http"
    )

    linha_sheets = registro_sheets.get(
        "linha"
    )

    aba_sheets = registro_sheets.get(
        "aba"
    )

    status_interno = registro_sheets.get(
        "status"
    )

    with coluna_sheets:
        with st.container(
            border=True
        ):
            st.caption(
                "Google Sheets"
            )

            if sincronizado:
                st.success(
                    "Sincronizado",
                    icon="✅",
                )

                if mensagem:
                    st.write(
                        mensagem
                    )

                detalhes = []

                if aba_sheets:
                    detalhes.append(
                        f"Aba: {aba_sheets}"
                    )

                if linha_sheets is not None:
                    detalhes.append(
                        f"Linha inserida: {linha_sheets}"
                    )

                if detalhes:
                    st.caption(
                        " · ".join(
                            detalhes
                        )
                    )

            elif not configurado:
                st.warning(
                    "Não configurado",
                    icon="⚠️",
                )

                st.write(
                    mensagem
                    or (
                        "A URL e o token do webhook "
                        "não foram configurados."
                    )
                )

            else:
                st.error(
                    "Não sincronizado",
                    icon="❌",
                )

                st.write(
                    mensagem
                    or (
                        "O registro remoto não "
                        "foi concluído."
                    )
                )

                detalhes = []

                if codigo_http is not None:
                    detalhes.append(
                        f"Código HTTP: {codigo_http}"
                    )

                if status_interno:
                    detalhes.append(
                        f"Status: {status_interno}"
                    )

                if detalhes:
                    st.caption(
                        " · ".join(
                            detalhes
                        )
                    )

    st.link_button(
        "Abrir planilha no Google Sheets",
        URL_GOOGLE_SHEETS,
        type="secondary",
        icon=":material/open_in_new:",
        width="stretch",
    )

def mostrar_downloads(
    resultado: dict[str, Any],
) -> None:
    """Disponibiliza arquivos para download."""

    st.subheader(
        "Arquivos"
    )

    colunas = st.columns(
        2
    )

    caminho_relatorio = Path(
        resultado.get(
            "caminho_relatorio",
            "",
        )
    )

    if caminho_relatorio.exists():
        colunas[0].download_button(
            label="Baixar relatório HTML",
            data=caminho_relatorio.read_bytes(),
            file_name=caminho_relatorio.name,
            mime="text/html",
            width="stretch",
        )

    else:
        colunas[0].warning(
            "O relatório HTML não foi encontrado."
        )

    caminho_historico = Path(
        resultado.get(
            "registro",
            {},
        ).get(
            "arquivo",
            CAMINHO_HISTORICO,
        )
    )

    if caminho_historico.exists():
        colunas[1].download_button(
            label="Baixar histórico CSV",
            data=caminho_historico.read_bytes(),
            file_name=caminho_historico.name,
            mime="text/csv",
            width="stretch",
        )

    else:
        colunas[1].warning(
            "O histórico não foi encontrado."
        )


def mostrar_detalhes_tecnicos(
    resultado: dict[str, Any],
) -> None:
    """Mostra detalhes técnicos."""

    with st.expander(
        "Ver detalhes técnicos"
    ):
        abas = st.tabs(
            [
                "Solicitação",
                "Validação",
                "Resultado",
                "Warnings",
                "Registro local",
                "Google Sheets",
            ]
        )

        with abas[0]:
            st.json(
                resultado.get(
                    "solicitacao",
                    {},
                )
            )

        with abas[1]:
            st.json(
                resultado.get(
                    "relatorio_validacao",
                    {},
                )
            )

        with abas[2]:
            st.json(
                resultado.get(
                    "resultado_base",
                    {},
                )
            )

        with abas[3]:
            st.json(
                resultado.get(
                    "resultado_warnings"
                )
            )

        with abas[4]:
            st.json(
                resultado.get(
                    "registro",
                    {},
                )
            )

        with abas[5]:
            st.json(
                resultado.get(
                    "registro_google_sheets",
                    {},
                )
            )


def mostrar_resultado() -> None:
    """Exibe o resultado da sessão."""

    resultado = st.session_state.get(
        "resultado"
    )

    if resultado is None:
        return

    st.divider()

    mostrar_resposta_natural(
        resultado
    )

    modo = resultado.get(
        "resultado_base",
        {},
    ).get(
        "modo"
    )

    if modo == "ranking":
        mostrar_resumo_ranking(
            resultado
        )

    else:
        mostrar_resumo_relatorio(
            resultado
        )

    st.divider()

    mostrar_warnings(
        resultado
    )

    if modo == "ranking":
        mostrar_ranking(
            resultado
        )

    else:
        mostrar_metricas_relatorio(
            resultado
        )

    st.divider()

    mostrar_status_registros(
        resultado
    )

    mostrar_downloads(
        resultado
    )

    mostrar_detalhes_tecnicos(
        resultado
    )

    st.divider()

    if st.button(
        "Nova análise",
        width="stretch",
    ):
        limpar_estado_analise()
        st.rerun()


def encerrar_servidor() -> None:
    """Encerra o servidor Streamlit."""

    remover_arquivo_temporario(
        st.session_state.get(
            "arquivo_temporario"
        )
    )

    st.warning(
        "Encerrando a aplicação..."
    )

    time.sleep(
        0.8
    )

    os._exit(
        0
    )


def mostrar_controle_encerramento() -> None:
    """Mostra controle de encerramento."""

    st.divider()

    if not st.session_state.confirmar_encerramento:
        if st.button(
            "Encerrar aplicação",
            width="stretch",
        ):
            st.session_state.confirmar_encerramento = True
            st.rerun()

        return

    st.warning(
        "Isso encerrará o servidor local."
    )

    coluna_confirmar, coluna_cancelar = st.columns(
        2
    )

    if coluna_confirmar.button(
        "Confirmar",
        type="primary",
        width="stretch",
    ):
        encerrar_servidor()

    if coluna_cancelar.button(
        "Cancelar",
        width="stretch",
    ):
        st.session_state.confirmar_encerramento = False
        st.rerun()


def mostrar_barra_lateral() -> None:
    """Mostra informações na barra lateral."""

    with st.sidebar:
        mostrar_identificacao_lateral()

        st.divider()

        st.header(
            "Como usar"
        )

        st.write(
            "Digite uma pergunta em linguagem natural "
            "e/ou carregue um arquivo CSV."
        )

        st.markdown(
            """
            **Exemplos**

            - Qual grupo do Parceiro A maximiza as vendas totais?
            - Qual grupo do Parceiro B minimiza a taxa de cashback?
            - Mostre o relatório geral do Parceiro C.
            """
        )

        st.divider()

        st.subheader(
            "Modos de análise"
        )

        mostrar_itens_laterais(
            DESCRICOES_MODOS
        )

        st.divider()

        st.subheader(
            "Objetivos"
        )

        mostrar_itens_laterais(
            DESCRICOES_OBJETIVOS
        )

        st.divider()

        st.subheader(
            "Métricas disponíveis"
        )

        mostrar_itens_laterais(
            DESCRICOES_METRICAS
        )

        st.divider()

        st.caption(
            "Quando o Gemini estiver indisponível, "
            "a aplicação permite selecionar os parâmetros "
            "manualmente."
        )

        st.link_button(
            "Abrir histórico no Google Sheets",
            URL_GOOGLE_SHEETS,
            icon=":material/table_view:",
            width="stretch",
        )

        mostrar_controle_encerramento()


def main() -> None:
    """Executa a interface."""

    configurar_pagina()
    inicializar_estado()
    mostrar_barra_lateral()
    mostrar_cabecalho()
    mostrar_formulario_principal()
    mostrar_formulario_manual()
    mostrar_resultado()


if __name__ == "__main__":
    main()