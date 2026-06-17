"""Geração de relatórios HTML profissionais e gráficos da análise."""

from __future__ import annotations

import base64
from datetime import datetime
from html import escape
from pathlib import Path
import re
import unicodedata
from typing import Any

import matplotlib.pyplot as plt


class GeradorRelatorio:
    """Gera relatórios HTML para rankings e consultas gerais."""

    COR_ROSA_PRINCIPAL = "#FF4B7D"
    COR_ROSA_CLARO = "#FFE4EE"
    COR_ROSA_SUAVE = "#FFF5F8"
    COR_ROSA_ESCURO = "#C91F5D"
    COR_TEXTO = "#2D2430"
    COR_TEXTO_SECUNDARIO = "#776D75"
    COR_BRANCO = "#FFFFFF"
    COR_FUNDO = "#FFF8FA"
    COR_BORDA = "#F1D7E0"

    METRICAS_PRINCIPAIS = [
        "vendas_totais",
        "receita_liquida",
        "margem_liquida",
    ]

    METRICAS_COMPLEMENTARES_1 = [
        "compradores",
        "comissao",
        "cashback",
        "vendas_por_comprador",
    ]

    METRICAS_COMPLEMENTARES_2 = [
        "comissao_por_comprador",
        "cashback_por_comprador",
        "receita_liquida_por_comprador",
        "taxa_comissao",
        "taxa_cashback",
    ]

    NOMES_METRICAS = {
        "compradores": "Compradores",
        "comissao": "Comissão",
        "cashback": "Cashback",
        "vendas_totais": "Vendas totais",
        "receita_liquida": "Receita líquida",
        "vendas_por_comprador": "Vendas por comprador",
        "comissao_por_comprador": "Comissão por comprador",
        "cashback_por_comprador": "Cashback por comprador",
        "receita_liquida_por_comprador": (
            "Receita líquida por comprador"
        ),
        "taxa_comissao": "Taxa de comissão",
        "taxa_cashback": "Taxa de cashback",
        "margem_liquida": "Margem líquida",
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

    def __init__(
        self,
        caminho_logo: str | Path | None = None,
    ) -> None:
        """
        Parameters
        ----------
        caminho_logo:
            Caminho da logo utilizada nos relatórios. Quando não
            informado, utiliza assets/logo_meliuz.png.
        """

        raiz_projeto = Path(
            __file__
        ).resolve().parent.parent

        if caminho_logo is None:
            caminho_logo = (
                raiz_projeto
                / "assets"
                / "logo_meliuz.png"
            )

        self.caminho_logo = Path(
            caminho_logo
        )

    def executar(
        self,
        relatorio_validacao: dict[str, Any],
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None = None,
        pasta_saida: str | Path = "outputs",
    ) -> Path:
        """Gera o relatório HTML e retorna seu caminho."""

        self.validar_entrada(
            relatorio_validacao=relatorio_validacao,
            resultado_base=resultado_base,
        )

        pasta_saida = Path(
            pasta_saida
        )

        pasta_graficos = (
            pasta_saida
            / "graficos"
        )

        pasta_saida.mkdir(
            parents=True,
            exist_ok=True,
        )

        pasta_graficos.mkdir(
            parents=True,
            exist_ok=True,
        )

        arquivo_base = Path(
            relatorio_validacao["arquivo"]
        ).stem

        modo = resultado_base[
            "modo"
        ]

        if modo == "ranking":
            imagens = self.gerar_graficos_ranking(
                resultado_base=resultado_base,
                resultado_warnings=resultado_warnings,
                arquivo_base=arquivo_base,
                pasta_graficos=pasta_graficos,
            )

            nome_html = (
                f"relatorio_"
                f"{resultado_base['metrica']}_"
                f"{self.converter_objetivo(resultado_base['direcao'])}_"
                f"{arquivo_base}.html"
            )

        else:
            imagens = self.gerar_graficos_gerais(
                resultado_base=resultado_base,
                arquivo_base=arquivo_base,
                pasta_graficos=pasta_graficos,
            )

            nome_html = (
                f"relatorio_geral_{arquivo_base}.html"
            )

        caminho_html = (
            pasta_saida
            / self.normalizar_nome(
                nome_html
            )
        )

        conteudo = self.criar_html(
            relatorio_validacao=relatorio_validacao,
            resultado_base=resultado_base,
            resultado_warnings=resultado_warnings,
            imagens=imagens,
        )

        caminho_html.write_text(
            conteudo,
            encoding="utf-8",
        )

        return caminho_html

    def validar_entrada(
        self,
        relatorio_validacao: dict[str, Any],
        resultado_base: dict[str, Any],
    ) -> None:
        """Valida os dados mínimos necessários."""

        if not isinstance(
            relatorio_validacao,
            dict,
        ):
            raise ValueError(
                "O relatório de validação deve ser um dicionário."
            )

        if "arquivo" not in relatorio_validacao:
            raise ValueError(
                "O relatório de validação não possui "
                "o nome do arquivo."
            )

        if not isinstance(
            resultado_base,
            dict,
        ):
            raise ValueError(
                "O resultado da análise deve ser um dicionário."
            )

        if resultado_base.get(
            "modo"
        ) not in {
            "ranking",
            "relatorio",
        }:
            raise ValueError(
                "O modo da análise deve ser ranking "
                "ou relatorio."
            )

        if "resultados_grupos" not in resultado_base:
            raise ValueError(
                "Os resultados por grupo não foram encontrados."
            )

    def gerar_graficos_ranking(
        self,
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None,
        arquivo_base: str,
        pasta_graficos: Path,
    ) -> dict[str, Path]:
        """Gera o gráfico principal e os gráficos dos alertas."""

        metrica_principal = resultado_base[
            "metrica"
        ]

        objetivo = self.converter_objetivo(
            resultado_base[
                "direcao"
            ]
        )

        imagens: dict[str, Path] = {}

        imagens[
            metrica_principal
        ] = self.gerar_grafico(
            resultados_grupos=resultado_base[
                "resultados_grupos"
            ],
            metrica=metrica_principal,
            objetivo=objetivo,
            arquivo_base=arquivo_base,
            pasta_graficos=pasta_graficos,
            destaque_grupo=resultado_base[
                "vencedor"
            ]["grupo"],
        )

        if resultado_warnings is None:
            return imagens

        metricas_warnings = []

        for warning in resultado_warnings.get(
            "warnings",
            [],
        ):
            metrica = warning.get(
                "metrica"
            )

            if (
                metrica
                and metrica not in metricas_warnings
            ):
                metricas_warnings.append(
                    metrica
                )

        for metrica in metricas_warnings:
            if metrica == metrica_principal:
                continue

            imagens[
                metrica
            ] = self.gerar_grafico(
                resultados_grupos=resultado_base[
                    "resultados_grupos"
                ],
                metrica=metrica,
                objetivo=objetivo,
                arquivo_base=arquivo_base,
                pasta_graficos=pasta_graficos,
                destaque_grupo=resultado_base[
                    "vencedor"
                ]["grupo"],
                secundario=True,
            )

        return imagens

    def gerar_graficos_gerais(
        self,
        resultado_base: dict[str, Any],
        arquivo_base: str,
        pasta_graficos: Path,
    ) -> dict[str, Path]:
        """Gera os principais gráficos do relatório geral."""

        imagens = {}

        for metrica in [
            "vendas_totais",
            "receita_liquida",
            "margem_liquida",
        ]:
            imagens[
                metrica
            ] = self.gerar_grafico(
                resultados_grupos=resultado_base[
                    "resultados_grupos"
                ],
                metrica=metrica,
                objetivo="geral",
                arquivo_base=arquivo_base,
                pasta_graficos=pasta_graficos,
            )

        return imagens

    def gerar_grafico(
        self,
        resultados_grupos: dict[str, Any],
        metrica: str,
        objetivo: str,
        arquivo_base: str,
        pasta_graficos: Path,
        destaque_grupo: str | None = None,
        secundario: bool = False,
    ) -> Path:
        """Gera um gráfico de barras com identidade visual."""

        grupos = list(
            resultados_grupos.keys()
        )

        valores = [
            resultados_grupos[
                grupo
            ]["metricas"][metrica]
            for grupo in grupos
        ]

        nome_arquivo = self.normalizar_nome(
            f"{metrica}_{objetivo}_{arquivo_base}.png"
        )

        caminho = (
            pasta_graficos
            / nome_arquivo
        )

        largura = (
            7.5
            if secundario
            else 9
        )

        altura = (
            4.2
            if secundario
            else 5
        )

        figura, eixo = plt.subplots(
            figsize=(
                largura,
                altura,
            )
        )

        figura.patch.set_facecolor(
            self.COR_BRANCO
        )

        eixo.set_facecolor(
            self.COR_BRANCO
        )

        cores = [
            self.COR_ROSA_CLARO
            for _ in grupos
        ]

        if destaque_grupo in grupos:
            indice_destaque = grupos.index(
                destaque_grupo
            )

            cores[
                indice_destaque
            ] = self.COR_ROSA_PRINCIPAL

        barras = eixo.bar(
            grupos,
            valores,
            color=cores,
            edgecolor=self.COR_ROSA_PRINCIPAL,
            linewidth=1.2,
        )

        if destaque_grupo in grupos:
            indice_destaque = grupos.index(
                destaque_grupo
            )

            barras[
                indice_destaque
            ].set_hatch(
                "//"
            )

        titulo = self.NOMES_METRICAS.get(
            metrica,
            metrica,
        )

        eixo.set_title(
            f"{titulo} por grupo",
            fontsize=15,
            fontweight="bold",
            color=self.COR_TEXTO,
            pad=18,
        )

        eixo.set_xlabel(
            ""
        )

        eixo.set_ylabel(
            titulo,
            color=self.COR_TEXTO_SECUNDARIO,
            fontsize=10,
        )

        eixo.grid(
            axis="y",
            linestyle="--",
            alpha=0.20,
        )

        eixo.spines[
            "top"
        ].set_visible(
            False
        )

        eixo.spines[
            "right"
        ].set_visible(
            False
        )

        eixo.spines[
            "left"
        ].set_color(
            self.COR_BORDA
        )

        eixo.spines[
            "bottom"
        ].set_color(
            self.COR_BORDA
        )

        eixo.tick_params(
            colors=self.COR_TEXTO_SECUNDARIO
        )

        for barra, valor in zip(
            barras,
            valores,
        ):
            altura_barra = barra.get_height()

            deslocamento = (
                max(
                    abs(
                        float(valor)
                    ),
                    1,
                )
                * 0.025
            )

            eixo.text(
                barra.get_x()
                + barra.get_width() / 2,
                altura_barra
                + deslocamento,
                self.formatar_valor(
                    metrica=metrica,
                    valor=valor,
                    curto=True,
                ),
                ha="center",
                va="bottom",
                fontsize=9,
                color=self.COR_TEXTO,
                fontweight="bold",
            )

        figura.tight_layout()

        figura.savefig(
            caminho,
            dpi=170,
            bbox_inches="tight",
            facecolor=self.COR_BRANCO,
        )

        plt.close(
            figura
        )

        return caminho

    def criar_html(
        self,
        relatorio_validacao: dict[str, Any],
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None,
        imagens: dict[str, Path],
    ) -> str:
        """Monta o conteúdo completo do relatório."""

        parceiro = (
            resultado_base.get(
                "parceiro"
            )
            or relatorio_validacao.get(
                "parceiro"
            )
            or "Parceiro não identificado"
        )

        modo = resultado_base[
            "modo"
        ]

        titulo = self.criar_titulo(
            parceiro=parceiro,
            resultado_base=resultado_base,
        )

        subtitulo = self.criar_subtitulo(
            resultado_base=resultado_base,
        )

        if modo == "ranking":
            conteudo_principal = (
                self.criar_secao_resumo_ranking(
                    resultado_base=resultado_base,
                    resultado_warnings=resultado_warnings,
                )
                + self.criar_secao_resultado(
                    resultado_base=resultado_base,
                    imagens=imagens,
                )
                + self.criar_secao_warnings(
                    resultado_warnings=resultado_warnings,
                    imagens=imagens,
                )
            )

        else:
            conteudo_principal = (
                self.criar_secao_resumo_geral(
                    resultado_base=resultado_base,
                )
                + self.criar_secao_graficos_gerais(
                    imagens=imagens,
                )
            )

        logo_html = self.criar_logo_html()

        data_geracao = datetime.now().strftime(
            "%d/%m/%Y às %H:%M"
        )

        return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>{escape(titulo)}</title>

    <style>
        :root {{
            --rosa-principal: {self.COR_ROSA_PRINCIPAL};
            --rosa-claro: {self.COR_ROSA_CLARO};
            --rosa-suave: {self.COR_ROSA_SUAVE};
            --rosa-escuro: {self.COR_ROSA_ESCURO};
            --texto: {self.COR_TEXTO};
            --texto-secundario: {self.COR_TEXTO_SECUNDARIO};
            --branco: {self.COR_BRANCO};
            --fundo: {self.COR_FUNDO};
            --borda: {self.COR_BORDA};
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background:
                linear-gradient(
                    180deg,
                    var(--rosa-claro) 0,
                    var(--fundo) 310px
                );
            color: var(--texto);
            font-family:
                Inter,
                "Segoe UI",
                Arial,
                sans-serif;
        }}

        .pagina {{
            width: min(1380px, calc(100% - 48px));
            margin: 0 auto;
            padding: 32px 0 48px;
        }}

        .cabecalho {{
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid var(--borda);
            border-radius: 24px;
            padding: 30px 34px;
            box-shadow: 0 18px 45px rgba(201, 31, 93, 0.10);
            margin-bottom: 24px;
        }}

        .marca {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 28px;
        }}

        .logo {{
            width: 54px;
            height: 54px;
            object-fit: contain;
            border-radius: 14px;
        }}

        .marca-texto {{
            color: var(--texto-secundario);
            font-size: 0.82rem;
            line-height: 1.35;
        }}

        h1 {{
            color: var(--texto);
            font-size: clamp(2rem, 4vw, 3.1rem);
            line-height: 1.08;
            margin: 0;
            max-width: 980px;
        }}

        .subtitulo {{
            color: var(--texto-secundario);
            font-size: 1.05rem;
            line-height: 1.6;
            margin: 14px 0 0;
            max-width: 880px;
        }}

        .faixa {{
            display: inline-block;
            background: var(--rosa-claro);
            color: var(--rosa-escuro);
            border-radius: 999px;
            padding: 7px 12px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 14px;
        }}

        .card {{
            background: var(--branco);
            border: 1px solid var(--borda);
            border-radius: 20px;
            padding: 28px;
            margin-bottom: 22px;
            box-shadow: 0 10px 30px rgba(67, 31, 48, 0.055);
        }}

        .card h2 {{
            font-size: 1.45rem;
            margin: 0 0 20px;
        }}

        .card h3 {{
            font-size: 1.05rem;
            margin: 28px 0 12px;
        }}

        .grade-resumo {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(190px, 1fr));
            gap: 14px;
        }}

        .indicador {{
            background: var(--rosa-suave);
            border: 1px solid var(--rosa-claro);
            border-radius: 16px;
            padding: 18px;
            min-height: 110px;
        }}

        .indicador-label {{
            color: var(--texto-secundario);
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 9px;
            text-transform: uppercase;
            letter-spacing: 0.035em;
        }}

        .indicador-valor {{
            color: var(--texto);
            font-size: 1.25rem;
            font-weight: 750;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }}

        .indicador-destaque {{
            background:
                linear-gradient(
                    135deg,
                    var(--rosa-principal),
                    var(--rosa-escuro)
                );
            border: 0;
        }}

        .indicador-destaque .indicador-label,
        .indicador-destaque .indicador-valor {{
            color: var(--branco);
        }}

        .grafico {{
            display: block;
            width: 100%;
            max-width: 960px;
            margin: 20px auto 8px;
            border-radius: 14px;
        }}

        .grafico-secundario {{
            max-width: 780px;
        }}

        .tabela-container {{
            width: 100%;
        }}

        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            table-layout: fixed;
            font-size: 0.88rem;
        }}

        th {{
            color: var(--rosa-escuro);
            background: var(--rosa-claro);
            font-size: 0.75rem;
            padding: 13px 10px;
            text-align: left;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }}

        td {{
            padding: 13px 10px;
            border-bottom: 1px solid #F4E8EC;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        tbody tr:nth-child(even) {{
            background: #FFF9FB;
        }}

        tbody tr:hover {{
            background: var(--rosa-suave);
        }}

        th:first-child {{
            border-radius: 12px 0 0 0;
        }}

        th:last-child {{
            border-radius: 0 12px 0 0;
        }}

        .alerta {{
            border-radius: 16px;
            padding: 20px;
            margin: 14px 0;
        }}

        .alerta-atencao {{
            background: #FFF7DE;
            border: 1px solid #F2D98A;
        }}

        .alerta-critico {{
            background: #F26F6F;
            border: 1px solid #8c0404;
        }}

        .alerta-titulo {{
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}

        .alerta-atencao .alerta-titulo {{
            color: #8A6200;
        }}

        .alerta-critico .alerta-titulo {{
            color: #B00038;
        }}

        .alerta p {{
            margin: 0;
            line-height: 1.55;
        }}

        .sem-alertas {{
            border-radius: 14px;
            padding: 18px;
            background: #EFFAF3;
            border: 1px solid #B7DFC5;
            color: #205F37;
        }}

        .bloco-tabela + .bloco-tabela {{
            margin-top: 26px;
        }}

        .rodape {{
            color: var(--texto-secundario);
            font-size: 0.76rem;
            line-height: 1.6;
            padding: 8px 6px 0;
        }}

        .rodape-detalhes {{
            border-top: 1px solid var(--borda);
            margin-top: 18px;
            padding-top: 16px;
        }}

        .rodape-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(210px, 1fr));
            gap: 8px 20px;
        }}

        .rodape strong {{
            color: var(--texto);
        }}

        @media (max-width: 760px) {{
            .pagina {{
                width: min(100% - 22px, 1380px);
                padding-top: 14px;
            }}

            .cabecalho,
            .card {{
                padding: 20px;
                border-radius: 16px;
            }}

            table {{
                font-size: 0.72rem;
            }}

            th,
            td {{
                padding: 9px 5px;
            }}
        }}

        @media print {{
            body {{
                background: var(--branco);
            }}

            .pagina {{
                width: 100%;
                padding: 0;
            }}

            .cabecalho,
            .card {{
                box-shadow: none;
                break-inside: avoid;
            }}
        }}
    </style>
