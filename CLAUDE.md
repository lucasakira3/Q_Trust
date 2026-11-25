# QTrust: contexto do projeto

Notas para retomar o trabalho em qualquer computador. O Claude Code lê este arquivo automaticamente.

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

- `dados/gerar_base.py` → gera `dados/mensagens_qtrust.csv` (500 mensagens fictícias, seed 42; 196 baixo, 131 médio, 173 alto; 4% de ruído nos rótulos).
- `src/treinar.py` → baseline clássico (regressão logística) + VQC no simulador; salva `modelos/` (ignorado no Git) e `interface/public/predicoes.json`. `--sem-vqc` treina só o clássico.
- `src/qtrust_model.py` → circuito da Bea: RY(π·x) + CX em cadeia + segunda camada RY, simulado no Aer. Não tem parâmetros treináveis (é uma codificação, não um classificador).
- `src/experimentos/qnn_encoding_bea.py` → experimento em andamento (ver abaixo).
- `interface/` → React + Vite. `npm install` e `npm run dev` (http://localhost:5173). Lê `public/predicoes.json` e mostra tabela, filtros e cálculo passo a passo por mensagem.
- `instalar.bat` / `instalar.sh` → criam o `.venv` e instalam `requirements.txt`.

## Estado do modelo (25/11/2026)

| Abordagem | Acurácia no teste |
|---|---|
| Regressão logística (baseline) | 84% |
| VQC padrão: ZZFeatureMap + RealAmplitudes, COBYLA 60 iter | 46% |
| VQC padrão com codificação por ângulo (RY), reps 2–3, COBYLA 80 iter | 52–54% |
| EstimatorQNN + L-BFGS-B (gradientes) | interrompido: lento demais (20+ min sem terminar) |
| EstimatorQNN + codificação da Bea + COBYLA 150 | não concluído (interrompido) |

Diagnóstico: no VQC padrão o custo quase não cai. A suspeita é a forma como ele converte as medições em 3 classes (paridade/contagem de bits). Por isso o próximo teste lê ⟨Z⟩ de um qubit por classe.

`predicoes.json` no repositório ainda não tem resultados do VQC (gerado com `--sem-vqc`).

## Próximos passos

1. Rodar `src/experimentos/qnn_encoding_bea.py` com progresso ao vivo e ver se passa de 54%.
2. Se melhorar, levar essa arquitetura para `src/treinar.py` e regerar `predicoes.json` com o VQC.
3. Conexão com IBM Quantum: o commit da Bea cita “conexão IBM”, mas `qtrust_model.py` só usa o simulador. Combinar com ela.
4. Fixar versões de `qiskit-aer` (0.18.4) e `qiskit-ibm-runtime` (0.52.1) no `requirements.txt`, se a Bea concordar.

## Apresentação

Deck “QTrust” (15 slides) no Claude: https://claude.ai/artifact/EagEFEgWppSoPwGphzTyct (privado; só abre logado na conta do Lucas).

- Identidade visual: paleta Qiskit + azul de cibersegurança. Roxos #6929C4 / #A56EFF / #8A3FFC; azuis #0F62FE / #33B1FF; fundo navy #0B1020; alerta #FF8389. Fontes IBM Plex Sans e IBM Plex Mono.
- Logo: esfera quântica com órbita e cadeado, wordmark “QTrust” e o lema “Quantum Security”.
- Base teórica: Weinberg & Faccia, “Quantum Algorithms: A New Frontier in Financial Crime Prevention”, arXiv:2403.18322 (2024). Usado nos slides “Por que quântico”, “Construção” e “Próximos passos”. Discurso honesto: QML é uma fronteira promissora; a vantagem prática ainda não está demonstrada, e o QTrust mede isso num problema real.
- Arquitetura apresentada: hardware IBM só no treino e na validação (fila de minutos); a resposta em tempo real usa o circuito já treinado em simulador. Sinais extraídos no aparelho; só o vetor de 4 números sai do dispositivo (LGPD).
