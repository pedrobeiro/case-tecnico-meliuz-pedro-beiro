@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo  Analisador de Testes A/B - Case Meliuz
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado.
    echo Instale Python 3.11 ou superior e tente novamente.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv .venv

    if errorlevel 1 (
        echo Nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

echo Atualizando o pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo Falha ao instalar as dependencias.
    pause
    exit /b 1
)

if not exist ".env" (
    echo.
    echo O arquivo .env ainda nao existe.

    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo Um arquivo .env foi criado a partir do .env.example.
        echo Preencha a chave GEMINI_API_KEY antes de continuar.
    ) else (
        echo Crie um arquivo .env com as configuracoes necessarias.
    )

    echo.
    pause
    exit /b 1
)

echo.
echo Iniciando a aplicacao...
".venv\Scripts\python.exe" -m streamlit run scripts\app.py

endlocal