</head>

<body>
<main class="pagina">

    <header class="cabecalho">
        <div class="marca">
            {logo_html}

            <div class="marca-texto">
                Case técnico realizado por<br>
                <strong>Pedro Moreira Beiro</strong>
            </div>
        </div>

        <div class="faixa">
            Análise de teste A/B
        </div>

        <h1>{escape(titulo)}</h1>

        <p class="subtitulo">
            {escape(subtitulo)}
        </p>
    </header>

    {conteudo_principal}

    {self.criar_secao_metricas(
        resultado_base["resultados_grupos"]
    )}

    <footer class="rodape">
        <div class="rodape-detalhes">
            <div class="rodape-grid">
                <div>
                    <strong>Arquivo analisado:</strong><br>
                    {escape(str(relatorio_validacao.get("arquivo", "")))}
                </div>

                <div>
                    <strong>Relatório gerado em:</strong><br>
                    {escape(data_geracao)}
                </div>

                <div>
                    <strong>Status dos dados:</strong><br>
                    {escape(str(relatorio_validacao.get("status", "")))}
                </div>
            </div>

            {self.criar_secao_qualidade(
                relatorio_validacao
            )}
        </div>
    </footer>

</main>
</body>
</html>
"""

    def criar_titulo(
        self,
        parceiro: str,
        resultado_base: dict[str, Any],
    ) -> str:
        """Cria um título natural para o relatório."""

        parceiro_formatado = self.formatar_parceiro(
            parceiro
        )

        if resultado_base[
            "modo"
        ] == "relatorio":
            return (
                f"Relatório geral do {parceiro_formatado}"
            )

        metrica = resultado_base[
            "metrica"
        ]

        direcao = resultado_base[
            "direcao"
        ]

        objetivo = (
            "Maximização"
            if direcao == "maximizar"
            else "Minimização"
        )

        nome_metrica = self.NOMES_METRICAS.get(
            metrica,
            metrica,
        )

        return (
            f"{objetivo} de {nome_metrica.lower()} "
            f"do {parceiro_formatado}"
        )

    def criar_subtitulo(
        self,
        resultado_base: dict[str, Any],
    ) -> str:
        """Cria o texto de apoio do cabeçalho."""

        if resultado_base[
            "modo"
        ] == "relatorio":
            quantidade = resultado_base.get(
                "quantidade_grupos",
                len(
                    resultado_base.get(
                        "resultados_grupos",
                        {},
                    )
                ),
            )

            return (
                "Visão consolidada do desempenho das "
                f"{quantidade} variantes avaliadas."
            )

        metrica = self.NOMES_METRICAS.get(
            resultado_base[
                "metrica"
            ],
            resultado_base[
                "metrica"
            ],
        ).lower()

        direcao = resultado_base[
            "direcao"
        ]

        return (
            f"Comparação das variantes para {direcao} "
            f"{metrica}, considerando também métricas "
            "financeiras complementares."
        )

    def criar_secao_resumo_ranking(
        self,
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None,
    ) -> str:
        """Cria os cards executivos do ranking."""

        vencedor = resultado_base[
            "vencedor"
        ]

        metrica = resultado_base[
            "metrica"
        ]

        quantidade_alertas = 0

        nivel_alerta = "Sem alertas"

        if resultado_warnings:
            warnings = resultado_warnings.get(
                "warnings",
                [],
            )

            quantidade_alertas = len(
                warnings
            )

            if any(
                warning.get(
                    "nivel"
                ) == "critico"
                for warning in warnings
            ):
                nivel_alerta = "Alerta crítico"

            elif quantidade_alertas:
                nivel_alerta = (
                    f"{quantidade_alertas} "
                    "alerta"
                    if quantidade_alertas == 1
                    else f"{quantidade_alertas} alertas"
                )

        direcao = (
            "Maior resultado"
            if resultado_base[
                "direcao"
            ] == "maximizar"
            else "Menor resultado"
        )

        return f"""
