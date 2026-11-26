"""QTrust — avaliação centralizada do VQC (simulador + piloto IBM Quantum).

Uso (PowerShell, dentro da pasta Q_Trust):
    python -u src/avaliar_ibm.py

Por padrão, NÃO envia novos jobs à IBM. Reutiliza o JSON do piloto já realizado.
Para uma nova execução de hardware, altere RUN_HARDWARE para True.
"""
from pathlib import Path
import json
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_recall_fscore_support
)

from qiskit import QuantumCircuit
from qiskit.circuit.library import real_amplitudes, zz_feature_map
from qiskit.quantum_info import Statevector

# IBM Runtime imports are only needed if a new hardware run is enabled.

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dados" / "mensagens_qtrust.csv"
WEIGHTS = ROOT / "modelos" / "vqc_pesos.npy"
PILOT_JSON = ROOT / "modelos" / "resultado_piloto_ibm.json"
REPORT_JSON = ROOT / "modelos" / "avaliacao_qtrust.json"

BACKEND_NAME = "ibm_fez"
SHOTS = 1024
FEATURES = ["urgencia", "transferencia", "premio", "falsa_identidade"]
CLASSES = ["baixo", "medio", "alto"]
SCALE = np.pi
TEST_SIZE = 0.25
RANDOM_STATE = 42

# Safe defaults: reuse existing pilot, never submit a new job unless explicitly enabled.
RUN_HARDWARE = False
USE_SAVED_PILOT = True


def build_circuit(feature_map, ansatz, sample, weights, measure=False):
    fm = feature_map.assign_parameters(dict(zip(feature_map.parameters, sample * SCALE)))
    an = ansatz.assign_parameters(dict(zip(ansatz.parameters, weights)))
    qc = QuantumCircuit(4)
    qc.compose(fm, inplace=True)
    qc.compose(an, inplace=True)
    if measure:
        qc.measure_all()
    return qc


def class_probabilities_from_statevector(qc):
    """Qiskit VQC default interpretation for output_shape=3: basis index % 3."""
    probabilities = Statevector.from_instruction(qc).probabilities()
    class_probs = np.zeros(3, dtype=float)
    for basis_index, prob in enumerate(probabilities):
        class_probs[basis_index % 3] += float(prob)
    return class_probs


def class_probabilities_from_counts(counts):
    """Aggregate measured bitstrings using decimal(bitstring) % 3.

    Sampler counts bitstrings are in classical-register order; for measure_all on
    the 4 logical qubits this corresponds to the VQC's integer basis index.
    """
    class_counts = np.zeros(3, dtype=float)
    total = sum(counts.values())
    if total == 0:
        raise ValueError("Counts vazios: não há medições para agregar.")
    for bitstring, count in counts.items():
        class_id = int(bitstring.replace(" ", ""), 2) % 3
        class_counts[class_id] += int(count)
    return class_counts / total


def show_probabilities(title, probs):
    print(f"\n{title}")
    for i, name in enumerate(CLASSES):
        print(f"  {name:5s}: {probs[i]:.4f} ({probs[i]*100:.2f}%)")
    print(f"  Predição: {CLASSES[int(np.argmax(probs))].upper()} (classe {int(np.argmax(probs))})")


def print_metrics(y_true, y_pred, title):
    print(f"\n{'='*55}\n{title}\n{'='*55}")
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], average=None, zero_division=0
    )
    for i, label in enumerate(CLASSES):
        print(f"{label.capitalize():5s} — Precision {p[i]:.4f} | Recall {r[i]:.4f} | F1 {f1[i]:.4f}")
    print("\nClassification report:")
    print(classification_report(y_true, y_pred, labels=[0, 1, 2], target_names=CLASSES, digits=4, zero_division=0))
    print("Matriz de confusão (linhas=real, colunas=predito):")
    print(confusion_matrix(y_true, y_pred, labels=[0, 1, 2]))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_por_classe": p.tolist(),
        "recall_por_classe": r.tolist(),
        "f1_por_classe": f1.tolist(),
        "matriz_confusao": confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist(),
    }


def load_pilot_counts():
    if not PILOT_JSON.exists():
        raise FileNotFoundError(f"Piloto salvo não encontrado: {PILOT_JSON}")
    data = json.loads(PILOT_JSON.read_text(encoding="utf-8"))
    counts = {str(k): int(v) for k, v in data["contagens"].items()}
    if sum(counts.values()) != int(data["shots"]):
        raise ValueError("O JSON do piloto tem contagens inconsistentes com o total de shots.")
    return data, counts


def run_new_hardware(qc, transpilation_seconds=0.0):
    # Explicit opt-in only. Save to a new filename to preserve the existing pilot artifact.
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = service.backend(BACKEND_NAME)
    pm = generate_preset_pass_manager(
        backend=backend, optimization_level=0, layout_method="trivial",
        routing_method="basic", initial_layout=[0, 1, 2, 3], seed_transpiler=42
    )
    start_transpile = time.time()
    isa = pm.run(qc.copy().measure_all(inplace=False))
    transpilation_seconds = time.time() - start_transpile
    sampler = SamplerV2(backend)
    print(f"\nSubmitting ONE circuit to {BACKEND_NAME} ({SHOTS} shots).")
    job = sampler.run([isa], shots=SHOTS)
    print("Job ID:", job.job_id())
    result = job.result()
    counts = result[0].data.meas.get_counts()
    out = {
        "backend": BACKEND_NAME,
        "job_id": job.job_id(),
        "shots": SHOTS,
        "tempo_transpilacao_segundos": transpilation_seconds,
        "contagens": counts,
    }
    new_path = ROOT / "modelos" / "resultado_ibm_novo.json"
    new_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Novo resultado salvo em:", new_path)
    return out, counts


