"""
Treina o motor de risco do QTrust no simulador e compara com um baseline clássico.

Uso:
    python src/treinar.py                 (100 iterações)
    python src/treinar.py --iter 200

Saídas:
    modelos/vqc_pesos.npy             parâmetros θ treinados do VQC
    modelos/resultados.json           métricas do clássico e do quântico
    interface/public/predicoes.json   resultado de cada mensagem, lido pela interface
"""
import argparse
import json
import time
from datetime import datetime
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
INTERFACE = RAIZ / "interface" / "public" / "predicoes.json"
SINAIS = ["urgencia", "transferencia", "premio", "falsa_identidade"]
CLASSES = ["baixo", "medio", "alto"]
ESCALA = np.pi  # sinais de 0 a 1 viram ângulos de 0 a π nos qubits


def carregar():
    df = pd.read_csv(DADOS)
    idx_tr, idx_te = train_test_split(
        np.arange(len(df)), test_size=0.25, stratify=df["risco"], random_state=42
    )
    return df, idx_tr, idx_te


def avaliar(nome, y_true, y_pred, segundos):
    acc = accuracy_score(y_true, y_pred)
    f1_alto = f1_score(y_true, y_pred, labels=[2], average="macro")
    print(f"\n=== {nome} ===  acurácia {acc:.3f} | F1 risco alto {f1_alto:.3f} | treino {segundos:.1f}s")
    print(classification_report(y_true, y_pred, target_names=CLASSES, digits=3, zero_division=0))
    return {"acuracia": round(acc, 4), "f1_alto": round(f1_alto, 4), "treino_s": round(segundos, 1)}


def probs_vqc(vqc, X):
    """Probabilidade de cada classe segundo o VQC (cai para one-hot se a versão não expõe predict_proba)."""
    try:
        return np.asarray(vqc.predict_proba(X))
    except (AttributeError, NotImplementedError):
        pred = np.asarray(vqc.predict(X)).astype(int).ravel()
        return np.eye(len(CLASSES))[pred]


def exportar(df, idx_tr, clf, p_cls, p_vqc, metricas, vqc_info):
    treino = set(idx_tr.tolist())
    linhas = []
    for i, row in df.iterrows():
        linhas.append({
            "id": int(i),
            "texto": row["texto"],
            "sinais": {s: float(row[s]) for s in SINAIS},
            "risco_real": int(row["risco"]),
            "conjunto": "treino" if i in treino else "teste",
            "classico": {"pred": int(p_cls[i].argmax()), "probs": [round(float(v), 4) for v in p_cls[i]]},
            "vqc": None if p_vqc is None else
                   {"pred": int(p_vqc[i].argmax()), "probs": [round(float(v), 4) for v in p_vqc[i]]},
        })
    saida = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "classes": CLASSES,
        "sinais": SINAIS,
        "metricas": metricas,
        "classico": {
            "modelo": "Regressão logística multinomial",
            "coef": [[round(float(v), 4) for v in linha] for linha in clf.coef_],
            "intercepto": [round(float(v), 4) for v in clf.intercept_],
        },
        "vqc": vqc_info,
        "linhas": linhas,
    }
    INTERFACE.parent.mkdir(parents=True, exist_ok=True)
    INTERFACE.write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
    print(f"Resultados por mensagem salvos em {INTERFACE}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, default=100, help="iterações do otimizador COBYLA")
    ap.add_argument("--sem-vqc", action="store_true", help="treina só o baseline (rápido, para testar a interface)")
    args = ap.parse_args()

    df, idx_tr, idx_te = carregar()
    X = df[SINAIS].to_numpy()
    y = df["risco"].to_numpy()
    X_tr, X_te, y_tr, y_te = X[idx_tr], X[idx_te], y[idx_tr], y[idx_te]
    print(f"Treino: {len(X_tr)} mensagens | Teste: {len(X_te)} mensagens")

    # Baseline clássico
    t0 = time.time()
    clf = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
    metricas = {"classico": avaliar("Baseline clássico (regressão logística)", y_te, clf.predict(X_te), time.time() - t0)}
    p_cls = clf.predict_proba(X)

    p_vqc, vqc_info = None, None
    if not args.sem_vqc:
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
        vqc.fit(X_tr * ESCALA, y_tr)
        tempo_vqc = time.time() - t0
        y_pred = np.asarray(vqc.predict(X_te * ESCALA)).astype(int).ravel()
        metricas["vqc_simulador"] = avaliar("VQC quântico (simulador)", y_te, y_pred, tempo_vqc)
        print(f"Custo: {historico[0]:.3f} -> {historico[-1]:.3f}")
        p_vqc = probs_vqc(vqc, X * ESCALA)
        vqc_info = {
            "modelo": "VQC (ZZFeatureMap + RealAmplitudes), simulador Qiskit",
            "qubits": 4,
            "parametros": int(ansatz.num_parameters),
            "iteracoes": args.iter,
            "escala_entrada": "pi",
            "pesos": [round(float(v), 4) for v in vqc.weights],
            "custo": [round(float(c), 4) for c in historico],
        }
        MODELOS.mkdir(exist_ok=True)
        np.save(MODELOS / "vqc_pesos.npy", vqc.weights)

    MODELOS.mkdir(exist_ok=True)
    (MODELOS / "resultados.json").write_text(json.dumps(metricas, indent=2), encoding="utf-8")
    exportar(df, idx_tr, clf, p_cls, p_vqc, metricas, vqc_info)


if __name__ == "__main__":
    main()
