"""Geração de respostas finais em linguagem natural."""

from __future__ import annotations

import json
import time
from typing import Any

from google.genai import errors
from google.genai import types

try:
    from .llm_client import ClienteLLM

except ImportError:
    from llm_client import ClienteLLM


class RespostaNatural:
    """
    Transforma resultados calculados pelo Python em texto.

    O Gemini é usado apenas para redigir a resposta. Caso a API
    esteja indisponível, uma resposta local é criada pelo Python.
    """

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

    CODIGOS_TEMPORARIOS = {
        429,
        500,
        502,
        503,
        504,
    }

    MAXIMO_TENTATIVAS = 2
    ESPERA_INICIAL = 2

    def __init__(
        self,
        cliente_llm: ClienteLLM,
    ) -> None:
        self.cliente_llm = cliente_llm
        self.cliente = cliente_llm.cliente
        self.modelo = cliente_llm.modelo

    def executar(
        self,
        pergunta: str,
        solicitacao: dict[str, Any],
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None,
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Gera a resposta final.

        A resposta local é utilizada quando a segunda chamada ao
        Gemini falha.
        """

        contexto = self.montar_contexto(
            pergunta=pergunta,
            solicitacao=solicitacao,
            resultado_base=resultado_base,
            resultado_warnings=resultado_warnings,
            registro=registro,
        )

        resposta_fallback = self.criar_resposta_local(
            contexto
        )

        try:
            resposta = self.gerar_resposta_gemini(
                contexto
            )

            if not resposta:
                return {
                    "texto": resposta_fallback,
                    "origem": "fallback_local",
                    "codigo_erro": None,
                }

            return {
                "texto": resposta,
                "origem": "gemini",
                "codigo_erro": None,
            }

        except Exception as erro:
            return {
                "texto": resposta_fallback,
                "origem": "fallback_local",
                "codigo_erro": self.extrair_codigo_erro(
                    erro
                ),
            }

    def montar_contexto(
        self,
        pergunta: str,
        solicitacao: dict[str, Any],
        resultado_base: dict[str, Any],
        resultado_warnings: dict[str, Any] | None,
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        """Monta um contexto compacto para a resposta."""

        modo = resultado_base.get(
            "modo"
        )

        contexto: dict[str, Any] = {
            "pergunta_original": pergunta,
            "modo": modo,
            "parceiro": resultado_base.get(
                "parceiro"
            ),
            "arquivo": solicitacao.get(
                "caminho_arquivo"
            ),
        }

        linha_registro = registro.get(
            "linha",
            {},
        )

        if modo == "ranking":
            vencedor = resultado_base.get(
                "vencedor",
                {},
            )

            contexto.update(
                {
                    "metrica": resultado_base.get(
                        "metrica"
                    ),
                    "direcao": resultado_base.get(
                        "direcao"
                    ),
                    "grupo_vencedor": vencedor.get(
                        "grupo"
                    ),
                    "valor_vencedor": vencedor.get(
                        "valor"
                    ),
                    "ranking": resultado_base.get(
                        "ranking",
                        [],
                    ),
                    "decisao_registrada": (
                        linha_registro.get(
                            "Decisão"
                        )
                    ),
                    "warnings": self.preparar_warnings(
                        resultado_warnings
                    ),
                }
            )

        else:
            contexto.update(
                {
                    "quantidade_grupos": (
                        resultado_base.get(
                            "quantidade_grupos",
                            0,
                        )
                    ),
                    "grupos": list(
                        resultado_base.get(
                            "resultados_grupos",
                            {},
                        ).keys()
                    ),
                    "decisao_registrada": (
                        linha_registro.get(
                            "Decisão"
                        )
                    ),
                }
            )

        return contexto

    def preparar_warnings(
        self,
        resultado_warnings: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Reduz os warnings aos campos necessários."""

        if not resultado_warnings:
            return []

        warnings_preparados = []

        for warning in resultado_warnings.get(
            "warnings",
            [],
        ):
            warnings_preparados.append(
                {
                    "nivel": warning.get(
                        "nivel"
                    ),
                    "metrica": warning.get(
                        "metrica"
                    ),
                    "valor_grupo": warning.get(
                        "valor_grupo"
                    ),
                    "melhor_grupo": warning.get(
                        "melhor_grupo"
                    ),
                    "melhor_valor": warning.get(
                        "melhor_valor"
                    ),
                    "defasagem": warning.get(
                        "defasagem"
                    ),
                    "mensagem": warning.get(
                        "mensagem"
                    ),
                }
            )

        return warnings_preparados

    def gerar_resposta_gemini(
        self,
        contexto: dict[str, Any],
    ) -> str:
        """Solicita ao Gemini a redação da resposta."""

        prompt = self.criar_prompt(
            contexto
        )

        ultimo_erro: Exception | None = None

        for tentativa in range(
            1,
            self.MAXIMO_TENTATIVAS + 1,
        ):
            try:
                resposta = (
                    self.cliente.models.generate_content(
                        model=self.modelo,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                        ),
                    )
                )

                if resposta.text:
                    return resposta.text.strip()

                return ""

            except errors.APIError as erro:
                ultimo_erro = erro

                codigo = self.extrair_codigo_erro(
                    erro
                )

                if codigo not in self.CODIGOS_TEMPORARIOS:
                    raise

                if tentativa == self.MAXIMO_TENTATIVAS:
                    break

                espera = (
                    self.ESPERA_INICIAL
                    * tentativa
                )

                time.sleep(
                    espera
                )

            except (
                ConnectionError,
                TimeoutError,
            ) as erro:
                ultimo_erro = erro

                if tentativa == self.MAXIMO_TENTATIVAS:
                    break

                espera = (
                    self.ESPERA_INICIAL
                    * tentativa
                )

                time.sleep(
                    espera
                )

        if ultimo_erro is not None:
            raise ultimo_erro

        raise RuntimeError(
            "Não foi possível gerar a resposta natural."
        )

    def criar_prompt(
        self,
        contexto: dict[str, Any],
    ) -> str:
        """Cria as instruções para a redação da resposta."""

        contexto_json = json.dumps(
            contexto,
            ensure_ascii=False,
            indent=2,
        )

        return f"""
Você redige respostas executivas para análises de testes
A/B de cashback.

Os cálculos já foram realizados pelo Python. Use somente
os dados fornecidos abaixo.

Regras obrigatórias:

1. Não faça novos cálculos.
2. Não altere o vencedor.
3. Não invente valores, grupos, métricas ou conclusões.
4. Use nomes amigáveis em português.
5. Para métricas monetárias, use o formato brasileiro.
6. Para taxas e margens, apresente percentual.
7. Destaque alertas críticos claramente.
8. Não use tabelas.
9. Não use títulos.
10. Não use listas.
11. Produza no máximo três parágrafos curtos.
12. Em consulta geral, não escolha um vencedor.
13. Não use a expressão "por transação" sem que essa
    informação esteja explicitamente nos dados.
14. A resposta deve ser direta e fácil de entender.

Dados da análise:

{contexto_json}
""".strip()

    def criar_resposta_local(
        self,
        contexto: dict[str, Any],
    ) -> str:
        """Cria uma resposta determinística sem usar a API."""

        if contexto.get(
            "modo"
        ) == "relatorio":
            return self.criar_resposta_relatorio(
                contexto
            )

        return self.criar_resposta_ranking(
            contexto
        )

    def criar_resposta_relatorio(
        self,
        contexto: dict[str, Any],
    ) -> str:
        """Cria o fallback para uma consulta geral."""

        parceiro = contexto.get(
            "parceiro",
            "parceiro não identificado",
        )

        quantidade_grupos = contexto.get(
            "quantidade_grupos",
            0,
        )

        return (
            f"O relatório geral do {parceiro} foi gerado "
            f"com os dados consolidados de "
            f"{quantidade_grupos} grupos. A consulta é "
            "descritiva e não seleciona um grupo vencedor."
        )

    def criar_resposta_ranking(
        self,
        contexto: dict[str, Any],
    ) -> str:
        """Cria o fallback para uma análise de ranking."""

        grupo = contexto.get(
            "grupo_vencedor",
            "Grupo não identificado",
        )

        metrica = contexto.get(
            "metrica",
            "",
        )

        direcao = contexto.get(
            "direcao",
            "maximizar",
        )

        valor = contexto.get(
            "valor_vencedor"
        )

        nome_metrica = self.nome_metrica(
            metrica
        )

        valor_formatado = self.formatar_valor(
            metrica=metrica,
            valor=valor,
        )

        criterio = (
            "menor"
            if direcao == "minimizar"
            else "maior"
        )

        resposta = (
            f"O {grupo} apresentou o {criterio} valor de "
            f"{nome_metrica}, com {valor_formatado}."
        )

        warnings = contexto.get(
            "warnings",
            [],
        )

        if warnings:
            resposta += " " + self.criar_texto_warnings(
                grupo=grupo,
                warnings=warnings,
            )

        decisao = contexto.get(
            "decisao_registrada"
        )

        if decisao:
            resposta += (
                f" A decisão registrada foi: {decisao}"
            )

        return resposta

    def criar_texto_warnings(
        self,
        grupo: str,
        warnings: list[dict[str, Any]],
    ) -> str:
        """Cria um texto amigável para os warnings."""

        textos = []

        for warning in warnings:
            nivel = warning.get(
                "nivel"
            )

            metrica = warning.get(
                "metrica",
                "",
            )

            nome_metrica = self.nome_metrica(
                metrica
            )

            if nivel == "critico":
                valor_grupo = warning.get(
                    "valor_grupo"
                )

                if (
                    metrica == "receita_liquida"
                    and valor_grupo == 0
                ):
                    textos.append(
                        "Há um alerta crítico: a receita "
                        f"líquida do {grupo} é igual a zero."
                    )

                else:
                    textos.append(
                        "Há um alerta crítico relacionado "
                        f"a {nome_metrica}."
                    )

                continue

            defasagem = warning.get(
                "defasagem"
            )

            melhor_grupo = warning.get(
                "melhor_grupo"
            )

            if (
                defasagem is not None
                and melhor_grupo is not None
            ):
                percentual = (
                    f"{float(defasagem) * 100:.1f}"
                    .replace(".", ",")
                )

                textos.append(
                    f"O {grupo} ficou {percentual}% abaixo "
                    f"do {melhor_grupo} em "
                    f"{nome_metrica}."
                )

            else:
                textos.append(
                    f"Foi identificado um alerta em "
                    f"{nome_metrica}."
                )

        return " ".join(
            textos
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

    def formatar_valor(
        self,
        metrica: str,
        valor: float | int | None,
    ) -> str:
        """Formata valores para exibição."""

        if valor is None:
            return "valor não disponível"

        if metrica in self.METRICAS_PERCENTUAIS:
            percentual = float(
                valor
            ) * 100

            return (
                f"{percentual:.2f}%"
                .replace(".", ",")
            )

        if metrica == "compradores":
            return (
                f"{int(round(float(valor))):,}"
                .replace(",", ".")
                + " compradores"
            )

        if metrica in self.METRICAS_MONETARIAS:
            texto = f"{float(valor):,.2f}"

            texto = (
                texto
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

            return f"R$ {texto}"

        return str(
            valor
        )

    def extrair_codigo_erro(
        self,
        erro: BaseException | None,
    ) -> int | None:
        """Procura o código HTTP no erro e em suas causas."""

        erro_atual = erro
        visitados: set[int] = set()

        while erro_atual is not None:
            identificador = id(
                erro_atual
            )

            if identificador in visitados:
                break

            visitados.add(
                identificador
            )

            codigo = getattr(
                erro_atual,
                "code",
                None,
            )

            if codigo is None:
                codigo = getattr(
                    erro_atual,
                    "status_code",
                    None,
                )

            try:
                if codigo is not None:
                    return int(
                        codigo
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

            erro_atual = (
                erro_atual.__cause__
                or erro_atual.__context__
            )

        return None