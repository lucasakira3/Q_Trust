import numpy as np

from qiskit.circuit.library import real_amplitudes, zz_feature_map
from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

# Conecta à conta IBM Quantum já salva
service = QiskitRuntimeService()

# Seleciona o hardware real
backend = service.backend("ibm_fez")

print("=" * 50)
print("QTRUST - EXPERIMENTO IBM QUANTUM")
print("=" * 50)

print(f"Backend: {backend.name}")
print(f"Qubits disponíveis: {backend.num_qubits}")
    
# ============================================================
# QTRUST - VQC TREINADO
# ============================================================

print("\n" + "=" * 50)
print("QTRUST - PREPARANDO VQC TREINADO")
print("=" * 50)

# Carregar pesos treinados
pesos = np.load("modelos/vqc_pesos.npy")

# Features da mensagem de alto risco
features = np.array([0.81, 0.89, 0.42, 0.86])

# Mesma escala usada durante o treinamento
features_escaladas = features * np.pi

# Reconstruir Feature Map original
feature_map = zz_feature_map(
    feature_dimension=4,
    reps=1
)

# Reconstruir Ansatz original
ansatz = real_amplitudes(
    num_qubits=4,
    reps=2
)

print(f"\nFeatures originais: {features}")
print(f"Features escaladas: {features_escaladas}")
print(f"Quantidade de pesos: {len(pesos)}")
print(f"Quantidade de parâmetros do Ansatz: {ansatz.num_parameters}")

# Inserir os dados no Feature Map
feature_map_com_dados = feature_map.assign_parameters(
    dict(zip(feature_map.parameters, features_escaladas))
)

# Inserir os pesos treinados no Ansatz
ansatz_com_pesos = ansatz.assign_parameters(
    dict(zip(ansatz.parameters, pesos))
)

# Montar circuito completo
qc_qtrust = QuantumCircuit(4)

qc_qtrust.compose(feature_map_com_dados, inplace=True)
qc_qtrust.compose(ansatz_com_pesos, inplace=True)

# Adicionar medições
qc_qtrust.measure_all()

print("\nCircuito QTrust:")
print(qc_qtrust.draw())

print("\nCircuito QTrust montado com sucesso!")

# ============================================================
# TRANSPILAÇÃO DO QTRUST PARA O IBM FEZ
# ============================================================

print("\n" + "=" * 50)
print("QTRUST - TRANSPILANDO PARA O HARDWARE")
print("=" * 50)

pm_qtrust = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1
)

isa_qtrust = pm_qtrust.run(qc_qtrust)

print("\nCircuito transpilado:")
print(isa_qtrust.draw())

print("\nProfundidade original:", qc_qtrust.depth())
print("Profundidade transpilada:", isa_qtrust.depth())

print("\nOperações do circuito transpilado:")
print(isa_qtrust.count_ops())

print("\nCircuito QTrust adaptado ao hardware com sucesso!")

# ============================================================
# EXECUÇÃO DO QTRUST NO HARDWARE REAL
# ============================================================

print("\n" + "=" * 50)
print("QTRUST - EXECUÇÃO NO IBM QUANTUM")
print("=" * 50)

# Criar o Sampler para o hardware selecionado
sampler = SamplerV2(backend)

# Quantidade de execuções do circuito
shots = 1024

print(f"\nQuantidade de shots: {shots}")
print("Enviando circuito para o hardware...")

# Enviar o circuito transp ilado
job = sampler.run(
    [isa_qtrust],
    shots=shots
)

print("\nJob enviado com sucesso!")
print(f"Job ID: {job.job_id()}")

# Aguardar e recuperar os resultados
resultado = job.result()

# Recuperar os resultados das medições
contagens = resultado[0].data.meas.get_counts()

print("\n" + "=" * 50)
print("RESULTADOS DO QTRUST NO IBM QUANTUM")
print("=" * 50)

print("\nContagens:")
print(contagens)

print("\nProbabilidades observadas:")

for estado, quantidade in sorted(contagens.items()):
    probabilidade = quantidade / shots
    print(
        f"Estado {estado}: "
        f"{quantidade} ocorrências "
        f"({probabilidade:.2%})"
    )

print("\nExperimento finalizado!")