def main():
    print("="*55)
    print("QTRUST — AVALIAÇÃO DO VQC")
    print("Modo seguro: reutiliza piloto IBM existente; nenhum job novo por padrão.")
    print("="*55)

    df = pd.read_csv(DATASET)
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["risco"].to_numpy(dtype=int)
    idx_train, idx_test = train_test_split(
        np.arange(len(df)), test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    X_test, y_test = X[idx_test], y[idx_test]
    print(f"Dataset: {len(df)} | treino: {len(idx_train)} | teste: {len(idx_test)}")

    weights = np.load(WEIGHTS)
    feature_map = zz_feature_map(feature_dimension=4, reps=1)
    ansatz = real_amplitudes(num_qubits=4, reps=2)
    if len(weights) != ansatz.num_parameters:
        raise ValueError(f"Pesos ({len(weights)}) incompatíveis com ansatz ({ansatz.num_parameters}).")
    print(f"Pesos carregados: {len(weights)}")

    # Full test-set evaluation in ideal statevector simulation (offline).
    print("\nCalculando avaliação do conjunto de teste no simulador ideal...")
    simulator_probs = []
    for i, sample in enumerate(X_test):
        circuit = build_circuit(feature_map, ansatz, sample, weights, measure=False)
        probs = class_probabilities_from_statevector(circuit)
        simulator_probs.append(probs)
        if (i + 1) % 25 == 0 or i + 1 == len(X_test):
            print(f"  Simuladas {i+1}/{len(X_test)} amostras")
    simulator_probs = np.asarray(simulator_probs)
    simulator_pred = simulator_probs.argmax(axis=1)
    sim_metrics = print_metrics(y_test, simulator_pred, "VQC — TESTE COMPLETO NO SIMULADOR IDEAL")

    # IBM pilot sample was the first sample of this same deterministic test split.
    pilot_sample = X_test[0]
    pilot_true = int(y_test[0])
    pilot_circuit = build_circuit(feature_map, ansatz, pilot_sample, weights, measure=False)
    sim_pilot_probs = class_probabilities_from_statevector(pilot_circuit)
    show_probabilities("SIMULADOR — AMOSTRA DO PILOTO (primeira do teste)", sim_pilot_probs)
    print(f"Rótulo real dessa amostra: {CLASSES[pilot_true].upper()} (classe {pilot_true})")

    pilot_info = None
    ibm_probs = None
    if RUN_HARDWARE:
        pilot_info, counts = run_new_hardware(pilot_circuit)
    elif USE_SAVED_PILOT:
        pilot_info, counts = load_pilot_counts()
        print("\nPiloto IBM reaproveitado — não foi enviado job novo.")
        print("Backend:", pilot_info.get("backend"), "| Job ID:", pilot_info.get("job_id"))
        print("Shots:", pilot_info.get("shots"))
    else:
        print("\nHardware desligado e piloto salvo não selecionado; sem resultado IBM nesta execução.")

    if pilot_info is not None:
        ibm_probs = class_probabilities_from_counts(counts)
        show_probabilities("IBM QUANTUM — DISTRIBUIÇÃO AGREGADA EM 3 CLASSES", ibm_probs)
        ibm_pred = int(ibm_probs.argmax())
        print(f"Rótulo real: {CLASSES[pilot_true].upper()} (classe {pilot_true})")
        print(f"Predição IBM: {CLASSES[ibm_pred].upper()} (classe {ibm_pred})")
        print("Acertou esta amostra?", "SIM" if ibm_pred == pilot_true else "NÃO")
        print("\nComparação simulador × IBM (mesma amostra):")
        for i, name in enumerate(CLASSES):
            diff = ibm_probs[i] - sim_pilot_probs[i]
            print(f"  {name:5s}: simulador {sim_pilot_probs[i]:.4f} | IBM {ibm_probs[i]:.4f} | diferença {diff:+.4f}")
        print("Nota: esta é uma comparação de uma amostra; não representa métricas gerais do hardware.")

    report = {
        "dataset_total": int(len(df)),
        "test_size": int(len(idx_test)),
        "split_seed": RANDOM_STATE,
        "classes": CLASSES,
        "simulador_ideal_teste_completo": sim_metrics,
        "simulador_piloto_amostra": {
            "id_dataset": int(idx_test[0]),
            "rotulo_real": pilot_true,
            "probabilidades": sim_pilot_probs.tolist(),
            "predicao": int(sim_pilot_probs.argmax()),
        },
        "ibm_piloto": None if ibm_probs is None else {
            "backend": pilot_info.get("backend"),
            "job_id": pilot_info.get("job_id"),
            "shots": int(pilot_info.get("shots", sum(counts.values()))),
            "id_dataset": int(idx_test[0]),
            "rotulo_real": pilot_true,
            "probabilidades": ibm_probs.tolist(),
            "predicao": int(ibm_probs.argmax()),
            "acertou_amostra": bool(int(ibm_probs.argmax()) == pilot_true),
            "counts": counts,
        },
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nRelatório salvo em:", REPORT_JSON)
    print("\nConcluído. Nenhum job IBM novo foi enviado (RUN_HARDWARE=False)." if not RUN_HARDWARE else "\nConcluído com nova execução IBM opt-in.")


if __name__ == "__main__":
    main()
