"""Registro local dos resultados das análises em CSV."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


class RegistroResultados:
    """Registra rankings e consultas gerais em um CSV local."""

    COLUNAS = [
        "Data da análise",
        "Nome do teste",
        "Parceiro",
        "Arquivo",
        "Tipo de consulta",
        "Descrição",
        "Resultado",
        "Decisão",
        "Número de warnings",
        "Warnings",
    ]

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

    NOMES_NIVEIS = {
        "atencao": "ATENÇÃO",
        "critico": "CRÍTICO",
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
        caminho_csv: str | Path = (
            "outputs/acompanhamento_testes.csv"
        ),
    ) -> None:
        self.caminho_csv = Path(
            caminho_csv
        )

    def executar(
        self,
        relatorio_validacao: dict[str, Any],
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Cria uma linha e a adiciona ao CSV.

        Cada execução gera uma nova linha, mesmo quando a análise
        já foi realizada anteriormente.
        """

        linha = self.criar_linha(
            relatorio_validacao=relatorio_validacao,
            resultado_base=resultado_base,
            resultado_warnings=resultado_warnings,
        )

        self.registrar_csv(
            linha
        )

        return {
            "status": "registrado",
            "arquivo": str(
                self.caminho_csv.resolve()
            ),
            "linha": linha,
        }

    def criar_linha(
        self,
        relatorio_validacao: dict[str, Any],
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Monta a linha de acordo com o tipo de consulta."""

        modo = resultado_base.get(
            "modo"
        )

        parceiro = (
            resultado_base.get(
                "parceiro"
            )
            or relatorio_validacao.get(
                "parceiro"
            )
            or "Parceiro não identificado"
        )

        arquivo = Path(
            str(
                relatorio_validacao.get(
                    "arquivo",
                    "",
                )
            )
        ).name

        if modo == "ranking":
            dados = self.criar_dados_ranking(
                parceiro=parceiro,
                resultado_base=resultado_base,
                resultado_warnings=resultado_warnings,
            )

        elif modo == "relatorio":
            dados = self.criar_dados_relatorio(
                parceiro=parceiro,
                resultado_base=resultado_base,
            )

        else:
            raise ValueError(
                "O modo da análise deve ser "
                "'ranking' ou 'relatorio'."
            )

        return {
            "Data da análise": datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
            "Nome do teste": dados[
                "nome_teste"
            ],
            "Parceiro": parceiro,
            "Arquivo": arquivo,
            "Tipo de consulta": dados[
                "tipo_consulta"
            ],
            "Descrição": dados[
                "descricao"
            ],
            "Resultado": dados[
                "resultado"
            ],
            "Decisão": dados[
                "decisao"
            ],
            "Número de warnings": dados[
                "numero_warnings"
            ],
            "Warnings": dados[
                "warnings"
            ],
        }

    def criar_dados_ranking(
        self,
        parceiro: str,
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Cria os textos de uma análise de ranking."""

        metrica = resultado_base.get(
            "metrica"
        )

        direcao = resultado_base.get(
            "direcao"
        )

        vencedor = resultado_base.get(
            "vencedor"
        )

        if metrica is None:
            raise ValueError(
                "A métrica não foi encontrada no resultado."
            )

        if direcao not in {
            "maximizar",
            "minimizar",
        }:
            raise ValueError(
                "A direção deve ser maximizar ou minimizar."
            )

        if not isinstance(
            vencedor,
            dict,
        ):
            raise ValueError(
                "O vencedor não foi encontrado no resultado."
            )

        grupo_vencedor = vencedor.get(
            "grupo"
        )

        valor_vencedor = vencedor.get(
            "valor"
        )

        if grupo_vencedor is None:
            raise ValueError(
                "O grupo vencedor não foi encontrado."
            )

        nome_metrica = self.nome_metrica(
            metrica
        )

        if direcao == "maximizar":
            nome_teste = (
                f"Maximização de {nome_metrica}"
            )

            descricao = (
                f"Selecionar o grupo com o maior resultado "
                f"em {nome_metrica} do {parceiro}."
            )

            termo_resultado = "maior"

        else:
            nome_teste = (
                f"Minimização de {nome_metrica}"
            )

            descricao = (
                f"Selecionar o grupo com o menor resultado "
                f"em {nome_metrica} do {parceiro}."
            )

            termo_resultado = "menor"

        resultado = (
            f"{grupo_vencedor} apresentou o "
            f"{termo_resultado} resultado em "
            f"{nome_metrica}: "
            f"{self.formatar_valor(metrica, valor_vencedor)}."
        )

        warnings: list[dict[str, Any]] = []

        if resultado_warnings is not None:
            warnings = resultado_warnings.get(
                "warnings",
                [],
            )

        numero_warnings = len(
            warnings
        )

        warnings_texto = self.resumir_warnings(
            warnings
        )

        niveis = {
            warning.get(
                "nivel"
            )
            for warning in warnings
        }

        if "critico" in niveis:
            decisao = (
                f"Revisar {grupo_vencedor} antes do "
                "escalonamento devido ao alerta crítico."
            )

        elif numero_warnings > 0:
            decisao = (
                f"Escalar {grupo_vencedor}, acompanhando "
                "os alertas identificados."
            )

        else:
            decisao = (
                f"Escalar {grupo_vencedor}."
            )

        return {
            "nome_teste": nome_teste,
            "tipo_consulta": "Ranking",
            "descricao": descricao,
            "resultado": resultado,
            "decisao": decisao,
            "numero_warnings": numero_warnings,
            "warnings": warnings_texto,
        }

    def criar_dados_relatorio(
        self,
        parceiro: str,
        resultado_base: dict[str, Any],
    ) -> dict[str, Any]:
        """Cria os textos padronizados da consulta geral."""

        resultados_grupos = resultado_base.get(
            "resultados_grupos",
            {},
        )

        quantidade_grupos = resultado_base.get(
            "quantidade_grupos",
            len(
                resultados_grupos
            ),
        )

        termo_grupos = (
            "grupo"
            if quantidade_grupos == 1
            else "grupos"
        )

        return {
            "nome_teste": (
                f"Relatório geral do {parceiro}"
            ),
            "tipo_consulta": "Relatório geral",
            "descricao": (
                "Consulta consolidada das métricas "
                f"dos grupos do {parceiro}."
            ),
            "resultado": (
                f"Relatório geral gerado para "
                f"{quantidade_grupos} {termo_grupos}."
            ),
            "decisao": (
                "Consulta descritiva, sem seleção "
                "de um grupo para escalonamento."
            ),
            "numero_warnings": 0,
            "warnings": "Nenhum alerta.",
        }

    def resumir_warnings(
        self,
        warnings: list[dict[str, Any]],
    ) -> str:
        """Transforma todos os warnings em uma única célula."""

        if not warnings:
            return "Nenhum alerta."

        mensagens = []

        for warning in warnings:
            nivel_interno = str(
                warning.get(
                    "nivel",
                    "atencao",
                )
            ).strip().lower()

            nivel = self.NOMES_NIVEIS.get(
                nivel_interno,
                nivel_interno.upper(),
            )

            mensagem = self.limpar_texto(
                warning.get(
                    "mensagem",
                    "Alerta sem descrição.",
                )
            )

            mensagens.append(
                f"[{nivel}] {mensagem}"
            )

        return " | ".join(
            mensagens
        )

    def registrar_csv(
        self,
        linha: dict[str, Any],
    ) -> None:
        """Adiciona uma nova linha ao CSV local."""

        self.caminho_csv.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        arquivo_existe = (
            self.caminho_csv.exists()
            and self.caminho_csv.stat().st_size > 0
        )

        with self.caminho_csv.open(
            mode="a",
            encoding="utf-8-sig",
            newline="",
        ) as arquivo:
            escritor = csv.DictWriter(
                arquivo,
                fieldnames=self.COLUNAS,
                delimiter=";",
            )

            if not arquivo_existe:
                escritor.writeheader()

            escritor.writerow(
                linha
            )

    def nome_metrica(
        self,
        metrica: str,
    ) -> str:
        """Retorna o nome amigável de uma métrica."""

        return self.NOMES_METRICAS.get(
            metrica,
            str(
                metrica
            ).replace(
                "_",
                " ",
            ),
        )

    def limpar_texto(
        self,
        texto: Any,
    ) -> str:
        """Remove espaços duplicados e quebras desnecessárias."""

        texto_limpo = " ".join(
            str(
                texto
            ).split()
        )

        if not texto_limpo:
            return "Alerta sem descrição."

        return texto_limpo

    def formatar_valor(
        self,
        metrica: str,
        valor: float | int | None,
    ) -> str:
        """Formata o valor principal da análise."""

        if valor is None:
            return "não disponível"

        if metrica in self.METRICAS_PERCENTUAIS:
            percentual = float(
                valor
            ) * 100

            return (
                f"{percentual:.2f}%"
                .replace(
                    ".",
                    ",",
                )
            )

        if metrica == "compradores":
            quantidade = (
                f"{int(round(float(valor))):,}"
                .replace(
                    ",",
                    ".",
                )
            )

            return (
                f"{quantidade} compradores"
            )

        if metrica in self.METRICAS_MONETARIAS:
            texto = f"{float(valor):,.2f}"

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

            return f"R$ {texto}"

        return str(
            valor
        )