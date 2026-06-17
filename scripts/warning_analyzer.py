"""Geração de warnings para o grupo vencedor da análise base."""

from __future__ import annotations

from typing import Any


class AnaliseWarnings:
    """
    Analisa o grupo vencedor usando métricas complementares.

    Métricas consideradas:
    - vendas totais;
    - receita líquida;
    - margem líquida.
    """

    METRICAS_ESSENCIAIS = [
        "vendas_totais",
        "receita_liquida",
        "margem_liquida",
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

    def __init__(
        self,
        limite_warning: float = 0.10,
    ) -> None:
        """
        Parameters
        ----------
        limite_warning:
            Defasagem mínima para gerar um alerta de atenção.

            O valor padrão de 0.10 corresponde a 10%.
        """

        if not 0 <= limite_warning <= 1:
            raise ValueError(
                "O limite do warning deve estar entre 0 e 1."
            )

        self.limite_warning = limite_warning

    def executar(
        self,
        resultado_base: dict[str, Any],
    ) -> dict[str, Any]:
        """Gera warnings para o vencedor do ranking."""

        self.validar_resultado(
            resultado_base
        )

        grupo_vencedor = resultado_base[
            "vencedor"
        ]["grupo"]

        metrica_objetivo = resultado_base[
            "metrica"
        ]

        resultados_grupos = resultado_base[
            "resultados_grupos"
        ]

        metricas_vencedor = resultados_grupos[
            grupo_vencedor
        ]["metricas"]

        warnings: list[dict[str, Any]] = []

        receita_liquida = metricas_vencedor[
            "receita_liquida"
        ]

        warning_critico = self.criar_warning_critico(
            grupo=grupo_vencedor,
            metrica_objetivo=metrica_objetivo,
            receita_liquida=receita_liquida,
        )

        if warning_critico is not None:
            warnings.append(
                warning_critico
            )

        for metrica in self.METRICAS_ESSENCIAIS:
            if metrica == metrica_objetivo:
                continue

            # Quando a receita líquida é zero ou negativa,
            # o alerta crítico já representa também o problema
            # da margem líquida.
            if (
                receita_liquida <= 0
                and metrica in {
                    "receita_liquida",
                    "margem_liquida",
                }
            ):
                continue

            warning = self.analisar_metrica(
                grupo_vencedor=grupo_vencedor,
                metrica_objetivo=metrica_objetivo,
                metrica_analisada=metrica,
                resultados_grupos=resultados_grupos,
            )

            if warning is not None:
                warnings.append(
                    warning
                )

        return {
            "parceiro": resultado_base.get(
                "parceiro"
            ),
            "grupo_analisado": grupo_vencedor,
            "metrica_objetivo": metrica_objetivo,
            "limite_warning": self.limite_warning,
            "quantidade_warnings": len(
                warnings
            ),
            "warnings": warnings,
        }

    def validar_resultado(
        self,
        resultado_base: dict[str, Any],
    ) -> None:
        """Confere se o resultado recebido pode ser analisado."""

        if not isinstance(
            resultado_base,
            dict,
        ):
            raise ValueError(
                "O resultado da análise base deve ser "
                "um dicionário."
            )

        if resultado_base.get(
            "modo"
        ) != "ranking":
            raise ValueError(
                "Os warnings somente podem ser gerados "
                "para resultados no modo ranking."
            )

        campos_obrigatorios = [
            "metrica",
            "vencedor",
            "resultados_grupos",
        ]

        campos_faltantes = [
            campo
            for campo in campos_obrigatorios
            if campo not in resultado_base
        ]

        if campos_faltantes:
            raise ValueError(
                "Campos ausentes no resultado da análise base: "
                + ", ".join(
                    campos_faltantes
                )
            )

        vencedor = resultado_base[
            "vencedor"
        ]

        if not isinstance(
            vencedor,
            dict,
        ):
            raise ValueError(
                "O vencedor da análise deve ser um dicionário."
            )

        grupo_vencedor = vencedor.get(
            "grupo"
        )

        resultados_grupos = resultado_base[
            "resultados_grupos"
        ]

        if grupo_vencedor not in resultados_grupos:
            raise ValueError(
                "O grupo vencedor não foi encontrado "
                "nos resultados consolidados."
            )

        metricas_vencedor = resultados_grupos[
            grupo_vencedor
        ].get(
            "metricas",
            {},
        )

        metricas_faltantes = [
            metrica
            for metrica in self.METRICAS_ESSENCIAIS
            if metrica not in metricas_vencedor
        ]

        if metricas_faltantes:
            raise ValueError(
                "Métricas essenciais ausentes no grupo "
                "vencedor: "
                + ", ".join(
                    metricas_faltantes
                )
            )

    def criar_warning_critico(
        self,
        grupo: str,
        metrica_objetivo: str,
        receita_liquida: float,
    ) -> dict[str, Any] | None:
        """Gera alerta crítico para receita líquida não positiva."""

        if receita_liquida > 0:
            return None

        nome_objetivo = self.nome_metrica(
            metrica_objetivo
        )

        if receita_liquida == 0:
            mensagem = (
                f"O {grupo} foi selecionado com base em "
                f"{nome_objetivo}, mas apresentou receita "
                "líquida igual a zero. O escalonamento deve "
                "ser revisado antes da tomada de decisão."
            )

        else:
            mensagem = (
                f"O {grupo} foi selecionado com base em "
                f"{nome_objetivo}, mas apresentou receita "
                "líquida negativa. O escalonamento deve "
                "ser revisado antes da tomada de decisão."
            )

        return {
            "nivel": "critico",
            "metrica": "receita_liquida",
            "mensagem": mensagem,
            "valor_grupo": receita_liquida,
            "melhor_grupo": None,
            "melhor_valor": None,
            "defasagem": None,
        }

    def analisar_metrica(
        self,
        grupo_vencedor: str,
        metrica_objetivo: str,
        metrica_analisada: str,
        resultados_grupos: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Verifica se o vencedor está pelo menos 10% abaixo
        do melhor grupo em uma métrica complementar.
        """

        valores = {
            grupo: resultado["metricas"][
                metrica_analisada
            ]
            for grupo, resultado
            in resultados_grupos.items()
        }

        valores_validos = {
            grupo: valor
            for grupo, valor in valores.items()
            if valor is not None
        }

        if not valores_validos:
            return None

        melhor_grupo = max(
            valores_validos,
            key=valores_validos.get,
        )

        melhor_valor = valores_validos[
            melhor_grupo
        ]

        valor_vencedor = valores_validos.get(
            grupo_vencedor
        )

        if valor_vencedor is None:
            return None

        if melhor_grupo == grupo_vencedor:
            return None

        defasagem = self.calcular_defasagem(
            valor_grupo=valor_vencedor,
            melhor_valor=melhor_valor,
        )

        if (
            defasagem is None
            or defasagem < self.limite_warning
        ):
            return None

        nome_objetivo = self.nome_metrica(
            metrica_objetivo
        )

        nome_analisado = self.nome_metrica(
            metrica_analisada
        )

        percentual = self.formatar_percentual(
            defasagem
        )

        mensagem = (
            f"O {grupo_vencedor} foi selecionado com base "
            f"em {nome_objetivo}, mas seu resultado em "
            f"{nome_analisado} ficou {percentual} abaixo "
            f"do {melhor_grupo}, que apresentou o melhor "
            "desempenho nessa métrica."
        )

        return {
            "nivel": "atencao",
            "metrica": metrica_analisada,
            "mensagem": mensagem,
            "valor_grupo": valor_vencedor,
            "melhor_grupo": melhor_grupo,
            "melhor_valor": melhor_valor,
            "defasagem": defasagem,
        }

    def calcular_defasagem(
        self,
        valor_grupo: float,
        melhor_valor: float,
    ) -> float | None:
        """Calcula quanto o grupo está abaixo do melhor resultado."""

        if melhor_valor == 0:
            return None

        return float(
            (
                melhor_valor
                - valor_grupo
            )
            / abs(
                melhor_valor
            )
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

    def formatar_percentual(
        self,
        valor: float,
    ) -> str:
        """Formata uma proporção como percentual brasileiro."""

        return (
            f"{float(valor) * 100:.1f}%"
            .replace(
                ".",
                ",",
            )
        )