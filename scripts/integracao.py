"""Integração completa do fluxo de análise."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .llm_client import (
        CallbackTentativa,
        ClienteLLM,
        SolicitacaoAnalise,
    )
    from .data_preparation_validation import PreparadorDados
    from .descriptive_ranking_analyzer import AnaliseBase
    from .warning_analyzer import AnaliseWarnings
    from .report_generator import GeradorRelatorio
    from .results_logger import RegistroResultados
    from .google_sheets_logger import RegistroGoogleSheets
    from .natural_language_response import RespostaNatural

except ImportError:
    from llm_client import (
        CallbackTentativa,
        ClienteLLM,
        SolicitacaoAnalise,
    )
    from data_preparation_validation import PreparadorDados
    from descriptive_ranking_analyzer import AnaliseBase
    from warning_analyzer import AnaliseWarnings
    from report_generator import GeradorRelatorio
    from results_logger import RegistroResultados
    from google_sheets_logger import RegistroGoogleSheets
    from natural_language_response import RespostaNatural


class Integracao:
    """Conecta interpretação, análise, relatório e registros."""

    def __init__(
        self,
        pasta_dados: str | Path = "data",
        pasta_saida: str | Path = "outputs",
        caminho_registro: str | Path | None = None,
        limite_warning: float = 0.10,
        cliente_llm: ClienteLLM | None = None,
        registro_google_sheets: RegistroGoogleSheets | None = None,
    ) -> None:
        self.pasta_dados = Path(
            pasta_dados
        )

        self.pasta_saida = Path(
            pasta_saida
        )

        if caminho_registro is None:
            caminho_registro = (
                self.pasta_saida
                / "acompanhamento_testes.csv"
            )

        self.cliente_llm = (
            cliente_llm
            if cliente_llm is not None
            else ClienteLLM()
        )

        self.preparador = PreparadorDados()
        self.analise_base = AnaliseBase()

        self.analise_warnings = AnaliseWarnings(
            limite_warning=limite_warning
        )

        self.gerador_relatorio = GeradorRelatorio()

        self.registro_resultados = RegistroResultados(
            caminho_csv=caminho_registro
        )

        self.registro_google_sheets = (
            registro_google_sheets
            if registro_google_sheets is not None
            else RegistroGoogleSheets()
        )

        self.resposta_natural = RespostaNatural(
            cliente_llm=self.cliente_llm
        )

    def executar(
        self,
        pergunta: str,
        arquivo_enviado: str | Path | None = None,
        callback_tentativa: CallbackTentativa | None = None,
    ) -> dict[str, Any]:
        """Executa o fluxo usando a interpretação do Gemini."""

        solicitacao = self.cliente_llm.executar(
            pergunta=pergunta,
            arquivo_enviado=arquivo_enviado,
            pasta_dados=self.pasta_dados,
            callback_tentativa=callback_tentativa,
        )

        solicitacao[
            "origem_interpretacao"
        ] = "gemini"

        return self.executar_solicitacao(
            pergunta=pergunta,
            solicitacao=solicitacao,
        )

    def executar_manual(
        self,
        pergunta: str,
        modo: str,
        parceiro: str | None = None,
        metrica: str | None = None,
        direcao: str | None = None,
        arquivo_enviado: str | Path | None = None,
    ) -> dict[str, Any]:
        """Executa o fluxo com parâmetros escolhidos manualmente."""

        if parceiro is not None:
            parceiro = self.cliente_llm.normalizar_parceiro(
                parceiro
            )

        solicitacao_modelo = SolicitacaoAnalise(
            modo=modo,
            metrica=metrica,
            direcao=direcao,
            parceiro=parceiro,
            arquivo=None,
        )

        self.cliente_llm.validar_solicitacao(
            solicitacao_modelo
        )

        caminho_arquivo = self.cliente_llm.definir_arquivo(
            solicitacao=solicitacao_modelo,
            arquivo_enviado=arquivo_enviado,
            pasta_dados=self.pasta_dados,
        )

        solicitacao = solicitacao_modelo.model_dump()

        solicitacao[
            "pergunta"
        ] = pergunta

        solicitacao[
            "origem_interpretacao"
        ] = "manual"

        solicitacao[
            "caminho_arquivo"
        ] = str(
            caminho_arquivo.resolve()
        )

        return self.executar_solicitacao(
            pergunta=pergunta,
            solicitacao=solicitacao,
        )

    def executar_solicitacao(
        self,
        pergunta: str,
        solicitacao: dict[str, Any],
    ) -> dict[str, Any]:
        """Executa análise, relatório e registros."""

        caminho_arquivo = Path(
            solicitacao[
                "caminho_arquivo"
            ]
        )

        dados, relatorio_validacao = (
            self.preparador.executar(
                caminho_arquivo
            )
        )

        if dados.empty:
            raise ValueError(
                "Nenhuma linha válida permaneceu após "
                "a preparação dos dados."
            )

        modo = solicitacao[
            "modo"
        ]

        if modo == "ranking":
            resultado_base = self.executar_ranking(
                dados=dados,
                solicitacao=solicitacao,
            )

            resultado_warnings = (
                self.analise_warnings.executar(
                    resultado_base
                )
            )

        elif modo == "relatorio":
            resultado_base = self.analise_base.executar(
                dados=dados,
                modo="relatorio",
            )

            resultado_warnings = None

        else:
            raise ValueError(
                "O modo deve ser 'ranking' ou 'relatorio'."
            )

        caminho_relatorio = self.gerador_relatorio.executar(
            relatorio_validacao=relatorio_validacao,
            resultado_base=resultado_base,
            resultado_warnings=resultado_warnings,
            pasta_saida=self.pasta_saida,
        )

        registro_local = self.registro_resultados.executar(
            relatorio_validacao=relatorio_validacao,
            resultado_base=resultado_base,
            resultado_warnings=resultado_warnings,
        )

        linha_registro = registro_local.get(
            "linha",
            {},
        )

        registro_sheets = (
            self.registro_google_sheets.executar(
                linha_registro
            )
        )

        resposta = self.resposta_natural.executar(
            pergunta=pergunta,
            solicitacao=solicitacao,
            resultado_base=resultado_base,
            resultado_warnings=resultado_warnings,
            registro=registro_local,
        )

        return {
            "pergunta": pergunta,
            "solicitacao": solicitacao,
            "relatorio_validacao": relatorio_validacao,
            "resultado_base": resultado_base,
            "resultado_warnings": resultado_warnings,
            "caminho_relatorio": str(
                Path(
                    caminho_relatorio
                ).resolve()
            ),
            "registro": registro_local,
            "registro_google_sheets": registro_sheets,
            "resposta_natural": resposta[
                "texto"
            ],
            "origem_resposta_natural": resposta[
                "origem"
            ],
            "codigo_erro_resposta_natural": resposta[
                "codigo_erro"
            ],
        }

    def executar_ranking(
        self,
        dados,
        solicitacao: dict[str, Any],
    ) -> dict[str, Any]:
        """Executa a análise de ranking."""

        return self.analise_base.executar(
            dados=dados,
            modo="ranking",
            metrica=solicitacao[
                "metrica"
            ],
            direcao=solicitacao[
                "direcao"
            ],
        )