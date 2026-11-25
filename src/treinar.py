"""
Treina o motor de risco do QTrust no simulador e compara com um baseline clássico.

Uso:
    python src/treinar.py                 (100 iterações)
    python src/treinar.py --iter 200

Saídas:
    modelos/vqc_pesos.npy      parâmetros θ treinados do VQC
    modelos/resultados.json    métricas do clássico e do quântico
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

from qiskit.circuit.library import real_amplitudes, zz_feature_map
from qiskit.primitives import StatevectorSampler
from qiskit_machine_learning.algorithms import VQC
from qiskit_machine_learning.optimizers import COBYLA

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "mensagens_qtrust.csv"
MODELOS = RAIZ / "modelos"
SINAIS = ["urgencia", "transferencia", "premio", "falsa_identidade"]
CLASSES = ["baixo", "medio", "alto"]


def carregar():
    df = pd.read_csv(DADOS)
    X = df[SINAIS].to_numpy()
    y = df["risco"].to_numpy()
    return train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)


def avaliar(nome, y_true, y_pred, segundos):
    acc = accuracy_score(y_true, y_pred)
    f1_alto = f1_score(y_true, y_pred, labels=[2], average="macro")
    print(f"\n=== {nome} ===  acurácia {acc:.3f} | F1 risco alto {f1_alto:.3f} | treino {segundos:.1f}s")
    print(classification_report(y_true, y_pred, target_names=CLASSES, digits=3, zero_division=0))
    return {"acuracia": round(acc, 4), "f1_alto": round(f1_alto, 4), "treino_s": round(segundos, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, default=100, help="iterações do otimizador COBYLA")
    args = ap.parse_args()

    X_tr, X_te, y_tr, y_te = carregar()
    print(f"Treino: {len(X_tr)} mensagens | Teste: {len(X_te)} mensagens")

    # Baseline clássico
    t0 = time.time()
    clf = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
    res_classico = avaliar("Baseline clássico (regressão logística)", y_te, clf.predict(X_te), time.time() - t0)

    # VQC: 4 sinais -> 4 qubits
    # Os sinais vão de 0 a 1; escalamos para 0..π para usar melhor as rotações dos qubits.
    escala = np.pi
    feature_map = zz_feature_map(feature_dimension=4, reps=1)
    ansatz = real_amplitudes(num_qubits=4, reps=2)

    historico = []
    vqc = VQC(
        sampler=StatevectorSampler(seed=42),
        feature_map=feature_map,
        ansatz=ansatz,
        optimizer=COBYLA(maxiter=args.iter),
        callback=lambda pesos, custo: historico.append(custo),
    )

    print(f"\nTreinando VQC ({ansatz.num_parameters} parâmetros θ, {args.iter} iterações)...")
    t0 = time.time()
    vqc.fit(X_tr * escala, y_tr)
    tempo_vqc = time.time() - t0
    y_pred = np.asarray(vqc.predict(X_te * escala)).astype(int).ravel()
    res_vqc = avaliar("VQC quântico (simulador)", y_te, y_pred, tempo_vqc)
    print(f"Custo: {historico[0]:.3f} -> {historico[-1]:.3f}")

    MODELOS.mkdir(exist_ok=True)
    np.save(MODELOS / "vqc_pesos.npy", vqc.weights)
    (MODELOS / "resultados.json").write_text(
        json.dumps({"classico": res_classico, "vqc_simulador": res_vqc,
                    "iteracoes": args.iter, "escala_entrada": "pi"}, indent=2),
        encoding="utf-8",
    )
    print(f"\nPesos e resultados salvos em {MODELOS}")


if __name__ == "__main__":
    main()
