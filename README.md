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
