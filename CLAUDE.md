# QTrust: contexto do projeto

Notas para retomar o trabalho em qualquer computador. O Claude Code lê este arquivo automaticamente. A documentação pública do projeto está no `README.md`.

## O que é

Motor de risco com Quantum Machine Learning (Qiskit) para identificar golpes em mensagens e transações via Pix. Visão de produto: extensão para WhatsApp Web, API para bancos e fintechs (consultada antes de confirmar um Pix) e app Android. O usuário vê o nível de risco (baixo, médio ou alto) e os sinais que o justificam.

Quatro sinais por mensagem, cada um de 0 a 1, um por qubit:
x1 urgência · x2 pedido de transferência · x3 promessa de prêmio · x4 falsa identidade.

Equipe: Lucas Akira (lucasakira3) e Bea (biihz).

## Preferências do Lucas

- Responder em português.
- **Não** adicionar a linha `Co-Authored-By: Claude` nos commits.
- Treinos longos devem mostrar progresso ao vivo: rodar com `python -u` em segundo plano e ir reportando, nunca travar o terminal por minutos sem saída.
- Antes de mexer em arquivos da Bea, perguntar.

## Estrutura

- `dados/gerar_base.py` → gera `dados/mensagens_qtrust.csv` (500 mensagens fictícias, seed 42; 196 baixo, 131 médio, 173 alto; 4% de ruído nos rótulos). Split 75/25 estratificado, seed 42: 125 mensagens de teste (49 baixo, 33 médio, 43 alto).
- `src/treinar.py` → baseline clássico (regressão logística) + VQC (ZZFeatureMap reps 1 + RealAmplitudes reps 2, 12 parâmetros, COBYLA). Os resultados publicados usam `--iter 50`. Salva `modelos/` (fora do Git) e `interface/public/predicoes.json`. `--sem-vqc` treina só o clássico.
- `src/avaliar_ibm.py` (Bea) → avalia o VQC no simulador ideal (Statevector) e compara uma mensagem com o piloto IBM salvo em `modelos/resultado_piloto_ibm.json`. Não envia jobs, a menos que `RUN_HARDWARE = True`.
- `src/executar_ibm.py` (Bea) → roda o VQC treinado em uma mensagem no `ibm_fez`. As features estão fixas no código (mensagem id 1: 0,81 · 0,89 · 0,42 · 0,86).
- `src/teste_bell.py` (Bea) → teste de conexão com o hardware usando um circuito de Bell.
- `interface/` → React + Vite. `npm install` e `npm run dev` (http://localhost:5173). Lê `public/predicoes.json` e mostra tabela, filtros e cálculo passo a passo por mensagem.
- `instalar.bat` / `instalar.sh` → criam o `.venv` e instalam `requirements.txt`.

## Estado do modelo (25/11/2026)

| Modelo | Plataforma | Acurácia (125 msgs de teste) | F1 risco alto |
|---|---|---|---|
| Regressão logística | CPU | 84% | 92,31% |
| VQC | simulador ideal (Statevector, `avaliar_ibm.py`) | 48% | 45,07% |
| VQC | simulador com 1.024 shots (`treinar.py`) | 46,4% | 42,25% |
| VQC | hardware `ibm_fez` | 45% | — |

- O `output_shape=3` que a Bea pôs no `treinar.py` é necessário: sem ele, o VQC interpreta a medição com paridade de 2 saídas e nunca prevê risco alto. Os números antigos (46% e 52–54% com codificação RY) foram medidos com esse erro e não valem mais.
- A leitura das classes é o índice medido módulo 3, então o baixo recebe 6 dos 16 estados. O VQC prevê baixo em 64% das mensagens e classifica 24 dos 43 golpes de risco alto como baixo (o clássico, 0).
- Custo do COBYLA: 1,75 → 1,47 (iteração 30) → 1,43 (iteração 50).
- Confiança média na classe escolhida: 45% no VQC, 77% no clássico. Chutar sempre a classe mais comum dá 39%.
- Job de exemplo no hardware (25/11, 19:54): mensagem id 1, qubits físicos 141 a 144, 166 portas nativas (67 RZ, 69 √X, 30 CZ). Distribuição em 3 classes: 35/23/42 no `ibm_fez` contra 40/20/40 no simulador ideal.

## Pendências

1. Responder à Bea sobre o `treinar.py`: a correção com `output_shape=3` está certa (ver acima).
2. O `avaliar_ibm.py` assume que o piloto foi a 1ª mensagem do teste (id 73, sinais 0,87 · 0,79 · 0,01 · 0,97), mas o job das 19:54 rodou a id 1: os ângulos RZ do circuito transpilado codificam 0,81, 0,89 e 0,42. Conferir o `job_id` em `modelos/resultado_piloto_ibm.json`.
3. O script que rodou as 125 mensagens de teste no hardware (45%) ainda não está no repositório. Pedir para a Bea versionar.
4. Fixar versões de `qiskit-aer` (0.18.4) e `qiskit-ibm-runtime` (0.52.1) no `requirements.txt`, se a Bea concordar.
5. Melhorar o modelo: trocar a leitura das classes (por exemplo, ⟨Z⟩ de um qubit por classe ou um agrupamento balanceado dos 16 estados) e a codificação, e medir de novo contra o mesmo baseline.

## Apresentação

Deck "QTrust" (19 slides) no Claude: https://claude.ai/artifact/EagEFEgWppSoPwGphzTyct (privado; só abre logado na conta do Lucas). O PDF é exportado pelo menu do deck, e o último slide traz o link deste repositório.

- Identidade visual: paleta Qiskit + azul de cibersegurança. Roxos #6929C4 / #A56EFF / #8A3FFC; azuis #0F62FE / #33B1FF; fundo navy #0B1020; alerta #FF8389. Fontes IBM Plex Sans e IBM Plex Mono.
- Logo: esfera quântica com órbita e cadeado, wordmark "QTrust" e o lema "Quantum Security".
- Base teórica: Weinberg & Faccia, "Quantum Algorithms: A New Frontier in Financial Crime Prevention", arXiv:2403.18322 (2024). Usado nos slides "Por que quântico", "Construção" e "Próximos passos". Discurso honesto: QML é uma fronteira promissora; a vantagem prática ainda não está demonstrada, e o QTrust mede isso num problema real.
- Arquitetura apresentada: hardware IBM só no treino e na validação (fila de minutos); a resposta em tempo real usa o circuito já treinado em simulador. Sinais extraídos no aparelho; só o vetor de 4 números sai do dispositivo (LGPD).
- Slides de resultados: 10 Resultados (84% / 48% / 45%), 11 Hardware (exemplo de uma mensagem e 45% contra 48%), 12 circuito como rodou no chip (4 faixas), 13 Análise (por que o VQC fica atrás).

## Conclusão científica do QTrust

O modelo clássico de Regressão Logística apresentou desempenho superior ao Variational Quantum Classifier (VQC) na classificação das mensagens do dataset QTrust, alcançando acurácia de 84% e F1-score de 92,31% para a classe Alto, em comparação aos 48% de acurácia e 45,07% de F1-score do VQC. Apesar do desempenho inferior, o modelo quântico foi implementado, treinado e avaliado em simulador ideal, além de ter sido executado em hardware quântico real da IBM, permitindo observar diferenças entre as distribuições de saída obtidas nas duas plataformas. Os resultados evidenciam as limitações da configuração quântica utilizada e demonstram a importância de estabelecer comparações com modelos clássicos.

O VQC melhorou quando as iterações subiram de 10 para 30, mas estabilizou entre 30 e 50, permanecendo inferior ao baseline clássico.
