from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

# Conecta à conta IBM Quantum já salva
service = QiskitRuntimeService()

# Seleciona o hardware real
backend = service.backend("ibm_fez")

print("=" * 50)
print("TESTE BELL - IBM QUANTUM")
print("=" * 50)

print(f"Backend: {backend.name}")
print(f"Qubits disponíveis: {backend.num_qubits}")

# Criar circuito Bell
qc = QuantumCircuit(2)

qc.h(0)
qc.cx(0, 1)

qc.measure_all()

print("\nCircuito original:")
print(qc.draw())

# Adaptar circuito ao hardware
pm = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1
)

isa_circuit = pm.run(qc)

print("\nCircuito adaptado ao hardware:")
print(isa_circuit.draw())

print("\nCircuito pronto para execução!")

# Executar no hardware real
print("\nEnviando circuito Bell para o hardware IBM Quantum...")

sampler = SamplerV2(backend)

job = sampler.run(
    [isa_circuit],
    shots=1024
)

print(f"\nJob ID: {job.job_id()}")
print("Aguardando resultado da execução...")

result = job.result()

# Recuperar contagens
counts = result[0].data.meas.get_counts()

print("\n" + "=" * 50)
print("RESULTADO DO HARDWARE REAL")
print("=" * 50)

print("Contagens:", counts)

total = sum(counts.values())

for estado, quantidade in sorted(counts.items()):
    porcentagem = (quantidade / total) * 100
    print(f"{estado}: {quantidade} ({porcentagem:.2f}%)")