<section class="card">
    <h2>Resumo executivo</h2>

    <div class="grade-resumo">
        <div class="indicador indicador-destaque">
            <div class="indicador-label">
                Grupo selecionado
            </div>

            <div class="indicador-valor">
                {escape(str(vencedor["grupo"]))}
            </div>
        </div>

        <div class="indicador">
            <div class="indicador-label">
                Métrica analisada
            </div>

            <div class="indicador-valor">
                {escape(self.NOMES_METRICAS.get(metrica, metrica))}
            </div>
        </div>

        <div class="indicador">
            <div class="indicador-label">
                {escape(direcao)}
            </div>

            <div class="indicador-valor">
                {self.formatar_valor(
                    metrica=metrica,
                    valor=vencedor["valor"],
                )}
            </div>
        </div>

        <div class="indicador">
            <div class="indicador-label">
                Avaliação complementar
            </div>

            <div class="indicador-valor">
                {escape(nivel_alerta)}
            </div>
        </div>
    </div>
</section>
"""

    def criar_secao_resumo_geral(
        self,
        resultado_base: dict[str, Any],
    ) -> str:
        """Cria os cards executivos do relatório geral."""

        resultados = resultado_base[
            "resultados_grupos"
        ]

        quantidade_grupos = resultado_base.get(
            "quantidade_grupos",
            len(
                resultados
            ),
        )

        melhor_vendas = max(
            resultados,
            key=lambda grupo: resultados[
                grupo
            ]["metricas"]["vendas_totais"],
        )

        melhor_receita = max(
            resultados,
            key=lambda grupo: resultados[
                grupo
            ]["metricas"]["receita_liquida"],
        )

        melhor_margem = max(
            resultados,
            key=lambda grupo: resultados[
                grupo
            ]["metricas"]["margem_liquida"],
        )

        return f"""
