"""Análise consolidada e ranking dos grupos."""

from typing import Any

import numpy as np
import pandas as pd


class AnaliseBase:
    """Gera ranking por métrica ou relatório consolidado do parceiro."""

    METRICAS = [
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

    DIRECOES_PADRAO = {
        "compradores": "maximizar",
        "comissao": "maximizar",
        "cashback": "minimizar",
        "vendas_totais": "maximizar",
        "receita_liquida": "maximizar",
        "vendas_por_comprador": "maximizar",
        "comissao_por_comprador": "maximizar",
        "cashback_por_comprador": "minimizar",
        "receita_liquida_por_comprador": "maximizar",
        "taxa_comissao": "maximizar",
        "taxa_cashback": "minimizar",
        "margem_liquida": "maximizar",
    }

    def executar(
        self,
        dados: pd.DataFrame,
        modo: str = "ranking",
        metrica: str | None = None,
        direcao: str | None = None,
    ) -> dict[str, Any]:
        """
        Executa a análise.

        Modos disponíveis:
        - ranking: ordena os grupos segundo uma métrica.
        - relatorio: devolve todas as métricas consolidadas.
        """

        modo = modo.lower().strip()

        self.validar_entrada(
            dados=dados,
            modo=modo,
            metrica=metrica,
            direcao=direcao,
        )

        resultados_grupos = self.calcular_resultados(dados)

        parceiro = self.identificar_parceiro(dados)

        if modo == "relatorio":
            return {
                "modo": "relatorio",
                "parceiro": parceiro,
                "quantidade_grupos": len(resultados_grupos),
                "resultados_grupos": resultados_grupos,
            }

        metrica = str(metrica).lower().strip()

        if direcao is None:
            direcao = self.DIRECOES_PADRAO[metrica]
        else:
            direcao = direcao.lower().strip()

        ranking = self.criar_ranking(
            resultados_grupos=resultados_grupos,
            metrica=metrica,
            direcao=direcao,
        )

        vencedor = ranking[0]

        comparacoes = self.comparar_vencedor(
            ranking=ranking,
            metrica=metrica,
            direcao=direcao,
        )

        return {
            "modo": "ranking",
            "parceiro": parceiro,
            "metrica": metrica,
            "direcao": direcao,
            "quantidade_grupos": len(ranking),
            "vencedor": vencedor,
            "ranking": ranking,
            "comparacoes": comparacoes,
            "resultados_grupos": resultados_grupos,
        }

    def validar_entrada(
        self,
        dados: pd.DataFrame,
        modo: str,
        metrica: str | None,
        direcao: str | None,
    ) -> None:
        """Valida apenas os parâmetros necessários para a análise."""

        if dados.empty:
            raise ValueError("O DataFrame está vazio.")

        if "grupo" not in dados.columns:
            raise ValueError("A coluna 'grupo' não foi encontrada.")

        if dados["grupo"].nunique() < 2:
            raise ValueError(
                "O dataset deve possuir pelo menos dois grupos."
            )

        if modo not in ["ranking", "relatorio"]:
            raise ValueError(
                "O modo deve ser 'ranking' ou 'relatorio'."
            )

        if modo == "relatorio":
            return

        if metrica is None:
            raise ValueError(
                "Uma métrica deve ser informada no modo ranking."
            )

        metrica = metrica.lower().strip()

        if metrica not in self.METRICAS:
            raise ValueError(
                f"Métrica inválida: {metrica}. "
                f"Opções: {', '.join(self.METRICAS)}"
            )

        if direcao is not None:
            direcao = direcao.lower().strip()

            if direcao not in ["maximizar", "minimizar"]:
                raise ValueError(
                    "A direção deve ser 'maximizar' ou 'minimizar'."
                )

    def identificar_parceiro(
        self,
        dados: pd.DataFrame,
    ) -> str | None:
        """Retorna o parceiro encontrado no arquivo."""

        if "parceiro" not in dados.columns:
            return None

        parceiros = (
            dados["parceiro"]
            .dropna()
            .unique()
            .tolist()
        )

        if len(parceiros) == 1:
            return str(parceiros[0])

        return None

    def calcular_resultados(
        self,
        dados: pd.DataFrame,
    ) -> dict[str, dict[str, Any]]:
        """Calcula totais, razões consolidadas e estatísticas por grupo."""

        resultados = {}

        for grupo, dados_grupo in dados.groupby("grupo"):
            compradores = float(
                dados_grupo["compradores"].sum()
            )

            comissao = float(
                dados_grupo["comissao"].sum()
            )

            cashback = float(
                dados_grupo["cashback"].sum()
            )

            vendas_totais = float(
                dados_grupo["vendas_totais"].sum()
            )

            receita_liquida = comissao - cashback

            metricas_consolidadas = {
                "compradores": compradores,
                "comissao": comissao,
                "cashback": cashback,
                "vendas_totais": vendas_totais,
                "receita_liquida": receita_liquida,
                "vendas_por_comprador": self.dividir(
                    vendas_totais,
                    compradores,
                ),
                "comissao_por_comprador": self.dividir(
                    comissao,
                    compradores,
                ),
                "cashback_por_comprador": self.dividir(
                    cashback,
                    compradores,
                ),
                "receita_liquida_por_comprador": self.dividir(
                    receita_liquida,
                    compradores,
                ),
                "taxa_comissao": self.dividir(
                    comissao,
                    vendas_totais,
                ),
                "taxa_cashback": self.dividir(
                    cashback,
                    vendas_totais,
                ),
                "margem_liquida": self.dividir(
                    receita_liquida,
                    vendas_totais,
                ),
            }

            estatisticas = {}

            for metrica in self.METRICAS:
                if metrica not in dados_grupo.columns:
                    continue

                serie = dados_grupo[metrica].dropna()

                estatisticas[metrica] = {
                    "media": float(serie.mean()),
                    "mediana": float(serie.median()),
                    "desvio_padrao": float(serie.std()),
                    "observacoes": int(serie.count()),
                }

            resultados[str(grupo)] = {
                "metricas": metricas_consolidadas,
                "estatisticas": estatisticas,
            }

        return resultados

    def criar_ranking(
        self,
        resultados_grupos: dict[str, dict[str, Any]],
        metrica: str,
        direcao: str,
    ) -> list[dict[str, Any]]:
        """Ordena os grupos segundo a métrica escolhida."""

        ranking = []

        for grupo, resultado in resultados_grupos.items():
            ranking.append(
                {
                    "grupo": grupo,
                    "valor": resultado["metricas"][metrica],
                }
            )

        ordem_decrescente = direcao == "maximizar"

        ranking = sorted(
            ranking,
            key=lambda item: (
                -np.inf
                if item["valor"] is None
                else item["valor"]
            ),
            reverse=ordem_decrescente,
        )

        for posicao, item in enumerate(
            ranking,
            start=1,
        ):
            item["posicao"] = posicao

        return ranking

    def comparar_vencedor(
        self,
        ranking: list[dict[str, Any]],
        metrica: str,
        direcao: str,
    ) -> list[dict[str, Any]]:
        """Compara o vencedor com todos os demais grupos."""

        vencedor = ranking[0]
        valor_vencedor = vencedor["valor"]

        comparacoes = []

        for concorrente in ranking[1:]:
            valor_concorrente = concorrente["valor"]

            if direcao == "maximizar":
                diferenca_absoluta = (
                    valor_vencedor - valor_concorrente
                )
            else:
                diferenca_absoluta = (
                    valor_concorrente - valor_vencedor
                )

            if valor_concorrente == 0:
                diferenca_percentual = None
            else:
                diferenca_percentual = (
                    diferenca_absoluta
                    / abs(valor_concorrente)
                )

            comparacoes.append(
                {
                    "metrica": metrica,
                    "vencedor": vencedor["grupo"],
                    "concorrente": concorrente["grupo"],
                    "valor_vencedor": valor_vencedor,
                    "valor_concorrente": valor_concorrente,
                    "diferenca_absoluta": diferenca_absoluta,
                    "diferenca_percentual": diferenca_percentual,
                }
            )

        return comparacoes

    def dividir(
        self,
        numerador: float,
        denominador: float,
    ) -> float | None:
        """Realiza uma divisão segura."""

        if denominador == 0:
            return None

        return float(numerador / denominador)