"""
Gera uma base FICTÍCIA de mensagens para treinar o MVP do QTrust.

Cada linha tem:
  texto            mensagem simulada de WhatsApp
  urgencia         sinal x1, 0 a 1
  transferencia    sinal x2, 0 a 1 (pedido de Pix/transferência/pagamento)
  premio           sinal x3, 0 a 1
  falsa_identidade sinal x4, 0 a 1
  risco            0 = baixo, 1 = médio, 2 = alto
  rotulo           baixo / medio / alto

Os sinais vêm dos trechos usados para montar a mensagem (com ruído),
simulando o que um extrator de sinais devolveria. Todos os nomes, valores
e chaves Pix são inventados.

Uso:  python gerar_base.py            (gera mensagens_qtrust.csv com 500 linhas)
      python gerar_base.py 1000       (outro tamanho)
"""
import csv
import random
import sys
from pathlib import Path

SEED = 42
N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
SAIDA = Path(__file__).with_name("mensagens_qtrust.csv")
RUIDO_ROTULO = 0.04  # 4% dos rótulos trocados para a classe vizinha (realismo)

rng = random.Random(SEED)

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Fernanda", "Gabriel", "Juliana", "Lucas",
         "Mariana", "Pedro", "Rafael", "Beatriz", "Thiago", "Camila", "Vitor"]
PARENTES = ["mãe", "pai", "tia", "vó", "amor", "mano", "filha", "filho"]
BANCOS = ["Banco Aurora", "Banco Horizonte", "FinPlus", "Banco Atlântico"]  # fictícios


def valor():
    return rng.choice(["150", "280", "450", "500", "800", "1.200", "1.500", "2.300", "3.000"])


def chave():
    tipo = rng.random()
    if tipo < 0.4:
        return f"{rng.randint(10000000, 99999999):08x}-{rng.randint(1000, 9999)}-ab{rng.randint(10, 99)}"
    if tipo < 0.7:
        return f"pagamentos{rng.randint(10, 999)}@exemplo.com"
    return f"(11) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"


def preencher(t):
    return (t.replace("{v}", valor()).replace("{chave}", chave())
             .replace("{nome}", rng.choice(NOMES)).replace("{parente}", rng.choice(PARENTES))
             .replace("{banco}", rng.choice(BANCOS)))


# Trechos por sinal: (texto, intensidade mínima, intensidade máxima)
TRECHOS = {
    "falsa_identidade": {
        "forte": [
            "Oi {parente}, troquei de número, salva esse.",
            "Oi {parente}, sou eu, meu celular quebrou e esse é meu número novo.",
            "Aqui é da central de segurança do {banco}.",
            "Olá, sou o gerente da sua conta no {banco}.",
            "Oi, sou eu, {nome}, tô usando o celular de um amigo.",
            "Somos do suporte do WhatsApp, sua conta foi denunciada.",
            "Atendimento {banco}: identificamos uma compra suspeita no seu cartão.",
        ],
        "fraco": [
            "Oi, aqui é da loja onde você comprou semana passada.",
            "Olá, falo em nome da administração do condomínio.",
            "Oi, peguei seu contato com o {nome}.",
        ],
    },
    "urgencia": {
        "forte": [
            "É urgente!",
            "Preciso disso agora, por favor.",
            "Tem que ser hoje, senão vão cortar.",
            "Responde rápido, é sério!",
            "Sua conta será bloqueada em 30 minutos.",
            "Última chance, o prazo acaba hoje.",
            "Não posso falar agora, só faz isso rápido.",
        ],
        "fraco": [
            "Quando puder, me responde.",
            "Se der pra resolver hoje seria bom.",
            "Me avisa até amanhã, beleza?",
        ],
    },
    "transferencia": {
        "forte": [
            "Faz um Pix de R$ {v} pra essa chave: {chave}",
            "Me empresta R$ {v}? Te devolvo amanhã.",
            "Transfere R$ {v} para regularizar sua conta.",
            "Paga esse boleto de R$ {v} pra mim? Depois te passo.",
            "Faz uma transferência de R$ {v} pra conta de segurança.",
            "Manda R$ {v} nessa chave Pix: {chave}",
        ],
        "fraco": [
            "Depois me passa os R$ {v} da viagem, sem pressa.",
            "A vaquinha do presente ficou R$ {v} pra cada.",
        ],
    },
    "premio": {
        "forte": [
            "Parabéns! Você foi sorteado e ganhou R$ {v}.",
            "Seu CPF tem um valor a receber de R$ {v}.",
            "Você ganhou um celular novo, pague só o frete.",
            "Seu cadastro foi premiado na promoção de aniversário do {banco}.",
            "Resgate agora seu bônus de R$ {v}.",
        ],
        "fraco": [
            "Promoção da semana: 20% de desconto na loja.",
            "Participe do sorteio do grupo da academia.",
            "Cupom de frete grátis válido até domingo.",
        ],
    },
}
INTENSIDADE = {"forte": (0.75, 1.0), "fraco": (0.3, 0.55)}

