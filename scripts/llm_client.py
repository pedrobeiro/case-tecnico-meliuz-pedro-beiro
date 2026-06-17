"""Interpretação de solicitações em linguagem natural usando Gemini."""

from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Callable, Literal

import pandas as pd
from dotenv import load_dotenv
import google.genai as genai
from google.genai import errors
from google.genai import types
from pydantic import BaseModel, model_validator


MetricasDisponiveis = Literal[
    "compradores",
    "comissao",
    "cashback",
    "vendas_totais",
    "receita_liquida",
    "vendas_por_comprador",
    "comissao_por_comprador",
    "cashback_por_comprador",
    "receita_liquida_por_comprador",
    "taxa_comissao",
    "taxa_cashback",
    "margem_liquida",
]


CallbackTentativa = Callable[
    [
        int,
        int,
        str,
        int | None,
        int | None,
    ],
    None,
]


class ErroComunicacaoLLM(RuntimeError):
    """Erro de comunicação ou acesso à API do Gemini."""

    def __init__(
        self,
        mensagem: str,
        codigo: int | None = None,
        detalhe: str | None = None,
    ) -> None:
        super().__init__(
            mensagem
        )

        self.codigo = codigo
        self.detalhe = detalhe

    def __str__(self) -> str:
        partes = [
            super().__str__()
        ]

        if self.codigo is not None:
            partes.append(
                f"Código do erro: {self.codigo}."
            )

        if self.detalhe:
            partes.append(
                f"Detalhe: {self.detalhe}"
            )

        return " ".join(
            partes
        )


class SolicitacaoAnalise(BaseModel):
    """Estrutura extraída da pergunta pela LLM."""

    modo: Literal[
        "ranking",
        "relatorio",
    ]

    metrica: MetricasDisponiveis | None = None

    direcao: Literal[
        "maximizar",
        "minimizar",
    ] | None = None

    parceiro: str | None = None
    arquivo: str | None = None

    @model_validator(mode="after")
    def ajustar_relatorio(
        self,
    ) -> "SolicitacaoAnalise":
        """Remove métrica e direção de consultas gerais."""

        if self.modo == "relatorio":
            self.metrica = None
            self.direcao = None

        return self


