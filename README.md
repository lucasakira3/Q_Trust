# QTrust

**Detecção de golpes em mensagens de Pix com Quantum Machine Learning.**

O QTrust é um motor de risco que classifica mensagens de WhatsApp em risco **baixo**, **médio** ou **alto** de golpe via Pix. Cada mensagem vira 4 sinais numéricos, um por qubit, e um classificador quântico variacional (VQC) feito em Qiskit decide o nível de risco. Para medir o que o modelo quântico entrega de fato, o mesmo problema é resolvido por um baseline clássico, e o VQC roda tanto no simulador quanto em um computador quântico real da IBM.

> Projeto acadêmico. A base de mensagens é **sintética**: os resultados validam o pipeline, não o desempenho em mensagens reais.

## Resultados

Conjunto de teste: 125 mensagens (25% da base, estratificado: 49 de risco baixo, 33 de médio e 43 de alto).

| Modelo | Onde rodou | Acurácia | F1 (risco alto) |
|---|---|---|---|
| Regressão logística (baseline) | CPU | **84%** | 92,3% |
| VQC | Simulador ideal do Qiskit | 48% | 45,1% |
| VQC | IBM Quantum `ibm_fez` (Heron r2, 156 qubits) | 45% | — |

**Conclusão.** O modelo clássico teve desempenho superior ao VQC. Apesar disso, o modelo quântico foi implementado, treinado, avaliado em simulador ideal e executado em hardware quântico real da IBM, o que permitiu comparar as saídas nas duas plataformas. Os resultados mostram os limites da configuração quântica usada e a importância de comparar sempre com um modelo clássico.

### Análise

- **O VQC deixa golpes passarem.** Dos 43 golpes de risco alto, o clássico detecta 42 e não classifica nenhum como risco baixo. O VQC detecta 16 e classifica 24 como risco baixo.
- **Tendência ao baixo.** O VQC responde "baixo" em 64% das mensagens. A leitura das 3 classes usa o resto da divisão por 3 do resultado medido (um inteiro de 0 a 15), o que dá ao baixo 6 dos 16 resultados possíveis, contra 5 para médio e 5 para alto.
- **Pouca confiança.** A classe escolhida pelo VQC tem, em média, 45% de probabilidade, contra 77% no clássico.
- **Treino estagnado.** O custo caiu de 1,75 para 1,47 até a iteração 30 e chegou só a 1,43 na iteração 50.
- **O ruído não é o gargalo.** No hardware, a acurácia caiu apenas 3 pontos em relação ao simulador ideal (de 48% para 45%). O limite está no modelo.
- **Ainda assim, o VQC aprende algo:** 48% de acurácia, contra 39% de quem chutasse sempre a classe mais comum.

## Como funciona

| Sinal | Qubit | Exemplo |
|---|---|---|
| x1 urgência | q0 | "Preciso disso agora, é urgente!" |
| x2 pedido de transferência | q1 | "Faz um Pix de R$ 500 para essa chave." |
| x3 promessa de prêmio | q2 | "Você foi sorteado! Pague a taxa para liberar." |
| x4 falsa identidade | q3 | "Oi, mãe, troquei de número. Salva esse." |

- **Codificação:** cada sinal (de 0 a 1) vira um ângulo de 0 a π no `ZZFeatureMap` (1 repetição), que também emaranha os qubits.
- **Classificador:** ansatz `RealAmplitudes` (2 repetições, 12 parâmetros θ), treinado pelo otimizador COBYLA por 50 iterações, com o `VQC` do `qiskit-machine-learning`.
- **Leitura:** cada medição gera um inteiro de 0 a 15, e a classe é esse inteiro módulo 3 (padrão do `VQC` com `output_shape=3`).
- **Baseline:** regressão logística multinomial (scikit-learn) com os mesmos 4 sinais.
- **Hardware:** o circuito treinado é transpilado para as portas nativas do `ibm_fez` (RZ, √X e CZ) e executado com 1.024 shots pelo `SamplerV2` do `qiskit-ibm-runtime`.

## Estrutura

```
dados/
  gerar_base.py            gera a base sintética (seed 42)
  mensagens_qtrust.csv     500 mensagens com os 4 sinais e o risco
src/
  treinar.py               treina o baseline e o VQC no simulador e gera predicoes.json
  avaliar_ibm.py           avalia o VQC no simulador ideal e compara com o piloto na IBM
  executar_ibm.py          roda o VQC treinado em uma mensagem no ibm_fez
  teste_bell.py            testa a conexão com o hardware IBM (circuito de Bell)
interface/                 React + Vite: tabela, filtros e cálculo passo a passo por mensagem
instalar.bat, instalar.sh  criam o .venv e instalam o requirements.txt
```