<section class="card">
    <h2>Resumo executivo</h2>

    <div class="grade-resumo">
        <div class="indicador indicador-destaque">
            <div class="indicador-label">
                Variantes avaliadas
            </div>

            <div class="indicador-valor">
                {quantidade_grupos} grupos
            </div>
        </div>

        <div class="indicador">
            <div class="indicador-label">
                Maior volume de vendas
            </div>

            <div class="indicador-valor">
                {escape(str(melhor_vendas))}
            </div>
        </div>

        <div class="indicador">
            <div class="indicador-label">
                Maior receita líquida
            </div>

            <div class="indicador-valor">
                {escape(str(melhor_receita))}
            </div>
        </div>

        <div class="indicador">
            <div class="indicador-label">
                Maior margem líquida
            </div>

            <div class="indicador-valor">
                {escape(str(melhor_margem))}
            </div>
        </div>
    </div>
</section>
"""

    def criar_secao_resultado(
        self,
        resultado_base: dict[str, Any],
        imagens: dict[str, Path],
    ) -> str:
        """Cria a seção detalhada do resultado principal."""

        metrica = resultado_base[
            "metrica"
        ]

        linhas_ranking = ""

        for item in resultado_base.get(
            "ranking",
            [],
        ):
            linhas_ranking += f"""
