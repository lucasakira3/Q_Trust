
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def create_qtrust_circuit(features, shots=1024):
    """
    Cria e executa um circuito quântico de 4 qubits.

    Features:
    0 - Urgência
    1 - Transferência
    2 - Promessa de prêmio
    3 - Falsa identidade
    """

    if len(features) != 4:
        raise ValueError("O circuito precisa receber exatamente 4 features.")

    circuit = QuantumCircuit(4, 4)

    # 1. Encoding: transformar features em estados quânticos
    for qubit, feature in enumerate(features):
        circuit.ry(float(feature) * 3.14159, qubit)

    # 2. Entanglement: conectar os qubits
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.cx(2, 3)

    # 3. Segunda camada de rotações
    for qubit, feature in enumerate(features):
        circuit.ry(float(feature) * 3.14159 / 2, qubit)

    # 4. Medição
    circuit.measure(range(4), range(4))

    return circuit


def simulate_circuit(features, shots=1024):
    circuit = create_qtrust_circuit(features, shots)

    simulator = AerSimulator()
    result = simulator.run(circuit, shots=shots).result()

    counts = result.get_counts()

    return circuit, counts


if __name__ == "__main__":
    # Exemplo: urgência, transferência, prêmio, falsa identidade
    example = [1, 1, 0, 1]

    circuit, counts = simulate_circuit(example)

    print("Circuito QTrust:")
    print(circuit.draw())

    print("\nResultados da simulação:")
    print(counts)
