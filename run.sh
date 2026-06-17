#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

echo "============================================"
echo " Analisador de Testes A/B - Case Méliuz"
echo "============================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 não foi encontrado."
    echo "Instale Python 3.11 ou superior."
    exit 1
fi

if [ ! -f ".venv/bin/python" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
fi

echo "Atualizando o pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Instalando dependências..."
.venv/bin/python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo
        echo "O arquivo .env foi criado a partir do .env.example."
        echo "Preencha a variável GEMINI_API_KEY e execute novamente."
        exit 1
    fi

    echo "Arquivo .env não encontrado."
    exit 1
fi

echo
echo "Iniciando a aplicação..."
.venv/bin/python -m streamlit run scripts/app.py