<tr>
    <td>{item["posicao"]}</td>
    <td><strong>{escape(str(item["grupo"]))}</strong></td>
    <td>
        {self.formatar_valor(
            metrica=metrica,
            valor=item["valor"],
        )}
    </td>
</tr>
"""

        linhas_comparacoes = ""

        for comparacao in resultado_base.get(
            "comparacoes",
            [],
        ):
            percentual = comparacao.get(
                "diferenca_percentual"
            )

            percentual_texto = (
                "Não calculável"
                if percentual is None
                else self.formatar_percentual(
                    percentual
                )
            )

            linhas_comparacoes += f"""
<tr>
    <td>
        {escape(str(comparacao["concorrente"]))}
    </td>

    <td>
        {self.formatar_valor(
            metrica=metrica,
            valor=comparacao["diferenca_absoluta"],
        )}
    </td>

    <td>{percentual_texto}</td>
</tr>
"""

        imagem = imagens[
            metrica
        ]

        return f"""
<section class="card">
    <h2>Desempenho na métrica selecionada</h2>

    <img
        class="grafico"
        src="{self.imagem_base64(imagem)}"
        alt="Gráfico principal da análise"
    >

    <h3>Ranking das variantes</h3>

    <div class="tabela-container">
        <table>
            <thead>
                <tr>
                    <th style="width: 18%;">Posição</th>
                    <th style="width: 42%;">Grupo</th>
                    <th style="width: 40%;">Resultado</th>
                </tr>
            </thead>

            <tbody>
                {linhas_ranking}
            </tbody>
        </table>
    </div>

    <h3>Diferença para as demais variantes</h3>

    <div class="tabela-container">
        <table>
            <thead>
                <tr>
                    <th>Grupo comparado</th>
                    <th>Diferença absoluta</th>
                    <th>Diferença percentual</th>
                </tr>
            </thead>

            <tbody>
                {linhas_comparacoes}
            </tbody>
        </table>
    </div>
