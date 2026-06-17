"""Registro opcional de resultados no Google Sheets via webhook."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error
from urllib import request

from dotenv import load_dotenv


class RegistroGoogleSheets:
    """
    Envia registros ao Google Sheets usando um Apps Script.

    A indisponibilidade do webhook não interrompe a análise.
    O método executar sempre retorna um dicionário com o
    status da tentativa de sincronização.
    """

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

    def __init__(
        self,
        url_webhook: str | None = None,
        token_webhook: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        """Carrega as configurações do webhook."""

        raiz_projeto = Path(
            __file__
        ).resolve().parent.parent

        load_dotenv(
            raiz_projeto / ".env"
        )

        self.url_webhook = (
            url_webhook
            or os.getenv(
                "GOOGLE_SHEETS_WEBHOOK_URL"
            )
            or ""
        ).strip()

        self.token_webhook = (
            token_webhook
            or os.getenv(
                "GOOGLE_SHEETS_WEBHOOK_TOKEN"
            )
            or ""
        ).strip()

        self.timeout = timeout

    def executar(
        self,
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Tenta registrar uma linha no Google Sheets.

        Uma falha de rede, configuração ou resposta do Apps
        Script é retornada como status, sem gerar uma exceção
        para o restante da aplicação.
        """

        if not self.esta_configurado():
            return {
                "configurado": False,
                "sincronizado": False,
                "status": "nao_configurado",
                "mensagem": (
                    "A integração com o Google Sheets "
                    "não está configurada."
                ),
                "codigo_http": None,
                "linha": None,
                "aba": None,
            }

        try:
            registro_preparado = self.preparar_registro(
                registro
            )

            resposta = self.enviar_registro(
                registro_preparado
            )

            if resposta.get(
                "sucesso"
            ) is not True:
                return {
                    "configurado": True,
                    "sincronizado": False,
                    "status": "erro_webhook",
                    "mensagem": resposta.get(
                        "mensagem",
                        "O webhook recusou o registro.",
                    ),
                    "codigo_http": 200,
                    "linha": resposta.get(
                        "linha"
                    ),
                    "aba": resposta.get(
                        "aba"
                    ),
                }

            return {
                "configurado": True,
                "sincronizado": True,
                "status": "sincronizado",
                "mensagem": resposta.get(
                    "mensagem",
                    "Registro sincronizado com o Google Sheets.",
                ),
                "codigo_http": 200,
                "linha": resposta.get(
                    "linha"
                ),
                "aba": resposta.get(
                    "aba"
                ),
            }

        except error.HTTPError as erro:
            return {
                "configurado": True,
                "sincronizado": False,
                "status": "erro_http",
                "mensagem": self.ler_erro_http(
                    erro
                ),
                "codigo_http": erro.code,
                "linha": None,
                "aba": None,
            }

        except error.URLError as erro:
            return {
                "configurado": True,
                "sincronizado": False,
                "status": "erro_conexao",
                "mensagem": (
                    "Não foi possível acessar o webhook "
                    f"do Google Sheets: {erro.reason}"
                ),
                "codigo_http": None,
                "linha": None,
                "aba": None,
            }

        except TimeoutError:
            return {
                "configurado": True,
                "sincronizado": False,
                "status": "timeout",
                "mensagem": (
                    "O Google Sheets não respondeu dentro "
                    "do tempo limite."
                ),
                "codigo_http": None,
                "linha": None,
                "aba": None,
            }

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as erro:
            return {
                "configurado": True,
                "sincronizado": False,
                "status": "resposta_invalida",
                "mensagem": (
                    "A resposta do webhook não pôde ser "
                    f"interpretada: {erro}"
                ),
                "codigo_http": None,
                "linha": None,
                "aba": None,
            }

        except Exception as erro:
            return {
                "configurado": True,
                "sincronizado": False,
                "status": "erro_inesperado",
                "mensagem": (
                    "O registro local foi concluído, mas "
                    "ocorreu um erro inesperado durante a "
                    f"sincronização: {erro}"
                ),
                "codigo_http": None,
                "linha": None,
                "aba": None,
            }

    def esta_configurado(
        self,
    ) -> bool:
        """Informa se URL e token foram configurados."""

        return bool(
            self.url_webhook
            and self.token_webhook
        )

    def preparar_registro(
        self,
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        """Seleciona e normaliza as colunas esperadas."""

        if not isinstance(
            registro,
            dict,
        ):
            raise TypeError(
                "O registro do Google Sheets deve ser "
                "um dicionário."
            )

        registro_preparado: dict[str, Any] = {}

        for coluna in self.COLUNAS:
            valor = registro.get(
                coluna,
                "",
            )

            registro_preparado[
                coluna
            ] = self.normalizar_valor(
                valor
            )

        return registro_preparado

    def normalizar_valor(
        self,
        valor: Any,
    ) -> str | int | float | bool:
        """Converte valores complexos para formatos JSON."""

        if valor is None:
            return ""

        if isinstance(
            valor,
            bool,
        ):
            return valor

        if isinstance(
            valor,
            int,
        ):
            return valor

        if isinstance(
            valor,
            float,
        ):
            return valor

        if isinstance(
            valor,
            str,
        ):
            return valor

        if isinstance(
            valor,
            (
                list,
                tuple,
                set,
            ),
        ):
            return "; ".join(
                str(
                    item
                )
                for item in valor
            )

        if isinstance(
            valor,
            dict,
        ):
            return json.dumps(
                valor,
                ensure_ascii=False,
            )

        return str(
            valor
        )

    def enviar_registro(
        self,
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        """Envia o POST ao Apps Script."""

        corpo = {
            "token": self.token_webhook,
            "registro": registro,
        }

        dados = json.dumps(
            corpo,
            ensure_ascii=False,
        ).encode(
            "utf-8"
        )

        requisicao = request.Request(
            url=self.url_webhook,
            data=dados,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": (
                    "case-tecnico-meliuz-google-sheets/1.0"
                ),
            },
        )

        with request.urlopen(
            requisicao,
            timeout=self.timeout,
        ) as resposta_http:
            conteudo = resposta_http.read().decode(
                "utf-8"
            )

            return json.loads(
                conteudo
            )

    def ler_erro_http(
        self,
        erro: error.HTTPError,
    ) -> str:
        """Extrai uma mensagem legível de um erro HTTP."""

        try:
            conteudo = erro.read().decode(
                "utf-8"
            )

        except Exception:
            conteudo = ""

        if conteudo:
            try:
                resposta = json.loads(
                    conteudo
                )

                mensagem = resposta.get(
                    "mensagem"
                )

                if mensagem:
                    return str(
                        mensagem
                    )

            except json.JSONDecodeError:
                return conteudo[
                    :500
                ]

        return (
            "O webhook do Google Sheets retornou "
            f"o código HTTP {erro.code}."
        )