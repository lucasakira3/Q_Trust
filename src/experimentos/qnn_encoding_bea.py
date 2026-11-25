"""
Experimento (ainda não concluído): classificador quântico com a codificação da Bea.

- Codificação: RY(π·x) em cada qubit + CX em cadeia (igual a src/qtrust_model.py)
- Camada treinável: real_amplitudes(4, reps=2), 12 parâmetros θ
- Leitura: ⟨Z⟩ nos qubits 0, 1 e 2, um por classe (baixo, médio, alto)
- Otimizador: COBYLA (sem gradientes, mais rápido por iteração)

Rodar a partir da raiz do projeto, com progresso ao vivo:
    .venv\\Scripts\\python -u src\\experimentos\\qnn_encoding_bea.py
"""
import time, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.circuit.library import real_amplitudes
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import StatevectorEstimator
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit_machine_learning.algorithms import NeuralNetworkClassifier
from qiskit_machine_learning.optimizers import COBYLA
df = pd.read_csv("dados/mensagens_qtrust.csv")
X = df[["urgencia","transferencia","premio","falsa_identidade"]].to_numpy(); y = df["risco"].to_numpy()
X_tr,X_te,y_tr,y_te = train_test_split(X,y,test_size=0.25,stratify=y,random_state=42)
x = ParameterVector("x",4); fm = QuantumCircuit(4)
for i in range(4): fm.ry(np.pi*x[i], i)          # codificação da Bea
fm.cx(0,1); fm.cx(1,2); fm.cx(2,3)               # emaranhamento em cadeia
an = real_amplitudes(4, reps=2)                   # camada treinável (12 θ)
qnn = EstimatorQNN(circuit=fm.compose(an), estimator=StatevectorEstimator(),
                   observables=[SparsePauliOp("IIIZ"), SparsePauliOp("IIZI"), SparsePauliOp("IZII")],
                   input_params=list(x), weight_params=list(an.parameters))
it=[0]; t0=time.time()
def cb(w, c):
    it[0]+=1
    if it[0]==1 or it[0]%10==0: print(f"iter {it[0]:>3} | custo {c:.4f} | {time.time()-t0:5.0f}s", flush=True)
clf = NeuralNetworkClassifier(qnn, optimizer=COBYLA(maxiter=150), loss="squared_error", one_hot=True,
                              initial_point=np.random.default_rng(0).uniform(-0.5,0.5,an.num_parameters), callback=cb)
clf.fit(X_tr, y_tr)
def pred(X):
    p = np.asarray(clf.predict(X)); return p.argmax(axis=1) if p.ndim==2 else p.astype(int).ravel()
print(f"\nRESULTADO: acurácia treino {np.mean(pred(X_tr)==y_tr):.3f} | teste {np.mean(pred(X_te)==y_te):.3f} | {time.time()-t0:.0f}s", flush=True)
