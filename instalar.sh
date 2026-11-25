#!/usr/bin/env bash
# Instala o ambiente do QTrust no Mac/Linux (cria .venv e instala as dependências)
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 não encontrado. Instale o Python 3.11 ou mais novo: https://www.python.org/downloads/"
  exit 1
fi

echo "Criando ambiente virtual em .venv ..."
python3 -m venv .venv
echo "Instalando dependências (pode levar alguns minutos) ..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Pronto! Para treinar o modelo:"
echo "  source .venv/bin/activate"
echo "  python src/treinar.py"