</section>
"""

    def criar_secao_warnings(
        self,
        resultado_warnings: dict[str, Any] | None,
        imagens: dict[str, Path],
    ) -> str:
        """Cria a seção visual dos alertas."""

        if (
            resultado_warnings is None
            or not resultado_warnings.get(
                "warnings"
            )
        ):
            return """
<section class="card">
    <h2>Avaliação complementar</h2>

    <div class="sem-alertas">
        Nenhum conflito relevante foi identificado entre
        a métrica selecionada e os principais indicadores
        financeiros.
    </div>
</section>
"""

        conteudo = ""

        for warning in resultado_warnings[
            "warnings"
        ]:
            nivel = warning.get(
                "nivel"
            )

            classe = (
                "alerta alerta-critico"
                if nivel == "critico"
                else "alerta alerta-atencao"
            )

            nome_nivel = (
                "ALERTA CRÍTICO"
                if nivel == "critico"
                else "PONTO DE ATENÇÃO"
            )

            metrica = warning.get(
                "metrica"
            )

            imagem_html = ""

            if metrica in imagens:
                imagem_html = f"""
<img
    class="grafico grafico-secundario"
    src="{self.imagem_base64(imagens[metrica])}"
    alt="Gráfico da métrica complementar"
>
"""

            conteudo += f"""