class ClienteLLM:
    """Interpreta perguntas com Gemini e localiza o CSV."""

    METRICAS = {
        "compradores": (
            "quantidade total de compradores"
        ),
        "comissao": (
            "comissão total recebida pelo parceiro"
        ),
        "cashback": (
            "cashback total concedido aos usuários"
        ),
        "vendas_totais": (
            "valor total das vendas"
        ),
        "receita_liquida": (
            "comissão menos cashback"
        ),
        "vendas_por_comprador": (
            "vendas totais divididas pelos compradores"
        ),
        "comissao_por_comprador": (
            "comissão dividida pelos compradores"
        ),
        "cashback_por_comprador": (
            "cashback dividido pelos compradores"
        ),
        "receita_liquida_por_comprador": (
            "receita líquida dividida pelos compradores"
        ),
        "taxa_comissao": (
            "comissão dividida pelas vendas totais"
        ),
        "taxa_cashback": (
            "cashback dividido pelas vendas totais"
        ),
        "margem_liquida": (
            "receita líquida dividida pelas vendas totais"
        ),
    }

    NOMES_METRICAS = {
        "compradores": "compradores",
        "comissao": "comissão",
        "cashback": "cashback",
        "vendas_totais": "vendas totais",
        "receita_liquida": "receita líquida",
        "vendas_por_comprador": "vendas por comprador",
        "comissao_por_comprador": "comissão por comprador",
        "cashback_por_comprador": "cashback por comprador",
        "receita_liquida_por_comprador": (
            "receita líquida por comprador"
        ),
        "taxa_comissao": "taxa de comissão",
        "taxa_cashback": "taxa de cashback",
        "margem_liquida": "margem líquida",
    }

    PARCEIROS_VALIDOS = {
        "a": "Parceiro A",
        "b": "Parceiro B",
        "c": "Parceiro C",
    }

    CODIGOS_TEMPORARIOS = {
        429,
        500,
        502,
        503,
        504,
    }

    MAXIMO_TENTATIVAS = 3

    def __init__(
        self,
        api_key: str | None = None,
        modelo: str | None = None,
        cliente=None,
    ) -> None:
        """Inicializa o cliente Gemini."""

        raiz = Path(__file__).resolve().parent.parent

        load_dotenv(
            raiz / ".env"
        )

        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        self.modelo = (
            modelo
            or os.getenv(
                "GEMINI_MODEL",
                "gemini-2.5-flash",
            )
        )

        if cliente is not None:
            self.cliente = cliente
            return

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY não foi configurada."
            )

        self.cliente = genai.Client(
            api_key=self.api_key
        )

    def executar(
        self,
        pergunta: str,
        arquivo_enviado: str | Path | None = None,
        pasta_dados: str | Path = "data",
        callback_tentativa: CallbackTentativa | None = None,
    ) -> dict:
        """Interpreta a pergunta e determina o CSV."""

        if not pergunta or not pergunta.strip():
            raise ValueError(
                "A pergunta não pode estar vazia."
            )

        solicitacao = self.interpretar(
            pergunta=pergunta.strip(),
            callback_tentativa=callback_tentativa,
        )

        if solicitacao.parceiro is not None:
            solicitacao.parceiro = (
                self.normalizar_parceiro(
                    solicitacao.parceiro
                )
            )

        self.validar_solicitacao(
            solicitacao
        )

        caminho_arquivo = self.definir_arquivo(
            solicitacao=solicitacao,
            arquivo_enviado=arquivo_enviado,
            pasta_dados=pasta_dados,
        )

        resultado = solicitacao.model_dump()

        resultado["pergunta"] = pergunta.strip()

        resultado["caminho_arquivo"] = str(
            caminho_arquivo.resolve()
        )

        return resultado

    def interpretar(
        self,
        pergunta: str,
        callback_tentativa: CallbackTentativa | None = None,
    ) -> SolicitacaoAnalise:
        """Converte a pergunta em parâmetros estruturados."""

        prompt = (
            f"{self.criar_prompt_sistema()}\n\n"
            f"Solicitação do usuário:\n"
            f"{pergunta}"
        )

        resposta = self.gerar_conteudo_com_tentativas(
            prompt=prompt,
            callback_tentativa=callback_tentativa,
        )

        if not resposta.text:
            raise ValueError(
                "A LLM não retornou conteúdo."
            )

        try:
            return SolicitacaoAnalise.model_validate_json(
                resposta.text
            )

        except Exception as erro:
            raise ValueError(
                "A LLM retornou uma solicitação inválida. "
                f"Conteúdo recebido: {resposta.text}"
            ) from erro

    def gerar_conteudo_com_tentativas(
        self,
        prompt: str,
        callback_tentativa: CallbackTentativa | None = None,
    ):
        """Consulta o Gemini e repete falhas temporárias."""

        ultimo_erro: Exception | None = None
        ultimo_codigo: int | None = None

        for tentativa in range(
            1,
            self.MAXIMO_TENTATIVAS + 1,
        ):
            self.notificar_tentativa(
                callback=callback_tentativa,
                tentativa=tentativa,
                etapa="iniciando",
                codigo=None,
                espera=None,
            )

            try:
                resposta = self.cliente.models.generate_content(
                    model=self.modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=SolicitacaoAnalise,
                        temperature=0,
                    ),
                )

                self.notificar_tentativa(
                    callback=callback_tentativa,
                    tentativa=tentativa,
                    etapa="sucesso",
                    codigo=None,
                    espera=None,
                )

                return resposta

            except errors.APIError as erro:
                ultimo_erro = erro
                ultimo_codigo = self.obter_codigo_erro(
                    erro
                )

                if (
                    ultimo_codigo
                    not in self.CODIGOS_TEMPORARIOS
                ):
                    self.notificar_tentativa(
                        callback=callback_tentativa,
                        tentativa=tentativa,
                        etapa="erro_definitivo",
                        codigo=ultimo_codigo,
                        espera=None,
                    )

                    raise ErroComunicacaoLLM(
                        mensagem=(
                            "Não foi possível acessar "
                            "o Gemini."
                        ),
                        codigo=ultimo_codigo,
                        detalhe=str(erro),
                    ) from erro

                if tentativa == self.MAXIMO_TENTATIVAS:
                    self.notificar_tentativa(
                        callback=callback_tentativa,
                        tentativa=tentativa,
                        etapa="esgotado",
                        codigo=ultimo_codigo,
                        espera=None,
                    )

                    break

                espera = self.calcular_espera(
                    codigo=ultimo_codigo,
                    tentativa=tentativa,
                )

                self.notificar_tentativa(
                    callback=callback_tentativa,
                    tentativa=tentativa,
                    etapa="aguardando",
                    codigo=ultimo_codigo,
                    espera=espera,
                )

                print(
                    "\nFalha temporária na comunicação "
                    "com o Gemini."
                )

                print(
                    f"Código recebido: {ultimo_codigo}"
                )

                print(
                    f"Nova tentativa em {espera} segundos "
                    f"({tentativa + 1}/"
                    f"{self.MAXIMO_TENTATIVAS})..."
                )

                time.sleep(
                    espera
                )

            except (
                ConnectionError,
                TimeoutError,
            ) as erro:
                ultimo_erro = erro
                ultimo_codigo = None

                if tentativa == self.MAXIMO_TENTATIVAS:
                    self.notificar_tentativa(
                        callback=callback_tentativa,
                        tentativa=tentativa,
                        etapa="esgotado",
                        codigo=None,
                        espera=None,
                    )

                    break

                espera = 5 * tentativa

                self.notificar_tentativa(
                    callback=callback_tentativa,
                    tentativa=tentativa,
                    etapa="aguardando",
                    codigo=None,
                    espera=espera,
                )

                print(
                    "\nFalha de conexão com o Gemini."
                )

                print(
                    f"Nova tentativa em {espera} segundos "
                    f"({tentativa + 1}/"
                    f"{self.MAXIMO_TENTATIVAS})..."
                )

                time.sleep(
                    espera
                )

        raise ErroComunicacaoLLM(
            mensagem=(
                "O Gemini permaneceu indisponível "
                "após várias tentativas."
            ),
            codigo=ultimo_codigo,
            detalhe=(
                str(ultimo_erro)
                if ultimo_erro is not None
                else None
            ),
        ) from ultimo_erro

    def notificar_tentativa(
        self,
        callback: CallbackTentativa | None,
        tentativa: int,
        etapa: str,
        codigo: int | None,
        espera: int | None,
    ) -> None:
        """Informa o andamento para a interface."""

        if callback is None:
            return

        try:
            callback(
                tentativa,
                self.MAXIMO_TENTATIVAS,
                etapa,
                codigo,
                espera,
            )

        except Exception:
            # Uma falha visual não pode interromper a análise.
            pass

    def calcular_espera(
        self,
        codigo: int | None,
        tentativa: int,
    ) -> int:
        """Define esperas diferentes para 429 e 5xx."""

        if codigo == 429:
            esperas = {
                1: 5,
                2: 10,
            }

            return esperas.get(
                tentativa,
                15,
            )

        esperas = {
            1: 2,
            2: 5,
        }

        return esperas.get(
            tentativa,
            10,
        )

    def obter_codigo_erro(
        self,
        erro: Exception,
    ) -> int | None:
        """Obtém o código HTTP disponível no erro."""

        codigo = getattr(
            erro,
            "code",
            None,
        )

        if codigo is None:
            codigo = getattr(
                erro,
                "status_code",
                None,
            )

        try:
            return int(
                codigo
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    def validar_solicitacao(
        self,
        solicitacao: SolicitacaoAnalise,
    ) -> None:
        """Verifica se a solicitação possui dados suficientes."""

        if solicitacao.modo == "relatorio":
            return

        if solicitacao.metrica is None:
            raise ValueError(
                "Não foi possível identificar qual métrica "
                "deve ser analisada.\n\n"
                f"{self.listar_metricas_disponiveis()}"
            )

        if solicitacao.direcao is None:
            raise ValueError(
                "Não foi possível identificar o objetivo "
                "da análise.\n\n"
                "Opções disponíveis:\n"
                "- maximizar: selecionar o maior valor;\n"
                "- minimizar: selecionar o menor valor."
            )

    def normalizar_parceiro(
        self,
        parceiro: str,
    ) -> str:
        """Padroniza referências aos parceiros A, B e C."""

        parceiro_normalizado = self.normalizar_texto(
            parceiro
        )

        padrao = re.fullmatch(
            r"(?:(?:parceiro|grupo)\s*)?([abc])",
            parceiro_normalizado,
        )

        if padrao:
            return self.PARCEIROS_VALIDOS[
                padrao.group(1)
            ]

        raise ValueError(
            f"O parceiro '{parceiro}' não foi reconhecido.\n\n"
            "Parceiros disponíveis:\n"
            "- Parceiro A\n"
            "- Parceiro B\n"
            "- Parceiro C"
        )

    def listar_metricas_disponiveis(
        self,
    ) -> str:
        """Retorna uma lista legível das métricas."""

        linhas = [
            "Métricas disponíveis:"
        ]

        for metrica, nome in (
            self.NOMES_METRICAS.items()
        ):
            linhas.append(
                f"- {nome}: {self.METRICAS[metrica]};"
            )

        return "\n".join(
            linhas
        )

    def definir_arquivo(
        self,
        solicitacao: SolicitacaoAnalise,
        arquivo_enviado: str | Path | None,
        pasta_dados: str | Path,
    ) -> Path:
        """Define qual CSV será utilizado."""

        if arquivo_enviado is not None:
            caminho = Path(
                arquivo_enviado
            )

            if not caminho.exists():
                raise FileNotFoundError(
                    "Arquivo enviado não encontrado: "
                    f"{caminho}"
                )

            if caminho.suffix.lower() != ".csv":
                raise ValueError(
                    "O arquivo enviado deve possuir "
                    "extensão .csv."
                )

            return caminho

        pasta_dados = Path(
            pasta_dados
        )

        if not pasta_dados.exists():
            raise FileNotFoundError(
                "Pasta de dados não encontrada: "
                f"{pasta_dados}"
            )

        if solicitacao.arquivo:
            caminho = self.localizar_por_nome(
                nome_arquivo=solicitacao.arquivo,
                pasta_dados=pasta_dados,
            )

            if caminho is not None:
                return caminho

        if solicitacao.parceiro:
            return self.localizar_por_parceiro(
                parceiro=solicitacao.parceiro,
                pasta_dados=pasta_dados,
            )

        raise ValueError(
            "Nenhum CSV foi enviado e a pergunta não "
            "identifica um parceiro ou arquivo."
        )

    def localizar_por_nome(
        self,
        nome_arquivo: str,
        pasta_dados: Path,
    ) -> Path | None:
        """Procura um CSV pelo nome informado."""

        nome_procurado = self.normalizar_texto(
            Path(nome_arquivo).stem
        )

        correspondencias = []

        for caminho in pasta_dados.glob("*.csv"):
            nome_candidato = self.normalizar_texto(
                caminho.stem
            )

            if (
                nome_procurado == nome_candidato
                or nome_procurado in nome_candidato
                or nome_candidato in nome_procurado
            ):
                correspondencias.append(
                    caminho
                )

        if len(correspondencias) == 1:
            return correspondencias[0]

        if len(correspondencias) > 1:
            nomes = ", ".join(
                caminho.name
                for caminho in correspondencias
            )

            raise ValueError(
                "Mais de um arquivo corresponde ao nome "
                f"informado: {nomes}"
            )

        return None

    def localizar_por_parceiro(
        self,
        parceiro: str,
        pasta_dados: Path,
    ) -> Path:
        """Procura o CSV pelo nome ou pelo conteúdo local."""

        parceiro_normalizado = self.normalizar_texto(
            parceiro
        )

        termos_parceiro = self.criar_termos_parceiro(
            parceiro_normalizado
        )

        correspondencias_nome = []

        for caminho in pasta_dados.glob("*.csv"):
            nome_normalizado = self.normalizar_texto(
                caminho.stem
            )

            if any(
                termo in nome_normalizado
                for termo in termos_parceiro
            ):
                correspondencias_nome.append(
                    caminho
                )

        if len(correspondencias_nome) == 1:
            return correspondencias_nome[0]

        correspondencias_conteudo = (
            self.localizar_parceiro_no_conteudo(
                parceiro_normalizado=parceiro_normalizado,
                pasta_dados=pasta_dados,
            )
        )

        correspondencias = list(
            {
                caminho.resolve(): caminho
                for caminho in (
                    correspondencias_nome
                    + correspondencias_conteudo
                )
            }.values()
        )

        if not correspondencias:
            raise FileNotFoundError(
                f"Nenhum CSV do {parceiro} foi encontrado "
                f"em {pasta_dados}."
            )

        if len(correspondencias) > 1:
            nomes = ", ".join(
                caminho.name
                for caminho in correspondencias
            )

            raise ValueError(
                f"Mais de um CSV corresponde ao "
                f"{parceiro}: {nomes}"
            )

        return correspondencias[0]

    def localizar_parceiro_no_conteudo(
        self,
        parceiro_normalizado: str,
        pasta_dados: Path,
    ) -> list[Path]:
        """Lê localmente a coluna Parceiro dos CSVs."""

        correspondencias = []

        for caminho in pasta_dados.glob("*.csv"):
            try:
                dados = pd.read_csv(
                    caminho,
                    usecols=["Parceiro"],
                    encoding="utf-8",
                )

            except (
                ValueError,
                UnicodeDecodeError,
                pd.errors.EmptyDataError,
                pd.errors.ParserError,
            ):
                continue

            parceiros = {
                self.normalizar_texto(valor)
                for valor in (
                    dados["Parceiro"]
                    .dropna()
                    .astype(str)
                    .unique()
                )
            }

            if parceiro_normalizado in parceiros:
                correspondencias.append(
                    caminho
                )

        return correspondencias

    def criar_termos_parceiro(
        self,
        parceiro_normalizado: str,
    ) -> set[str]:
        """Cria variações do parceiro para busca."""

        termos = {
            parceiro_normalizado,
            parceiro_normalizado.replace(
                " ",
                "",
            ),
            parceiro_normalizado.replace(
                "parceiro ",
                "parceiro",
            ),
        }

        partes = parceiro_normalizado.split()

        if (
            len(partes) == 2
            and partes[0] == "parceiro"
        ):
            termos.add(
                f"parceiro{partes[1]}"
            )

        return {
            termo
            for termo in termos
            if termo
        }

    def criar_prompt_sistema(
        self,
    ) -> str:
        """Cria as instruções enviadas ao Gemini."""

        metricas = "\n".join(
            f"- {nome}: {descricao}"
            for nome, descricao
            in self.METRICAS.items()
        )

        return f"""
Você interpreta solicitações de análise de testes A/B
de cashback.

Sua única função é identificar:
- modo;
- métrica;
- direção;
- parceiro;
- arquivo mencionado.

Modos aceitos:
- ranking: comparar grupos e selecionar um grupo;
- relatorio: mostrar uma consulta geral sem selecionar
  um grupo vencedor.

Métricas aceitas:
{metricas}

Parceiros disponíveis:
- Parceiro A;
- Parceiro B;
- Parceiro C.

Regras obrigatórias:

1. Use "relatorio" quando o usuário pedir uma visão
   geral, todas as métricas ou uma consulta consolidada
   sem solicitar maior ou menor resultado.

2. Use "ranking" quando o usuário pedir maior, menor,
   melhor, máximo, mínimo, maximização, minimização,
   mais, menos ou qual grupo deve ser escalado.

3. A palavra "relatório" não determina sozinha o modo.
   Se a pergunta também solicitar maior, menor, mais,
   menos, maximização ou minimização, use "ranking".

4. Para maior, máximo, mais, melhor ou aumentar, use
   a direção "maximizar".

5. Para menor, mínimo, menos, reduzir ou diminuir, use
   a direção "minimizar".

6. "Mais gente comprando" significa maximizar
   compradores.

7. "Menos gente comprando" significa minimizar
   compradores.

8. "Cashback pago para cada cliente" significa
   cashback_por_comprador.

9. "Grupo A", "grupo B" ou "grupo C" devem ser
   interpretados como Parceiro A, Parceiro B ou
   Parceiro C.

10. Sempre retorne o parceiro no formato:
    - Parceiro A;
    - Parceiro B;
    - Parceiro C.

11. Se nenhuma métrica puder ser identificada em uma
    consulta de ranking, retorne metrica como nula.

12. Se nenhuma direção puder ser identificada em uma
    consulta de ranking, retorne direcao como nula.

13. Em um relatório geral, metrica e direcao devem ser
    nulas.

14. Extraia arquivo somente quando o usuário mencionar
    explicitamente um nome de arquivo ou CSV.

15. Não invente parceiro, arquivo, métrica ou direção.

16. Não analise valores, não faça cálculos e não escolha
    o grupo vencedor.
""".strip()

    def normalizar_texto(
        self,
        texto: str,
    ) -> str:
        """Normaliza textos para comparações locais."""

        texto = unicodedata.normalize(
            "NFKD",
            str(texto),
        )

        texto = "".join(
            caractere
            for caractere in texto
            if not unicodedata.combining(
                caractere
            )
        )

        texto = (
            texto
            .strip()
            .lower()
            .replace("_", " ")
            .replace("-", " ")
        )

        return " ".join(
            texto.split()
        )