A pasta `modelos/`, com os pesos e as métricas gerados, fica fora do Git.

## Como rodar

### 1. Instalação

Pré-requisito: Python 3.11 ou mais novo (testado com 3.14), instalado a partir de [python.org](https://www.python.org/downloads/). No Windows, marque "Add Python to PATH" na instalação.

- **Windows:** dê dois cliques em `instalar.bat`.
- **Mac/Linux:** rode `./instalar.sh` no terminal.

O script cria o ambiente virtual `.venv` e instala as versões de `requirements.txt`. Depois, ative o ambiente:

```bash
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
```

### 2. Treinar e comparar no simulador

```bash
python -u src/treinar.py --iter 50
```

Treina o baseline e o VQC, salva `modelos/vqc_pesos.npy` e `modelos/resultados.json` e gera `interface/public/predicoes.json`. Sem `--iter`, usa 100 iterações. Com `--sem-vqc`, treina só o baseline, o que é rápido e serve para testar a interface.

### 3. Avaliar no simulador ideal

```bash
python -u src/avaliar_ibm.py
```

Calcula as métricas do VQC no conjunto de teste com o simulador de vetor de estado (probabilidades exatas, sem amostragem) e compara uma mensagem com o resultado do piloto no hardware, salvo em `modelos/resultado_piloto_ibm.json`. Sem esse arquivo, mude `USE_SAVED_PILOT` para `False` para ver só o simulador. Por padrão, o script não envia jobs à IBM. Para uma nova execução no hardware, mude `RUN_HARDWARE` para `True`.

### 4. Rodar no hardware IBM Quantum

É preciso uma conta no [IBM Quantum Platform](https://quantum.cloud.ibm.com/). Salve a credencial uma vez:

```python
from qiskit_ibm_runtime import QiskitRuntimeService

QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token="SEU_TOKEN",
    instance="SEU_CRN",
    set_as_default=True,
)
```

Depois:

```bash
python src/teste_bell.py      # confere a conexão com um circuito de Bell
python src/executar_ibm.py    # roda o VQC treinado (modelos/vqc_pesos.npy) em uma mensagem
```

Os scripts usam o backend `ibm_fez`, e cada job consome tempo de QPU da cota da conta.

### 5. Interface

Requer [Node.js](https://nodejs.org/) 20 ou mais novo.

```bash
cd interface
npm install        # só na primeira vez
npm run dev        # abre em http://localhost:5173
```

A interface lê `interface/public/predicoes.json` e mostra cada mensagem, os 4 sinais, o resultado de cada modelo e o cálculo passo a passo.

## Base de dados

| Coluna | Descrição |
|---|---|
| `texto` | mensagem simulada |
| `urgencia` | sinal x1, de 0 a 1 |
| `transferencia` | sinal x2, de 0 a 1 |
| `premio` | sinal x3, de 0 a 1 |
| `falsa_identidade` | sinal x4, de 0 a 1 |
| `risco` | 0 = baixo, 1 = médio, 2 = alto |
| `rotulo` | risco por extenso |

São 500 mensagens (196 de risco baixo, 131 de médio e 173 de alto), com 4% de ruído nos rótulos. Todos os nomes, bancos, valores e chaves Pix são inventados. Os sinais são atribuídos pelo gerador, simulando a saída de um extrator.

Para gerar outra base: `python dados/gerar_base.py 1000`

## Limitações

- A base é sintética e os sinais vêm do gerador, então os números não medem o desempenho em mensagens reais.
- A extração dos sinais a partir do texto ainda não está implementada: o MVP parte dos 4 sinais prontos.
- No hardware atual, a fila e o ruído impedem a análise em tempo real. A arquitetura prevista usa o hardware IBM para treino e validação, e o circuito já treinado em simulador para responder ao usuário.

## Referência

Weinberg & Faccia (2024). *Quantum Algorithms: A New Frontier in Financial Crime Prevention*. [arXiv:2403.18322](https://arxiv.org/abs/2403.18322).

## Equipe

- Lucas Akira ([lucasakira3](https://github.com/lucasakira3))
- Bea ([biihz](https://github.com/biihz))
