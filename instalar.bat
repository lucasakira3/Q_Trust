@echo off
REM Instala o ambiente do QTrust no Windows (cria .venv e instala as dependencias)
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/
    echo Marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

echo Criando ambiente virtual em .venv ...
python -m venv .venv || goto erro
echo Instalando dependencias (pode levar alguns minutos) ...
.venv\Scripts\python -m pip install --upgrade pip || goto erro
.venv\Scripts\python -m pip install -r requirements.txt || goto erro

echo.
echo Pronto! Para treinar o modelo:
echo   .venv\Scripts\activate
echo   python src\treinar.py
pause
exit /b 0

:erro
echo.
echo Algo deu errado na instalacao. Veja a mensagem acima.
pause
exit /b 1
