# QTrust

Motor de risco baseado em Quantum Machine Learning (Qiskit) para identificar golpes em mensagens e transações via Pix, com integração prevista em WhatsApp Web, apps de banco e Android.

## Estrutura

- `dados/gerar_base.py` — gera a base fictícia de mensagens (reproduzível, seed 42).
- `dados/mensagens_qtrust.csv` — 500 mensagens fictícias com os 4 sinais e o nível de risco.

## Base de dados

| Coluna | Descrição |
|---|---|
| `texto` | mensagem simulada |
| `urgencia` | sinal x1, 0 a 1 |
| `transferencia` | sinal x2, 0 a 1 |
| `premio` | sinal x3, 0 a 1 |
| `falsa_identidade` | sinal x4, 0 a 1 |
| `risco` | 0 = baixo, 1 = médio, 2 = alto |
| `rotulo` | risco por extenso |

Todos os nomes, bancos, valores e chaves Pix são inventados. Os sinais são atribuídos pelo gerador, simulando a saída de um extrator; servem para validar o pipeline do MVP, não para medir desempenho em mensagens reais.

Para gerar outra base: `python dados/gerar_base.py 1000`

## Instalação

Pré-requisito: Python 3.11 ou mais novo (testado com 3.14), instalado a partir de [python.org](https://www.python.org/downloads/). No Windows, marque “Add Python to PATH” na instalação.

- **Windows:** dê dois cliques em `instalar.bat`.
- **Mac/Linux:** rode `./instalar.sh` no terminal.

O script cria o ambiente virtual `.venv` e instala as versões exatas de `requirements.txt`.

## Treinar o modelo

```bash
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
python src/treinar.py --iter 100
```

O script treina um baseline clássico (regressão logística) e o VQC no simulador do Qiskit, e salva os pesos e as métricas em `modelos/`.

**Status:** o pipeline funciona de ponta a ponta, mas o VQC ainda não está bem ajustado. Nos primeiros testes, o baseline clássico chegou a 84% de acurácia e o VQC ficou entre 46% e 54%. Próximo passo: melhorar a codificação dos sinais e a leitura das classes no circuito.
