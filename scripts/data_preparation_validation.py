"""Preparação e validação dos datasets do case técnico."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class PreparadorDados:
    """Lê, valida, limpa e cria métricas derivadas."""

    COLUNAS_ORIGINAIS = {
        "Data": "data",
        "Grupos de usuários": "grupo",
        "Parceiro": "parceiro",
        "compradores": "compradores",
        "comissão": "comissao",
        "cashback": "cashback",
        "vendas totais": "vendas_totais",
    }

    COLUNAS_MONETARIAS = [
        "comissao",
        "cashback",
        "vendas_totais",
    ]

    def executar(
        self,
        caminho_arquivo: str | Path,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Executa toda a preparação do dataset."""

        caminho = Path(caminho_arquivo)

        relatorio = {
            "arquivo": caminho.name,
            "status": "valido",
            "linhas_iniciais": 0,
            "linhas_finais": 0,
            "linhas_removidas": 0,
            "parceiro": None,
            "grupos": [],
            "datas": 0,
            "amostras_por_grupo": {},
            "valores_ausentes": {},
            "duplicatas": 0,
            "warnings": [],
            "erros": [],
        }

        if not caminho.exists():
            relatorio["status"] = "invalido"
            relatorio["erros"].append(
                f"Arquivo não encontrado: {caminho}"
            )
            return pd.DataFrame(), relatorio

        try:
            dados = pd.read_csv(
                caminho,
                encoding="utf-8-sig",
            )
        except Exception as erro:
            relatorio["status"] = "invalido"
            relatorio["erros"].append(
                f"Erro ao ler o arquivo: {erro}"
            )
            return pd.DataFrame(), relatorio

        relatorio["linhas_iniciais"] = len(dados)

        if dados.empty:
            relatorio["status"] = "invalido"
            relatorio["erros"].append(
                "O arquivo está vazio."
            )
            return dados, relatorio

        dados = self.validar_colunas(
            dados,
            relatorio,
        )

        if relatorio["status"] == "invalido":
            return pd.DataFrame(), relatorio

        dados = self.converter_dados(dados)
        dados = self.remover_linhas_invalidas(
            dados,
            relatorio,
        )

        if dados.empty:
            relatorio["status"] = "invalido"
            relatorio["erros"].append(
                "Nenhuma linha válida permaneceu."
            )
            return dados, relatorio

        dados = self.check_compradores(
            dados,
            relatorio,
        )

        dados = self.criar_metricas(
            dados,
            relatorio,
        )

        self.check_duplicatas(
            dados,
            relatorio,
        )

        self.check_valores_negativos(
            dados,
            relatorio,
        )

        self.check_parceiros(
            dados,
            relatorio,
        )

        self.check_grupos(
            dados,
            relatorio,
        )

        dados = dados.sort_values(
            ["data", "grupo"]
        ).reset_index(drop=True)

        self.finalizar_relatorio(
            dados,
            relatorio,
        )

        return dados, relatorio

    def validar_colunas(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> pd.DataFrame:
        """Confere e renomeia as colunas esperadas."""

        colunas_faltantes = [
            coluna
            for coluna in self.COLUNAS_ORIGINAIS
            if coluna not in dados.columns
        ]

        if colunas_faltantes:
            relatorio["status"] = "invalido"
            relatorio["erros"].append(
                "Colunas ausentes: "
                + ", ".join(colunas_faltantes)
            )
            return dados

        dados = dados.rename(
            columns=self.COLUNAS_ORIGINAIS
        )

        return dados[
            list(self.COLUNAS_ORIGINAIS.values())
        ].copy()

    def converter_dados(
        self,
        dados: pd.DataFrame,
    ) -> pd.DataFrame:
        """Converte datas, números e textos."""

        dados = dados.copy()

        dados["data"] = pd.to_datetime(
            dados["data"],
            errors="coerce",
        )

        dados["grupo"] = (
            dados["grupo"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

        dados["parceiro"] = (
            dados["parceiro"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

        dados["compradores"] = pd.to_numeric(
            dados["compradores"],
            errors="coerce",
        )

        for coluna in self.COLUNAS_MONETARIAS:
            dados[coluna] = dados[coluna].apply(
                self.converter_valores
            )

        return dados

    def converter_valores(
        self,
        valor: Any,
    ) -> float:
        """Converte valores como 'R$ 10.273' para 10273."""

        if pd.isna(valor):
            return np.nan

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = (
            str(valor)
            .replace("R$", "")
            .replace(" ", "")
            .strip()
        )

        if not texto:
            return np.nan

        if "," in texto:
            texto = (
                texto
                .replace(".", "")
                .replace(",", ".")
            )
        else:
            texto = texto.replace(".", "")

        try:
            return float(texto)
        except ValueError:
            return np.nan

    def remover_linhas_invalidas(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> pd.DataFrame:
        """Remove linhas com qualquer valor ausente ou inválido."""

        ausentes = dados.isna().sum()

        relatorio["valores_ausentes"] = {
            coluna: int(quantidade)
            for coluna, quantidade in ausentes.items()
            if quantidade > 0
        }

        for coluna, quantidade in relatorio[
            "valores_ausentes"
        ].items():

            mensagem = (
                f"{quantidade} linhas com {coluna} "
                "ausente ou inválido foram removidas."
            )

            if coluna == "grupo":
                relatorio["erros"].append(mensagem)
            else:
                relatorio["warnings"].append(mensagem)

        return dados.dropna().copy()

    def check_compradores(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> pd.DataFrame:
        """Remove compradores fracionários."""

        dados = dados.copy()

        fracionarios = dados["compradores"] % 1 != 0
        quantidade = int(fracionarios.sum())

        if quantidade:
            relatorio["warnings"].append(
                f"{quantidade} linhas com compradores "
                "fracionários foram removidas."
            )

            dados = dados.loc[
                ~fracionarios
            ].copy()

        dados["compradores"] = (
            dados["compradores"].astype(int)
        )

        return dados

    def check_duplicatas(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> None:
        """Conta linhas duplicadas sem removê-las."""

        quantidade = int(
            dados.duplicated().sum()
        )

        relatorio["duplicatas"] = quantidade

        if quantidade:
            relatorio["warnings"].append(
                f"Foram encontradas {quantidade} "
                "linhas duplicadas."
            )

    def check_valores_negativos(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> None:
        """Sinaliza valores numéricos negativos."""

        colunas = [
            "compradores",
            "comissao",
            "cashback",
            "vendas_totais",
        ]

        for coluna in colunas:
            quantidade = int(
                (dados[coluna] < 0).sum()
            )

            if quantidade:
                relatorio["warnings"].append(
                    f"{quantidade} valores negativos "
                    f"encontrados em {coluna}."
                )

    def check_parceiros(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> None:
        """Verifica o parceiro presente no arquivo."""

        parceiros = sorted(
            dados["parceiro"].unique().tolist()
        )

        if len(parceiros) == 1:
            relatorio["parceiro"] = parceiros[0]
        else:
            relatorio["warnings"].append(
                "Mais de um parceiro foi encontrado: "
                + ", ".join(parceiros)
            )

    def check_grupos(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> None:
        """Verifica quantidade e presença dos grupos."""

        grupos = sorted(
            dados["grupo"].unique().tolist()
        )

        relatorio["grupos"] = grupos

        if len(grupos) < 2:
            relatorio["status"] = "invalido"
            relatorio["erros"].append(
                "O dataset deve possuir pelo menos dois grupos."
            )
            return

        tabela_datas = dados.pivot_table(
            index="data",
            columns="grupo",
            values="compradores",
            aggfunc="size",
            fill_value=0,
        )

        datas_incompletas = int(
            (tabela_datas == 0)
            .any(axis=1)
            .sum()
        )

        if datas_incompletas:
            relatorio["warnings"].append(
                f"{datas_incompletas} datas não possuem "
                "todos os grupos."
            )

    def criar_metricas(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> pd.DataFrame:
        """Cria métricas derivadas."""

        dados = dados.copy()

        dados["receita_liquida"] = (
            dados["comissao"]
            - dados["cashback"]
        )

        dados["vendas_por_comprador"] = (
            dados["vendas_totais"]
            / dados["compradores"].replace(0, np.nan)
        )

        dados["comissao_por_comprador"] = (
            dados["comissao"]
            / dados["compradores"].replace(0, np.nan)
        )

        dados["cashback_por_comprador"] = (
            dados["cashback"]
            / dados["compradores"].replace(0, np.nan)
        )

        dados["receita_liquida_por_comprador"] = (
            dados["receita_liquida"]
            / dados["compradores"].replace(0, np.nan)
        )

        dados["taxa_comissao"] = (
            dados["comissao"]
            / dados["vendas_totais"].replace(0, np.nan)
        )

        dados["taxa_cashback"] = (
            dados["cashback"]
            / dados["vendas_totais"].replace(0, np.nan)
        )

        dados["margem_liquida"] = (
            dados["receita_liquida"]
            / dados["vendas_totais"].replace(0, np.nan)
        )

        if (dados["compradores"] == 0).any():
            relatorio["warnings"].append(
                "Existem linhas com zero compradores. "
                "Métricas por comprador ficaram ausentes."
            )

        if (dados["vendas_totais"] == 0).any():
            relatorio["warnings"].append(
                "Existem linhas com vendas totais iguais a zero. "
                "As taxas ficaram ausentes."
            )

        return dados

    def finalizar_relatorio(
        self,
        dados: pd.DataFrame,
        relatorio: dict,
    ) -> None:
        """Completa o relatório final."""

        relatorio["linhas_finais"] = len(dados)

        relatorio["linhas_removidas"] = (
            relatorio["linhas_iniciais"]
            - relatorio["linhas_finais"]
        )

        relatorio["datas"] = int(
            dados["data"].nunique()
        )

        relatorio["amostras_por_grupo"] = {
            grupo: int(quantidade)
            for grupo, quantidade in (
                dados["grupo"]
                .value_counts()
                .sort_index()
                .items()
            )
        }

        if relatorio["status"] == "invalido":
            return

        if (
            relatorio["warnings"]
            or relatorio["erros"]
        ):
            relatorio["status"] = "valido_com_warnings"
        else:
            relatorio["status"] = "valido"