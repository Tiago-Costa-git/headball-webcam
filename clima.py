"""Clima durante a partida (só lógica, sem desenho, para ser fácil de testar).

- Chuva: os jogadores andam um pouco mais devagar, a bola ressalta menos e formam-se poças
  onde a bola e os jogadores abrandam.
- Trovoada: chuva + relâmpagos. Antes de cada raio aparece um aviso no chão; quem lá estiver
  fica atordoado e a bola é atirada ao ar.
- Neve: o chão fica escorregadio (os jogadores demoram a travar) e a bola desliza mais.
- Calor: aparecem zonas a arder no relvado (primeiro sai fumo, depois fogo). Quem pisa o fogo
  salta de dor e a bola é projetada para cima.
- Aleatório: começa com um clima ao calhas e muda a meio da partida.
"""
import random

CLIMAS = ["limpo", "chuva", "trovoada", "neve", "calor"]
NOMES = {"limpo": "Limpo", "chuva": "Chuva", "trovoada": "Trovoada", "neve": "Neve", "calor": "Calor"}
MODOS = ["aleatorio"] + CLIMAS                        # o que se escolhe no menu (tecla T)
AVISO_MUDANCA = {"limpo": "O céu limpou!", "chuva": "Começou a chover!", "trovoada": "Vem aí trovoada!",
                 "neve": "Começou a nevar!", "calor": "Que calor! Cuidado com o fogo!"}

# vel: velocidade dos jogadores · inercia: 1 = travar logo, perto de 0 = escorregar
# ressalto: quanto a bola ressalta no chão · atrito: quanto a bola mantém a velocidade a rolar
PARAMS = {
    "limpo":    {"vel": 1.00, "inercia": 1.00, "ressalto": 0.72, "atrito": 0.985},
    "chuva":    {"vel": 0.92, "inercia": 1.00, "ressalto": 0.58, "atrito": 0.975},
    "trovoada": {"vel": 0.92, "inercia": 1.00, "ressalto": 0.58, "atrito": 0.975},
    "neve":     {"vel": 0.95, "inercia": 0.07, "ressalto": 0.50, "atrito": 0.997},
    "calor":    {"vel": 1.00, "inercia": 1.00, "ressalto": 0.75, "atrito": 0.985},
}
POCA_MAX = 70            # largura máxima de uma poça (px)
LENTO_POCA = 0.7         # velocidade dos jogadores dentro de uma poça
RAIO_AVISO = 70          # frames de aviso antes do relâmpago
RAIO_ALCANCE = 75        # distância (px) a que o relâmpago atinge
ATORDOADO = 90           # frames sem controlo depois de levar com um raio
FOGO_AVISO, FOGO_VIDA, FOGO_LARG = 90, 300, 80


def novo_estado(modo="aleatorio", xmin=100, xmax=1000, rnd=random):
    """Cria o estado do clima de uma partida."""
    atual = rnd.choice(CLIMAS) if modo == "aleatorio" else modo
    return {"modo": modo, "atual": atual, "mudar_em": rnd.randint(1200, 1800) if modo == "aleatorio" else None,
            "pocas": [{"x": rnd.uniform(xmin + 60, xmax - 60), "larg": 0.0} for _ in range(3)],
            "raio": None, "flash": 0, "proximo_raio": rnd.randint(240, 420),
            "fogos": [], "proximo_fogo": rnd.randint(180, 300), "neve_chao": 0.0, "ultimo_raio": None, "xmin": xmin, "xmax": xmax}


def params(estado):
    """Parâmetros de física do clima atual."""
    return PARAMS[estado["atual"]]


def em_poca(estado, x):
    """True se a posição x está dentro de uma poça (com pelo menos 20 px)."""
    return any(p["larg"] > 20 and abs(x - p["x"]) < p["larg"] / 2 for p in estado["pocas"])


def em_fogo(estado, x):
    """True se a posição x está numa zona a arder (já com fogo, não só fumo)."""
    return any(f["aviso"] <= 0 and abs(x - f["x"]) < FOGO_LARG / 2 for f in estado["fogos"])