<div class="{classe}">
    <div class="alerta-titulo">
        {nome_nivel}
    </div>

    <p>
        {escape(str(warning.get("mensagem", "")))}
    </p>

    {imagem_html}
</div>
"""

        return f"""
<section class="card">
    <h2>Avaliação complementar</h2>
    {conteudo}
</section>
"""

    def criar_secao_graficos_gerais(
        self,
        imagens: dict[str, Path],
    ) -> str:
        """Cria a seção visual do relatório geral."""

        conteudo = ""

        for metrica, caminho in imagens.items():
            conteudo += f"""
<div class="bloco-grafico">
    <h3>
        {escape(
            self.NOMES_METRICAS.get(
                metrica,
                metrica,
            )
        )}
    </h3>

    <img
        class="grafico"
        src="{self.imagem_base64(caminho)}"
        alt="Gráfico geral da métrica"
    >
</div>
"""

        return f"""
<section class="card">
    <h2>Visão comparativa</h2>
    {conteudo}
</section>
"""

    def criar_secao_metricas(
        self,
        resultados_grupos: dict[str, Any],
    ) -> str:
        """Cria as tabelas de métricas sem rolagem horizontal."""

        tabela_principal = self.criar_tabela_metricas(
            resultados_grupos=resultados_grupos,
            metricas=self.METRICAS_PRINCIPAIS,
        )

        tabela_complementar_1 = self.criar_tabela_metricas(
            resultados_grupos=resultados_grupos,
            metricas=self.METRICAS_COMPLEMENTARES_1,
        )

        tabela_complementar_2 = self.criar_tabela_metricas(
            resultados_grupos=resultados_grupos,
            metricas=self.METRICAS_COMPLEMENTARES_2,
        )

        return f"""
<section class="card">
    <h2>Indicadores financeiros principais</h2>

    <div class="bloco-tabela">
        {tabela_principal}
    </div>
</section>

<section class="card">
    <h2>Indicadores complementares</h2>

    <div class="bloco-tabela">
        <h3>Volume e valores por comprador</h3>
        {tabela_complementar_1}
    </div>

    <div class="bloco-tabela">
        <h3>Eficiência e taxas</h3>
        {tabela_complementar_2}
    </div>
</section>
"""

    def criar_tabela_metricas(
        self,
        resultados_grupos: dict[str, Any],
        metricas: list[str],
    ) -> str:
        """Cria uma tabela HTML responsiva."""

        quantidade_colunas = len(
            metricas
        ) + 1

        largura_coluna = (
            100
            / quantidade_colunas
        )

        cabecalho = "".join(
            (
                f'<th style="width: {largura_coluna:.2f}%;">'
                f"{escape(self.NOMES_METRICAS[metrica])}"
                "</th>"
            )
            for metrica in metricas
        )

        linhas = ""

        for grupo, resultado in resultados_grupos.items():
            valores = resultado[
                "metricas"
            ]

            celulas = "".join(
                f"""
<td>
    {self.formatar_valor(
        metrica=metrica,
        valor=valores.get(metrica),
    )}
</td>
"""
                for metrica in metricas
            )

            linhas += f"""
<tr>
    <td>
        <strong>{escape(str(grupo))}</strong>
    </td>

    {celulas}
</tr>
"""

        return f"""
<div class="tabela-container">
    <table>
        <thead>
            <tr>
                <th style="width: {largura_coluna:.2f}%;">
                    Grupo
                </th>

                {cabecalho}
            </tr>
        </thead>

        <tbody>
            {linhas}
        </tbody>
    </table>
</div>
"""

    def criar_secao_qualidade(
        self,
        relatorio_validacao: dict[str, Any],
    ) -> str:
        """Cria informações técnicas discretas para o rodapé."""

        warnings = relatorio_validacao.get(
            "warnings",
            [],
        )

        erros = relatorio_validacao.get(
            "erros",
            [],
        )

        mensagens = []

        for mensagem in warnings:
            mensagens.append(
                f"Alerta de dados: {mensagem}"
            )

        for mensagem in erros:
            mensagens.append(
                f"Erro de dados: {mensagem}"
            )

        if not mensagens:
            mensagens.append(
                "Nenhum problema de qualidade identificado."
            )

        itens = "".join(
            f"<li>{escape(str(mensagem))}</li>"
            for mensagem in mensagens
        )

        return f"""