NEUTRAS = [
    "Bom dia, tudo bem?", "Chego em casa às 19h.", "Viu o jogo ontem?",
    "Amanhã tem reunião às 10h.", "Manda a foto do bolo!", "Obrigado pela ajuda hoje.",
    "Vamos almoçar onde?", "Já saí do trabalho.", "O {nome} vai na festa?",
    "Feliz aniversário! Tudo de bom.", "Comprei o pão, mais alguma coisa?",
    "Te mandei o Pix do almoço, confere aí.", "Qual sua chave Pix pra eu te pagar a pizza?",
    "Recebi o comprovante, obrigado!", "Boa noite, até amanhã.",
]

# Receitas por nível de risco: listas de (sinal, força)
RECEITAS = {
    2: [  # alto: combinações típicas de golpe
        [("falsa_identidade", "forte"), ("transferencia", "forte"), ("urgencia", "forte")],
        [("falsa_identidade", "forte"), ("transferencia", "forte")],
        [("premio", "forte"), ("transferencia", "forte"), ("urgencia", "forte")],
        [("premio", "forte"), ("transferencia", "forte")],
        [("falsa_identidade", "forte"), ("urgencia", "forte"), ("transferencia", "forte"), ("premio", "fraco")],
        [("urgencia", "forte"), ("transferencia", "forte"), ("falsa_identidade", "fraco")],
    ],
    1: [  # médio: um sinal forte isolado ou sinais fracos combinados
        [("urgencia", "forte")],
        [("transferencia", "forte")],
        [("premio", "forte")],
        [("falsa_identidade", "forte")],
        [("premio", "fraco"), ("urgencia", "fraco")],
        [("falsa_identidade", "fraco"), ("transferencia", "fraco")],
        [("falsa_identidade", "fraco"), ("urgencia", "forte")],
    ],
    0: [  # baixo: conversa comum, pagamento legítimo ou promoção inofensiva
        [],
        [],
        [("transferencia", "fraco")],
        [("premio", "fraco")],
        [("urgencia", "fraco")],
    ],
}
PROPORCAO = {0: 0.40, 1: 0.25, 2: 0.35}
ROTULOS = {0: "baixo", 1: "medio", 2: "alto"}
ORDEM = ["falsa_identidade", "premio", "urgencia", "transferencia"]  # ordem natural na mensagem


def gerar_linha(risco):
    receita = rng.choice(RECEITAS[risco])
    sinais = {s: round(rng.uniform(0.0, 0.15), 2) for s in ORDEM}
    partes = []
    for nome in ORDEM:
        for s, forca in receita:
            if s == nome:
                partes.append(preencher(rng.choice(TRECHOS[s][forca])))
                lo, hi = INTENSIDADE[forca]
                sinais[s] = round(min(1.0, max(0.0, rng.uniform(lo, hi) + rng.gauss(0, 0.04))), 2)
    if not partes or (risco == 0 and rng.random() < 0.5):
        partes.insert(0, preencher(rng.choice(NEUTRAS)))
    if risco == 2 and rng.random() < 0.25:  # golpes às vezes começam com cumprimento
        partes.insert(0, rng.choice(["Oi, tudo bem?", "Bom dia!", "Oi, sumida(o)!"]))

    if rng.random() < RUIDO_ROTULO:
        risco = min(2, risco + 1) if risco == 0 else (risco - 1 if risco == 2 else rng.choice([0, 2]))
    return {
        "texto": " ".join(partes),
        "urgencia": sinais["urgencia"],
        "transferencia": sinais["transferencia"],
        "premio": sinais["premio"],
        "falsa_identidade": sinais["falsa_identidade"],
        "risco": risco,
        "rotulo": ROTULOS[risco],
    }


def main():
    alvos = [0] * round(N * PROPORCAO[0]) + [1] * round(N * PROPORCAO[1])
    alvos += [2] * (N - len(alvos))
    rng.shuffle(alvos)
    linhas = [gerar_linha(r) for r in alvos]

    with SAIDA.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)

    contagem = {ROTULOS[k]: sum(1 for l in linhas if l["risco"] == k) for k in ROTULOS}
    print(f"{len(linhas)} linhas salvas em {SAIDA}")
    print("Distribuição:", contagem)


if __name__ == "__main__":
    main()