def mudar(estado, rnd=random):
    """Muda para outro clima (diferente do atual). Devolve o texto do aviso."""
    estado["atual"] = rnd.choice([c for c in CLIMAS if c != estado["atual"]])
    estado["fogos"].clear()
    estado["raio"] = None
    return AVISO_MUDANCA[estado["atual"]]


def passo_clima(estado, jogadores, bola, y_chao, rnd=random):
    """Avança um frame do clima e aplica-o aos jogadores e à bola.
    Devolve uma lista de acontecimentos para o jogo mostrar: ("mudou", texto), ("raio", x), ("fogo", x), ("chapinhar", x)."""
    ev = []
    atual = estado["atual"]
    if estado["mudar_em"] is not None:                         # modo aleatório: o clima muda a meio
        estado["mudar_em"] -= 1
        if estado["mudar_em"] <= 0:
            ev.append(("mudou", mudar(estado, rnd)))
            estado["mudar_em"] = rnd.randint(1200, 1800)
            atual = estado["atual"]

    molhado = atual in ("chuva", "trovoada")                   # poças crescem à chuva e secam no resto
    for p in estado["pocas"]:
        p["larg"] = min(POCA_MAX, p["larg"] + 0.12) if molhado else max(0.0, p["larg"] - 0.2)
    estado["neve_chao"] = min(1.0, estado["neve_chao"] + 0.004) if atual == "neve" else max(0.0, estado["neve_chao"] - 0.01)

    if estado["flash"] > 0:
        estado["flash"] -= 1
    if atual == "trovoada":                                    # relâmpagos com aviso
        if estado["raio"] is None:
            estado["proximo_raio"] -= 1
            if estado["proximo_raio"] <= 0:
                alvo = rnd.choice(jogadores).x if rnd.random() < 0.6 else rnd.uniform(estado["xmin"], estado["xmax"])
                estado["raio"] = {"x": alvo, "t": RAIO_AVISO}
        else:
            estado["raio"]["t"] -= 1
            if estado["raio"]["t"] <= 0:
                x = estado["raio"]["x"]
                for j in jogadores:
                    if abs(j.x - x) < RAIO_ALCANCE:
                        j.efeitos["atordoado"] = ATORDOADO
                        j.vy = -8
                if abs(bola.x - x) < RAIO_ALCANCE + 10:
                    bola.vy, bola.vx = -14, rnd.choice((-5, 5))
                estado["raio"], estado["flash"], estado["ultimo_raio"] = None, 8, x
                estado["proximo_raio"] = rnd.randint(300, 540)
                ev.append(("raio", x))

    if atual == "calor":                                       # zonas a arder
        estado["proximo_fogo"] -= 1
        if estado["proximo_fogo"] <= 0 and len(estado["fogos"]) < 2:
            estado["fogos"].append({"x": rnd.uniform(estado["xmin"] + 40, estado["xmax"] - 40),
                                    "aviso": FOGO_AVISO, "vida": FOGO_VIDA})
            estado["proximo_fogo"] = rnd.randint(240, 420)
    for f in list(estado["fogos"]):
        if f["aviso"] > 0:
            f["aviso"] -= 1
        else:
            f["vida"] -= 1
            if f["vida"] <= 0:
                estado["fogos"].remove(f)
    for j in jogadores:
        if j.on_ground and em_fogo(estado, j.x):
            j.vy, j.on_ground = -11, False                     # salta de dor
            j.efeitos["queimado"] = 40
            ev.append(("fogo", j.x))
    if bola.y >= y_chao - 2:
        if em_fogo(estado, bola.x):
            bola.vy = -10
            ev.append(("fogo", bola.x))
        elif em_poca(estado, bola.x):
            if abs(bola.vx) > 2:
                ev.append(("chapinhar", bola.x))
            bola.vx *= 0.93                                    # a água trava a bola
    return ev


def velocidade(estado, jogador):
    """Multiplicador da velocidade do jogador com o clima (e as poças) neste momento."""
    v = params(estado)["vel"]
    if jogador.on_ground and em_poca(estado, jogador.x):
        v *= LENTO_POCA
    return v