<div class="rodape-grid" style="margin-top: 16px;">
    <div>
        <strong>Linhas iniciais:</strong><br>
        {relatorio_validacao.get("linhas_iniciais", 0)}
    </div>

    <div>
        <strong>Linhas finais:</strong><br>
        {relatorio_validacao.get("linhas_finais", 0)}
    </div>

    <div>
        <strong>Linhas removidas:</strong><br>
        {relatorio_validacao.get("linhas_removidas", 0)}
    </div>

    <div>
        <strong>Datas avaliadas:</strong><br>
        {relatorio_validacao.get("datas", 0)}
    </div>
</div>

<ul>
    {itens}
</ul>
"""

    def criar_logo_html(
        self,
    ) -> str:
        """Cria o HTML da logo incorporada."""

        logo = self.imagem_base64(
            self.caminho_logo
        )

        if not logo:
            return """
<div
    class="logo"
    style="
        background: #FF8EB6;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        font-weight: bold;
    "
>
    m
</div>
"""

        return f"""
<img
    class="logo"
    src="{logo}"
    alt="Logo Méliuz"
>
"""

    def imagem_base64(
        self,
        caminho: Path,
    ) -> str:
        """Converte uma imagem em uma URL Base64."""

        caminho = Path(
            caminho
        )

        if not caminho.exists():
            return ""

        extensao = caminho.suffix.lower()

        tipos = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }

        tipo = tipos.get(
            extensao,
            "image/png",
        )

        conteudo = base64.b64encode(
            caminho.read_bytes()
        ).decode(
            "ascii"
        )

        return (
            f"data:{tipo};base64,"
            f"{conteudo}"
        )

    def formatar_parceiro(
        self,
        parceiro: str,
    ) -> str:
        """Garante uma apresentação natural do parceiro."""

        texto = str(
            parceiro
        ).strip()

        if texto.lower().startswith(
            "parceiro "
        ):
            return texto

        return (
            f"Parceiro {texto}"
        )

    def formatar_percentual(
        self,
        valor: float,
        casas: int = 2,
    ) -> str:
        """Formata uma proporção como percentual."""

        return (
            f"{float(valor) * 100:.{casas}f}%"
            .replace(
                ".",
                ",",
            )
        )

    def formatar_valor(
        self,
        metrica: str,
        valor: Any,
        curto: bool = False,
    ) -> str:
        """Formata valores monetários, percentuais e inteiros."""

        if valor is None:
            return "Não disponível"

        valor_numerico = float(
            valor
        )

        if metrica in self.METRICAS_PERCENTUAIS:
            return self.formatar_percentual(
                valor_numerico
            )

        if metrica == "compradores":
            return (
                f"{int(round(valor_numerico)):,}"
                .replace(
                    ",",
                    ".",
                )
            )

        if metrica in self.METRICAS_MONETARIAS:
            if (
                curto
                and abs(
                    valor_numerico
                ) >= 1_000_000
            ):
                texto = (
                    f"{valor_numerico / 1_000_000:.2f}"
                    .replace(
                        ".",
                        ",",
                    )
                )

                return (
                    f"R$ {texto} mi"
                )

            if (
                curto
                and abs(
                    valor_numerico
                ) >= 1_000
            ):
                texto = (
                    f"{valor_numerico / 1_000:.1f}"
                    .replace(
                        ".",
                        ",",
                    )
                )

                return (
                    f"R$ {texto} mil"
                )

            texto = f"{valor_numerico:,.2f}"

            texto = (
                texto
                .replace(
                    ",",
                    "X",
                )
                .replace(
                    ".",
                    ",",
                )
                .replace(
                    "X",
                    ".",
                )
            )

            return (
                f"R$ {texto}"
            )

        return (
            f"{valor_numerico:.4f}"
            .replace(
                ".",
                ",",
            )
        )

    def converter_objetivo(
        self,
        direcao: str,
    ) -> str:
        """Converte maximizar/minimizar para max/min."""

        if direcao == "maximizar":
            return "max"

        if direcao == "minimizar":
            return "min"

        return "geral"

    def normalizar_nome(
        self,
        nome: str,
    ) -> str:
        """Remove caracteres inadequados de nomes de arquivos."""

        nome = unicodedata.normalize(
            "NFKD",
            nome,
        )

        nome = "".join(
            caractere
            for caractere in nome
            if not unicodedata.combining(
                caractere
            )
        )

        nome = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            nome,
        )

        return nome.strip(
            "_"
        )