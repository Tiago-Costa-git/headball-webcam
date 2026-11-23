"""Power-ups que aparecem durante a partida (só lógica, sem desenho, para ser fácil de testar).

Cada jogador tem um dicionário de efeitos ativos, por exemplo {"velocidade": 240},
em que o número é quantos frames faltam (60 frames = 1 segundo).
"""
import math
import random

TIPOS = {
    # nome: (texto no ecrã, duração em frames, cor, quem recebe o efeito)
    "velocidade":  ("VELOCIDADE",  360, (255, 220, 60),  "proprio"),
    "super_chuto": ("SUPER CHUTO", 360, (255, 90, 70),   "proprio"),
    "salto":       ("SUPER SALTO", 360, (110, 230, 110), "proprio"),
    "gelo":        ("GELO",        150, (120, 220, 255), "adversario"),
}
MULT_VELOCIDADE = 1.45
MULT_CHUTO = 1.8
MULT_SALTO = 1.3
INTERVALO = (480, 720)          # aparece um power-up a cada 8 a 12 segundos
VIDA = 480                      # e desaparece se ninguém o apanhar em 8 segundos
RAIO_APANHAR = 62               # distância (do centro da cabeça ou do corpo) para apanhar


class PowerUp:
    def __init__(self, tipo, x, y):
        self.tipo, self.x, self.y = tipo, x, y
        self.vida = VIDA


def novo_powerup(xmin, xmax, y_chao, rnd=random):
    """Cria um power-up num sítio aleatório que se consegue apanhar a andar ou a saltar."""
    tipo = rnd.choice(list(TIPOS))
    return PowerUp(tipo, rnd.uniform(xmin + 40, xmax - 40), y_chao - rnd.choice((0, 60, 120)))


def atualizar_efeitos(efeitos):
    """Desconta um frame a cada efeito e devolve só os que ainda estão ativos."""
    return {k: v - 1 for k, v in efeitos.items() if v > 1}


def aplicar(tipo, jogador, adversario):
    """Dá o efeito ao jogador que apanhou (ou ao adversário, no caso do gelo). Devolve o texto a mostrar."""
    texto, duracao, _, alvo = TIPOS[tipo]
    quem = jogador if alvo == "proprio" else adversario
    quem.efeitos[tipo] = duracao
    return texto


def apanhou(pu, jogador):
    """True se o jogador está a tocar no power-up (cabeça ou corpo)."""
    corpo_y = jogador.y + 70
    return (math.hypot(pu.x - jogador.x, pu.y - jogador.y) < RAIO_APANHAR or
            math.hypot(pu.x - jogador.x, pu.y - corpo_y) < RAIO_APANHAR)


def passo_powerups(estado, jogadores, xmin, xmax, y_chao, rnd=random):
    """Avança um frame: faz aparecer, envelhecer e apanhar power-ups.
    estado = {"lista": [...], "espera": frames até ao próximo}. Devolve (jogador, texto) se alguém apanhou, senão None."""
    estado["espera"] -= 1
    if estado["espera"] <= 0 and not estado["lista"]:
        estado["lista"].append(novo_powerup(xmin, xmax, y_chao, rnd))
        estado["espera"] = rnd.randint(*INTERVALO)
    apanhado = None
    for pu in list(estado["lista"]):
        pu.vida -= 1
        if pu.vida <= 0:
            estado["lista"].remove(pu)
            continue
        for i, j in enumerate(jogadores):
            if apanhou(pu, j):
                texto = aplicar(pu.tipo, j, jogadores[1 - i])
                estado["lista"].remove(pu)
                apanhado = (j, texto)
                break
    return apanhado
