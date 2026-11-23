"""
Head Ball com cabeças da webcam  -  pixel art + pernas com física
-----------------------------------------------------------------
Instalação:  py -m pip install pygame-ce numpy opencv-python
Execução:    py headball_webcam.py

Menu:  1 = 1 jogador vs Bot | 2 = 2 jogadores | B = trocar de estádio | TAB = controlos
       C = foto do Jogador 1 | V = foto do Jogador 2 / Bot | X = apagar fotos | ESC = sair
Jogo:  J1: A/D mover, W saltar, ESPAÇO chutar
       J2: setas esquerda/direita, seta cima saltar, ENTER chutar
       Comando (PS5, PS4, Xbox...; cabo ou Bluetooth): analógico/setas mover, CRUZ saltar,
       QUADRADO/CÍRCULO/R1/R2 chutar. No menu: CRUZ = 1 jogador, TRIÂNGULO = 2 jogadores,
       QUADRADO = estádio, OPTIONS = controlos. CREATE (Share) = voltar ao menu.
       ESC volta ao menu.
Captura: TAB troca de câmara, ESPAÇO tira a foto, F escolhe uma foto de um ficheiro, ESC cancela.
Regra: bola presa entre os dois jogadores 3 s -> BOLA AO AR (contagem 3-2-1 e a bola é lançada).

PX = tamanho dos "pixéis" do cenário (3 = mais detalhe, 6 = mais retro).
HEAD_PIXEL = pixelização das cabeças (1 = foto suave, 2 = ligeira, 4 = igual ao cenário).
"""
import math
import os
import random
import sys

import pygame

import base_dados as bd      # contas, histórico e estatísticas (SQLite)
import powerups as pw        # power-ups durante a partida
import clima as cl           # chuva, trovoada, neve e calor

try:
    import numpy as np
except ImportError:
    np = None
try:
    import cv2
except ImportError:
    cv2 = None
if np is None:
    cv2 = None  # a captura da webcam precisa do numpy
ENUM_ERR = ""    # motivo pelo qual os nomes das câmaras não estão disponíveis
try:
    from cv2_enumerate_cameras import enumerate_cameras   # opcional: dá nomes às câmaras
except Exception as _exc:
    enumerate_cameras = None
    ENUM_ERR = f"{type(_exc).__name__}: {_exc}"

# ---------------------------------------------------------------- constantes
W, H = 1120, 640
PX = 4                         # tamanho de cada "pixel" do jogo no ecrã
LW, LH = W // PX, H // PX      # resolução interna (baixa)
GROUND = H - 72
GRAV = 0.7
HEAD_R = 46
HIP_DY = 14                    # anca abaixo da base da cabeça
L1, L2 = 15, 15                # coxa e canela
BODY_H = 50                    # da base da cabeça aos pés
BALL_R = 24                    # raio físico = raio desenhado (com contorno)
GOAL_W, GOAL_H = 96, 224       # baliza alta o suficiente para a bola passar por cima de um jogador parado
CROSSBAR_Y = GROUND - GOAL_H
XMIN = GOAL_W + HEAD_R - 4        # os jogadores não entram nas balizas (senão a bola nunca entrava)
XMAX = W - XMIN
GOAL_LINE = GOAL_W - 18           # a bola é golo quando o centro passa esta linha
SPEED = 6.0
JUMP = 15.5
KICK_FRAMES = 14
KICK_COOLDOWN = 8
MATCH_TIME = 60
STUCK_FRAMES = 180             # bola presa entre os dois jogadores durante 3 s -> bola ao ar
JUMPBALL_FRAMES = 180          # contagem regressiva de 3 s antes de lançar a bola
HEAD_PIXEL = 2        # pixelização das cabeças da webcam (1 = suave ... 4 = como o cenário)
PORT_SIZE = 52        # tamanho dos retratos no ecrã

HEAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heads")
os.makedirs(HEAD_DIR, exist_ok=True)
HEAD_PATHS = [os.path.join(HEAD_DIR, "jogador1.png"), os.path.join(HEAD_DIR, "jogador2.png")]
CAM_FILE = os.path.join(HEAD_DIR, "camera.txt")
CAM_INDEX = 0
try:
    with open(CAM_FILE) as _fh:
        CAM_INDEX = int(_fh.read().strip())
except Exception:
    pass

OUTLINE = (20, 16, 32)
WHITE = (250, 250, 250)
SHADOW = (28, 96, 52)
SKIN_LEG = (236, 190, 150)
TEAMS = [
    {"shirt": (40, 110, 230), "shorts": (240, 240, 240), "sock": (40, 110, 230), "name": "JOGADOR 1"},
    {"shirt": (226, 60, 60), "shorts": (30, 30, 40), "sock": (226, 60, 60), "name": "JOGADOR 2"},
]
SKINS = [(245, 205, 160), (222, 178, 140)]
HAIRS = [(60, 40, 30), (240, 200, 70)]


def I(v):
    """Coordenada real -> coordenada do ecrã de baixa resolução."""
    return int(round(v / PX))


# ---------------------------------------------------------------- webcam
def crop_box(frame, face):
    h, w = frame.shape[:2]
    if face is not None:
        x, y, fw, fh = face
        return x + fw / 2, y + fh / 2, int(max(fw, fh) * 1.4)
    return w / 2, h / 2, int(min(w, h) * 0.7)


def make_head_png(frame, face):
    cx, cy, s = crop_box(frame, face)
    half = s // 2
    padded = cv2.copyMakeBorder(frame, half, half, half, half, cv2.BORDER_REPLICATE)
    x0, y0 = int(cx) - half + half, int(cy) - half + half
    crop = padded[y0:y0 + 2 * half, x0:x0 + 2 * half]
    crop = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)
    yy, xx = np.ogrid[:256, :256]
    mask = (((xx - 127.5) ** 2 + (yy - 127.5) ** 2) <= 127.5 ** 2).astype(np.uint8) * 255
    return cv2.merge([crop[:, :, 0], crop[:, :, 1], crop[:, :, 2], mask])


_CAP = None


def load_cascade():
    """Devolve o detetor de caras, ou None se esta instalação do OpenCV não o tiver."""
    try:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(path)
        return None if cascade.empty() else cascade
    except Exception:
        return None


def save_png(path, img):
    """Guarda a imagem mesmo que o caminho tenha acentos (cv2.imwrite falha nesses casos)."""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("não consegui gerar o PNG")
    buf.tofile(path)


def import_head_from_file(slot, cascade):
    """Abre o seletor de ficheiros e usa a foto escolhida como cabeça."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title=f"Escolhe a foto do Jogador {slot + 1}",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Todos", "*.*")])
        root.destroy()
    except Exception as exc:
        return f"Não consegui abrir o seletor de ficheiros: {exc}"
    if not path:
        return "Nenhuma foto escolhida."
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return "Não consegui ler essa imagem."
    big = max(img.shape[:2])
    if big > 1280:                                   # fotos grandes: reduz para detetar mais depressa
        k = 1280 / big
        img = cv2.resize(img, (int(img.shape[1] * k), int(img.shape[0] * k)), interpolation=cv2.INTER_AREA)
    face = None
    if cascade is not None:
        faces = cascade.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.2, 5, minSize=(60, 60))
        face = max(faces, key=lambda f: f[2] * f[3]) if len(faces) else None
    save_png(HEAD_PATHS[slot], make_head_png(img, face))
    return "Foto importada!" if face is not None else "Foto importada (cara não detetada, usei o centro)."


_CAMERAS = None   # lista de câmaras encontradas (procurada uma vez por sessão)


def probe_camera(index, backend):
    """Abre a câmara e confirma que devolve imagem. Devolve o cap ou None."""
    cap = cv2.VideoCapture(index, backend)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        for _ in range(10):  # a câmara pode demorar a devolver imagem
            ok, _frame = cap.read()
            if ok:
                return cap
    cap.release()
    return None


def find_cameras():
    """Lista as câmaras [{'index','backend','name'}] usando o backend que encontrar mais."""
    global ENUM_ERR
    found = {}
    if enumerate_cameras is not None:
        try:
            for info in enumerate_cameras():
                found.setdefault(info.backend, []).append(
                    {"index": info.index, "backend": info.backend, "name": info.name})
            if not found:
                ENUM_ERR = "a lista de câmaras veio vazia"
        except Exception as exc:
            found = {}
            ENUM_ERR = f"{type(exc).__name__}: {exc}"
    if ENUM_ERR:
        print("[aviso] nomes das câmaras indisponíveis:", ENUM_ERR)
    if not found:
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
            for i in range(10):
                cap = probe_camera(i, backend)
                if cap is not None:
                    cap.release()
                    found.setdefault(backend, []).append(
                        {"index": i, "backend": backend, "name": f"Câmara {i + 1}"})
    if not found:
        return []
    best = max(found, key=lambda b: (len(found[b]), b == cv2.CAP_MSMF))
    return found[best]


def open_from(start, cams):
    """Abre a primeira câmara que funcionar a partir de 'start'. Devolve (cap, posição, saltadas)."""
    skipped = []
    for step in range(len(cams)):
        pos = (start + step) % len(cams)
        cap = probe_camera(cams[pos]["index"], cams[pos]["backend"])
        if cap is not None:
            return cap, pos, skipped
        skipped.append(cams[pos]["name"])
    return None, start, skipped


def save_cam_index():
    try:
        with open(CAM_FILE, "w") as fh:
            fh.write(str(CAM_INDEX))
    except OSError:
        pass


def capture_head(screen, clock, font, slot):
    """Nunca deixa o jogo crashar: se algo falhar, devolve a mensagem de erro."""
    global _CAP
    if cv2 is None:
        return "Falta instalar: pip install opencv-python numpy"
    try:
        return _capture_head(screen, clock, font, slot)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return f"Erro na webcam: {type(exc).__name__}: {exc}"
    finally:
        if _CAP is not None:
            _CAP.release()
            _CAP = None


def _capture_head(screen, clock, font, slot):
    """Mostra a webcam; TAB troca de câmara, ESPAÇO tira a foto, ESC cancela."""
    global _CAP, _CAMERAS, CAM_INDEX
    if _CAMERAS is None:
        screen.fill((20, 22, 30))
        screen.blit(font.render("A procurar câmaras...", True, (255, 255, 255)), (W // 2 - 110, H // 2))
        pygame.display.flip()
        pygame.event.pump()
        _CAMERAS = find_cameras()
    cams = _CAMERAS
    if not cams:
        return import_head_from_file(slot, load_cascade())
    cap, pos, skipped = open_from(CAM_INDEX % len(cams), cams)
    _CAP = cap
    if cap is None:
        return "Nenhuma câmara devolveu imagem (outra app a usar? permissões?)."
    CAM_INDEX = pos
    status = ("Sem imagem: " + ", ".join(skipped)) if skipped else ""
    cascade = load_cascade()
    face, last, n = None, None, 0
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                cap.release()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "Captura cancelada."
                if e.key == pygame.K_TAB:                       # próxima câmara
                    cap.release()
                    cap, pos, skipped = open_from((pos + 1) % len(cams), cams)
                    _CAP = cap
                    if cap is None:
                        return "Nenhuma câmara devolveu imagem."
                    CAM_INDEX = pos
                    save_cam_index()
                    face, last = None, None
                    if len(cams) == 1:
                        status = "Só foi encontrada 1 câmara."
                    else:
                        status = ("Sem imagem: " + ", ".join(skipped)) if skipped else ""
                if e.key == pygame.K_f:                         # foto de um ficheiro
                    cap.release()
                    return import_head_from_file(slot, cascade)
                if e.key == pygame.K_SPACE and last is not None:
                    save_png(HEAD_PATHS[slot], make_head_png(last, face))
                    save_cam_index()
                    return "Foto guardada!"
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)  # espelho, como uma selfie
        last = frame
        if cascade is not None and n % 4 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
            face = max(faces, key=lambda f: f[2] * f[3]) if len(faces) else None
        n += 1

        screen.fill((20, 22, 30))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), "RGB")
        ox, oy = (W - surf.get_width()) // 2, (H - surf.get_height()) // 2
        screen.blit(surf, (ox, oy))
        cx, cy, sz = crop_box(frame, face)
        pygame.draw.circle(screen, (60, 255, 120) if face is not None else (255, 200, 60),
                           (int(ox + cx), int(oy + cy)), sz // 2, 3)
        txt = f"Cabeça do Jogador {slot + 1}: enquadra a cara e carrega ESPAÇO (ESC cancela)"
        screen.blit(font.render(txt, True, (255, 255, 255)), (W // 2 - 380, 20))
        txt2 = f"{cams[pos]['name']}  ({pos + 1}/{len(cams)})  -  TAB para trocar de câmara"
        screen.blit(font.render(txt2, True, (140, 200, 255)), (W // 2 - 380, 52))
        if status:
            screen.blit(font.render(status, True, (255, 170, 80)), (W // 2 - 380, 84))
        if ENUM_ERR:
            screen.blit(pygame.font.Font(None, 22).render(
                "Sem nomes de câmaras: " + ENUM_ERR[:90], True, (255, 170, 80)), (W // 2 - 380, 116))
        screen.blit(font.render("F = escolher uma foto de um ficheiro (ex.: tirada com a app Câmara)",
                                True, (140, 200, 255)), (W // 2 - 380, H - 80))
        if face is None:
            aviso = ("Cara não detetada - vou usar o centro da imagem" if cascade is not None
                     else "Sem deteção automática: põe a cara no centro do círculo")
            screen.blit(font.render(aviso, True, (255, 200, 60)), (W // 2 - 260, H - 45))
        pygame.display.flip()
        clock.tick(30)


# ---------------------------------------------------------------- cabeças (pixel art)
def pixelate_head(img, size):
    """Foto -> sprite quadrado 'size' com pixéis de HEAD_PIXEL, paleta reduzida e borda nítida."""
    base = max(8, size // HEAD_PIXEL)
    small = pygame.transform.smoothscale(img, (base, base)).convert_alpha()
    if np is not None:
        try:
            rgb = pygame.surfarray.pixels3d(small)
            rgb[:] = (rgb // 16) * 16 + 8              # 16 níveis por canal
            del rgb
            if HEAD_PIXEL > 1:
                alpha = pygame.surfarray.pixels_alpha(small)
                alpha[:] = np.where(alpha > 127, 255, 0)
                del alpha
        except Exception:
            pass
    if base != size:
        small = pygame.transform.scale(small, (size, size))
    return small


def default_head(slot, size):
    base = max(8, size // HEAD_PIXEL)
    s = pygame.Surface((base, base), pygame.SRCALPHA)
    c = (base - 1) / 2
    r = base / 2
    for y in range(base):
        for x in range(base):
            if (x - c) ** 2 + (y - c) ** 2 <= r * r:
                s.set_at((x, y), HAIRS[slot] if y < base * 0.22 else SKINS[slot])
    u = base / 23
    for ex in (6, 13):
        pygame.draw.rect(s, WHITE, (int(ex * u), int(9 * u), max(2, int(4 * u)), max(2, int(4 * u))))
        pygame.draw.rect(s, OUTLINE, (int((ex + 2) * u), int(10 * u), max(1, int(2 * u)), max(1, int(2 * u))))
    my = int(17 * u)
    pygame.draw.rect(s, (150, 40, 40), (int(8 * u), my, max(2, int(7 * u)), max(1, int(u))))
    s.set_at((int(7 * u), my - 1), (150, 40, 40))
    s.set_at((int(15 * u), my - 1), (150, 40, 40))
    if base != size:
        s = pygame.transform.scale(s, (size, size))
    return s


def load_head(slot, size):
    if os.path.exists(HEAD_PATHS[slot]):
        try:
            return pixelate_head(pygame.image.load(HEAD_PATHS[slot]).convert_alpha(), size)
        except pygame.error:
            pass
    return default_head(slot, size)


def load_heads():
    """Devolve (cabeças do jogo, retratos do ecrã) para os dois jogadores."""
    return ([load_head(i, 2 * HEAD_R) for i in (0, 1)],
            [load_head(i, PORT_SIZE) for i in (0, 1)])


# ---------------------------------------------------------------- física
class Ball:
    def __init__(self):
        self.ressalto, self.atrito = 0.72, 0.985               # mudam com o clima (chuva, neve...)
        self.reset()

    def reset(self):
        self.x, self.y = W / 2, 200
        self.vx, self.vy = random.choice((-2, 2)), 0
        self.ang = 0.0
        self.bounce = 0.0

    def forces(self):
        """Gravidade e limite de velocidade (uma vez por frame)."""
        self.bounce = 0.0
        self.vy += GRAV * 0.8
        self.ang += self.vx * 0.05
        sp = math.hypot(self.vx, self.vy)
        if sp > 24:
            self.vx, self.vy = self.vx * 24 / sp, self.vy * 24 / sp

    def move(self, f=1.0):
        """Move uma fração f do frame. O jogo usa sub-passos para a bola nunca atravessar nada."""
        self.x += self.vx * f
        self.y += self.vy * f
        if self.y > GROUND - BALL_R:
            self.y = GROUND - BALL_R
            if self.vy > 3:
                self.bounce = max(self.bounce, self.vy)
            self.vy *= -self.ressalto
            self.vx *= self.atrito ** f
            if abs(self.vy) < 1.5:
                self.vy = 0
        if self.y < BALL_R:
            self.y, self.vy = BALL_R, abs(self.vy)
        if self.x < BALL_R:
            self.x, self.vx = BALL_R, abs(self.vx) * 0.6
        if self.x > W - BALL_R:
            self.x, self.vx = W - BALL_R, -abs(self.vx) * 0.6
        self.collide_rect(pygame.Rect(0, CROSSBAR_Y - 7, GOAL_W, 14), 1)
        self.collide_rect(pygame.Rect(W - GOAL_W, CROSSBAR_Y - 7, GOAL_W, 14), -1)

    def update(self):
        self.forces()
        self.move(1.0)

    def clamp(self):
        self.y = max(BALL_R, min(GROUND - BALL_R, self.y))
        self.x = max(BALL_R, min(W - BALL_R, self.x))

    def collide_rect(self, rect, side=0):
        cx = max(rect.left, min(self.x, rect.right))
        cy = max(rect.top, min(self.y, rect.bottom))
        dx, dy = self.x - cx, self.y - cy
        d = math.hypot(dx, dy)
        if d < BALL_R:
            nx, ny = (dx / d, dy / d) if d else (0, -1)
            self.x += nx * (BALL_R - d)
            self.y += ny * (BALL_R - d)
            vn = self.vx * nx + self.vy * ny
            if vn < 0:
                self.vx -= 1.8 * vn * nx
                self.vy -= 1.8 * vn * ny
            if side and ny < -0.7 and abs(self.vy) < 2:      # bola parada em cima da barra: escorrega para o campo
                self.vx += 0.3 * side

    def collide_circle(self, cx, cy, r, cvx, cvy, e=1.85):
        """Colisão com um círculo em movimento. Devolve True se houve sobreposição."""
        dx, dy = self.x - cx, self.y - cy
        d = math.hypot(dx, dy)
        if d >= BALL_R + r:
            return False
        nx, ny = (dx / d, dy / d) if d else (0, -1)
        over = BALL_R + r - d
        self.x += nx * over
        self.y += ny * over
        vn = (self.vx - cvx) * nx + (self.vy - cvy) * ny
        if vn < 0:
            self.vx -= e * vn * nx
            self.vy -= e * vn * ny
        return True


class Leg:
    """Perna com duas articulações: coxa (mola) e canela (segue a coxa com atraso -> chicote)."""

    def __init__(self):
        self.a = 0.0   # ângulo da coxa (0 = para baixo, + = para a frente)
        self.w = 0.0
        self.r = 0.0   # ângulo do joelho relativo à coxa (negativo = dobrado)
        self.wr = 0.0

    def step(self, a_target, r_target, k, damp=0.84):
        old_w = self.w
        self.w += -k * (self.a - a_target)
        self.w *= damp
        self.a += self.w
        acc = self.w - old_w
        self.wr += -0.22 * (self.r - r_target) - acc * 0.9   # inércia da canela
        self.wr *= 0.86
        self.r += self.wr
        if self.r < -2.5:
            self.r, self.wr = -2.5, max(self.wr, 0) * 0.3
        if self.r > 0.1:
            self.r, self.wr = 0.1, min(self.wr, 0) * 0.3


class Player:
    def __init__(self, slot, x, facing, head):
        self.slot, self.start_x, self.start_facing, self.head = slot, x, facing, head
        self.reset()

    def reset(self):
        self.x = self.start_x
        self.y = GROUND - BODY_H - HEAD_R
        self.vx = self.vy = 0.0
        self.facing = self.start_facing
        self.on_ground = True
        self.kick_cd = 0
        self.kick_hit = False
        self.efeitos = {}                # power-ups ativos: {"velocidade": frames que faltam, ...}
        self.inercia = 1.0               # 1 = trava logo; perto de 0 = escorrega (neve)
        self.walk = 0.0
        self.legs = [Leg(), Leg()]      # 0 = perna que chuta (da frente), 1 = perna de trás
        for _ in range(30):
            self.update_legs(0)
        self.prev_pts, self.prev_facing, self.vel = None, self.facing, {}
        self.track()

    # -- geometria
    @property
    def hip(self):
        return self.x, self.y + HEAD_R + HIP_DY

    def leg_points(self, leg):
        hx, hy = self.hip
        f = self.facing
        kx = hx + f * math.sin(leg.a) * L1
        ky = hy + math.cos(leg.a) * L1
        b = leg.a + leg.r
        return (hx, hy), (kx, ky), (kx + f * math.sin(b) * L2, ky + math.cos(b) * L2)

    def leg_circles(self):
        out = []
        for i, leg in enumerate(self.legs):
            h, k, f = self.leg_points(leg)
            th = ((h[0] + k[0]) / 2, (h[1] + k[1]) / 2)
            m = ((k[0] + f[0]) / 2, (k[1] + f[1]) / 2)
            out += [((i, 3), th, 10), ((i, 0), k, 10), ((i, 1), m, 10), ((i, 2), f, 12)]
        return out

    def track(self):
        pts = {key: pos for key, pos, _ in self.leg_circles()}
        if self.prev_pts is None or self.facing != self.prev_facing:
            self.vel = {k: (self.vx, self.vy) for k in pts}
        else:
            self.vel = {k: (pts[k][0] - self.prev_pts[k][0], pts[k][1] - self.prev_pts[k][1])
                        for k in pts}
        self.prev_pts, self.prev_facing = pts, self.facing

    # -- lógica
    def update_legs(self, ax):
        kicking = self.kick_cd > KICK_COOLDOWN
        walking = self.on_ground and abs(self.vx) > 0.5
        if walking:
            self.walk += abs(self.vx) * 0.05
        for i, leg in enumerate(self.legs):
            ph = self.walk + (0 if i == 0 else math.pi)
            if i == 0 and kicking:
                at, rt, k = 1.2, -0.2, 0.22
            elif not self.on_ground:
                at, rt, k = (0.7, -1.0, 0.12) if i == 0 else (-0.35, -0.5, 0.12)
            elif walking:
                at, rt, k = 0.55 * math.sin(ph), -0.9 * max(0.0, math.cos(ph)), 0.16
            else:
                at, rt, k = (0.12, -0.05, 0.10) if i == 0 else (-0.12, 0.0, 0.10)
            leg.w -= ax * self.facing * 0.03       # as pernas ficam para trás ao acelerar
            leg.step(at, rt, k)

    def update(self, left, right, jump, kick, speed=SPEED, face=None):
        prev_vx = self.vx
        if "gelo" in self.efeitos or "atordoado" in self.efeitos:   # congelado ou atingido por um raio
            left = right = jump = kick = False
        if "velocidade" in self.efeitos:
            speed *= pw.MULT_VELOCIDADE
        alvo = (right - left) * speed
        self.vx = alvo if self.inercia >= 1 else self.vx + (alvo - self.vx) * self.inercia
        if face is not None:
            self.facing = face
        elif left and not right:
            self.facing = -1
        elif right and not left:
            self.facing = 1
        if jump and self.on_ground:
            self.vy = -JUMP * (pw.MULT_SALTO if "salto" in self.efeitos else 1)
        if kick and self.kick_cd == 0:
            self.kick_cd = KICK_FRAMES + KICK_COOLDOWN
            self.kick_hit = False
        self.vy += GRAV
        self.x = max(XMIN, min(XMAX, self.x + self.vx))
        self.y += self.vy
        floor = GROUND - BODY_H - HEAD_R
        self.on_ground = self.y >= floor
        if self.on_ground:
            self.y, self.vy = floor, 0
        self.update_legs(self.vx - prev_vx)
        if self.kick_cd > 0:
            self.kick_cd -= 1
        self.efeitos = pw.atualizar_efeitos(self.efeitos)
        self.track()

    def clamp_x(self):
        self.x = max(XMIN, min(XMAX, self.x))

    def colliders(self):
        """Formas sólidas, iguais ao que está desenhado: cabeça (com contorno), uma 'coluna' do tronco ao chão
        (a bola não passa entre as pernas), círculos ao longo das pernas e uma cápsula para cada bota."""
        v = (self.vx, self.vy)
        cols = [(self, None, "c", (self.x, self.y, HEAD_R + 2), v, 1.85),
                (self, "body", "s", (self.x, self.y + HEAD_R - 6, self.x, self.y + HEAD_R + BODY_H - 4, 24), v, 1.4)]
        for key, (x, y), r in self.leg_circles():
            vel = self.vel.get(key, v)
            if key[1] == 2:                                   # bota: do calcanhar até à ponta (como está desenhada)
                cx = x + 2 + 4 * self.facing
                cols.append((self, key, "s", (cx - 8, y, cx + 8, y, r + 1), vel, 1.7))
            else:
                cols.append((self, key, "c", (x, y, r), vel, 1.7))
        return cols

    def on_impact(self, key, ball, cvel):
        """Chamado quando uma parte do jogador bate mesmo na bola (remate e levantamento)."""
        if not isinstance(key, tuple):
            return
        if key[0] == 0 and self.kick_cd > KICK_COOLDOWN and not self.kick_hit:
            forca = pw.MULT_CHUTO if "super_chuto" in self.efeitos else 1
            ball.vx += self.facing * 6 * forca                  # remate
            ball.vy -= 5 * (1 + (forca - 1) / 2)                # e levanta a bola
            self.kick_hit = True
        elif math.hypot(*cvel) > 6:
            ball.vy -= 2.5


def resolve_ball(ball, players):
    """Resolve as colisões da bola com todos os jogadores: o contacto mais fundo primeiro e sem
    prioridade entre jogadores. Devolve ({jogador: tocou}, força do impacto)."""
    cols = [c for p in players for c in p.colliders()]
    touched = {p.slot: False for p in players}
    impact = 0.0
    for _ in range(8):
        best = None
        for col in cols:
            _, _, kind, g, _, _ = col
            if kind == "c":
                cx, cy, r = g
            else:
                ax, ay, bx, by, r = g
                abx, aby = bx - ax, by - ay
                t = ((ball.x - ax) * abx + (ball.y - ay) * aby) / (abx * abx + aby * aby)
                t = max(0.0, min(1.0, t))
                cx, cy = ax + abx * t, ay + aby * t
            dx, dy = ball.x - cx, ball.y - cy
            d = math.hypot(dx, dy)
            depth = BALL_R + r - d
            if depth > 0 and (best is None or depth > best[0]):
                best = (depth, dx, dy, d, col)
        if best is None:
            break
        depth, dx, dy, d, col = best
        owner, key, _, _, (cvx, cvy), e = col
        nx, ny = (dx / d, dy / d) if d > 1e-6 else (0.0, -1.0)
        ball.x += nx * depth
        ball.y += ny * depth
        touched[owner.slot] = True
        vn = (ball.vx - cvx) * nx + (ball.vy - cvy) * ny
        if vn < 0:
            ovx, ovy = ball.vx, ball.vy
            ball.vx -= e * vn * nx
            ball.vy -= e * vn * ny
            owner.on_impact(key, ball, (cvx, cvy))
            impact = max(impact, math.hypot(ball.vx - ovx, ball.vy - ovy))
    ball.clamp()
    return touched, impact


# Modo competitivo: cada vitória sobe de nível; uma derrota ou um empate acaba a corrida.
# (nome, velocidade do bot, probabilidade de chutar, probabilidade de saltar)
NIVEIS = [("Estreante", 4.0, 0.30, 0.10), ("Amador", 4.4, 0.40, 0.15), ("Profissional", 5.0, 0.50, 0.20),
          ("Estrela", 5.6, 0.60, 0.25), ("Lenda", 6.2, 0.75, 0.30)]
TEMPO_COMPETITIVO = 45


def nivel_bot(n):
    """Dificuldade do bot no nível n (1, 2, 3...). Depois do último nível o bot continua a ficar mais rápido."""
    if n <= len(NIVEIS):
        nome, vel, chuto, salto = NIVEIS[n - 1]
    else:
        extra = n - len(NIVEIS)
        nome, vel, chuto, salto = NIVEIS[-1]
        nome, vel = f"{nome} +{extra}", min(7.5, vel + 0.3 * extra)
    return {"nome": nome, "velocidade": vel, "chuto": chuto, "salto": salto}


def bot_controls(bot, ball, chuto=0.4, salto=0.15):
    if ball.x < W * 0.35:
        target = max(ball.x + 90, W * 0.58)
    else:
        target = ball.x + 60
    dx = target - bot.x
    left, right = dx < -12, dx > 12
    near = abs(ball.x - bot.x) < 150
    jump = near and ball.y < bot.y - 30 and ball.vy > -2 and random.random() < salto
    hip_x, hip_y = bot.hip
    dist = math.hypot(ball.x - hip_x, ball.y - hip_y)
    kick = (ball.x < bot.x + 5 and dist < 70 and ball.y > hip_y - 45 and random.random() < chuto)
    return left, right, jump, kick


# ---------------------------------------------------------------- desenho (resolução baixa)
def draw_pitch(bg):
    """Relvado e balizas (iguais em todos os estádios)."""
    gl = I(GROUND)
    for i, sx in enumerate(range(0, LW, 14)):
        col = (46, 150, 70) if i % 2 == 0 else (56, 170, 82)
        pygame.draw.rect(bg, col, (sx, gl, 14, LH - gl))
    pygame.draw.rect(bg, (36, 120, 56), (0, LH - 3, LW, 3))
    pygame.draw.rect(bg, (240, 240, 240), (0, gl, LW, 1))
    pygame.draw.rect(bg, (240, 240, 240), (LW // 2, gl, 1, LH - gl))
    cb, gw = I(CROSSBAR_Y), I(GOAL_W)
    for left in (True, False):
        x0 = 0 if left else LW - gw
        pygame.draw.rect(bg, (24, 30, 64), (x0, cb, gw, gl - cb))
        for gx in range(0, gw + 1, 3):
            pygame.draw.rect(bg, (150, 156, 190), (x0 + gx, cb, 1, gl - cb))
        for gy in range(cb, gl, 3):
            pygame.draw.rect(bg, (150, 156, 190), (x0, gy, gw, 1))
        post_x = gw - 2 if left else x0
        pygame.draw.rect(bg, WHITE, (post_x, cb, 2, gl - cb))
        pygame.draw.rect(bg, WHITE, (x0, cb - 2, gw, 3))
    return bg


# ---------------------------------------------------------------- fundos (estádios)
class Canvas:
    """Tela de pixéis pura (sem pygame) para desenhar cenários em pixel art."""

    def __init__(self, w, h, fill=(0, 0, 0)):
        self.w, self.h = w, h
        self.buf = bytearray(bytes(fill) * (w * h))
        self.clip = (0, 0, w, h)

    def px(self, x, y, c):
        x0, y0, x1, y1 = self.clip
        if x0 <= x < x1 and y0 <= y < y1:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def get(self, x, y):
        i = (y * self.w + x) * 3
        return tuple(self.buf[i:i + 3])

    def rect(self, x, y, w, h, c):
        x, y, w, h = int(x), int(y), int(w), int(h)
        x0, y0, x1, y1 = self.clip
        xa, xb = max(x, x0), min(x + w, x1)
        if xb <= xa:
            return
        row = bytes(c) * (xb - xa)
        for yy in range(max(y, y0), min(y + h, y1)):
            i = (yy * self.w + xa) * 3
            self.buf[i:i + len(row)] = row

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def to_surface(self):
        return pygame.image.frombuffer(bytes(self.buf), (self.w, self.h), "RGB").convert()


# ------------------------------------------------------------------ cenário de Lisboa
LIS_W, LIS_H, LIS_GL = 280, 160, 142          # desenhado para PX = 4
WATER_TOP, CANOPY_TOP, STANDS_TOP, BOARDS_TOP = 86, 102, 106, 134


def _ridge(x):
    if x < 150:
        base = 57 + (x / 150) * 5
    elif x < 178:
        base = 62 + ((x - 150) / 28) ** 1.5 * 9
    else:
        base = 71 + ((x - 178) / 102) * 6
    bump = 1.2 * math.sin(x * 0.19) + 0.8 * math.sin(x * 0.47 + 1)
    return int(base + bump)


def _cloud(cv, cx, cy, w):
    cv.rect(cx - w // 2 + 2, cy - 2, w - 4, 1, (248, 251, 255))
    cv.rect(cx - w // 2, cy - 1, w, 2, (248, 251, 255))
    cv.rect(cx - w // 2 + 3, cy + 1, w - 6, 1, (206, 224, 242))


def _cristo_rei(cv, cx, by):
    stone, shade, dark = (214, 214, 218), (150, 152, 164), (66, 70, 88)
    cv.rect(cx - 8, by - 3, 16, 3, shade)                  # plinto
    cv.rect(cx - 5, by - 27, 10, 24, stone)                # pedestal
    cv.rect(cx + 2, by - 27, 3, 24, shade)
    cv.rect(cx - 1, by - 15, 3, 12, dark)                  # abertura
    cv.rect(cx - 2, by - 16, 5, 1, dark)
    top = by - 27
    cv.rect(cx - 1, top - 10, 3, 10, stone)                # corpo
    cv.rect(cx - 5, top - 8, 11, 2, stone)                 # braços abertos
    cv.rect(cx - 1, top - 12, 3, 3, stone)                 # cabeça
    cv.rect(cx + 1, top - 10, 1, 10, shade)
    cv.rect(cx + 1, top - 7, 5, 1, shade)


def _ponte(cv, tx=228):
    red, red_l, red_d = (192, 54, 42), (230, 90, 62), (128, 34, 34)
    top = 9
    # tabuleiro
    anchor_x = 172
    for x in range(anchor_x, cv.w):
        y0 = int(71 - (x - anchor_x) * 3 / 108)
        cv.px(x, y0, (186, 176, 178))
        cv.px(x, y0 + 1, (104, 60, 66))
        cv.px(x, y0 + 2, (104, 60, 66))
        cv.px(x, y0 + 3, (64, 40, 48))
        if x % 3 == 0:
            cv.px(x, y0 + 4, (64, 40, 48))
    deck_y = lambda x: int(71 - (x - anchor_x) * 3 / 108)
    # bloco de ancoragem
    cv.rect(anchor_x - 4, 68, 9, 19, (190, 190, 196))
    cv.rect(anchor_x + 2, 68, 3, 19, (140, 142, 152))
    # cabos: vão lateral (esquerda)
    lx0 = tx - 5
    pts = []
    for x in range(anchor_x, lx0 + 1):
        t = (lx0 - x) / (lx0 - anchor_x)
        y = top + (69 - top) * (t ** 0.92)
        pts.append((x, int(y)))
        cv.px(x, int(y), red_d)
        cv.px(x, int(y) + 1, red)
    for x, y in pts[::5]:
        cv.line(x, y + 2, x, deck_y(x) - 1, (170, 56, 46))
    # cabos: vão principal (direita)
    rx0 = tx + 5
    pts = []
    for x in range(rx0, cv.w):
        u = (x - rx0) / (cv.w - 1 - rx0)
        y = top + 36 * (1 - (1 - u) ** 1.7)
        pts.append((x, int(y)))
        cv.px(x, int(y), red_d)
        cv.px(x, int(y) + 1, red)
    for x, y in pts[::5]:
        cv.line(x, y + 2, x, deck_y(x) - 1, (170, 56, 46))
    # torre
    base = 90
    for lx in (tx - 6, tx + 4):
        cv.rect(lx, top, 3, base - top, red)
        cv.rect(lx, top, 1, base - top, red_l)
        cv.rect(lx + 2, top, 1, base - top, red_d)
    for by in (top + 12, 27, 45, 62):
        cv.rect(tx - 6, by, 13, 2, red)
        cv.rect(tx - 6, by + 1, 13, 1, red_d)
    for (y0, y1) in ((top + 14, 27), (29, 45), (47, 62)):
        cv.line(tx - 3, y0, tx + 3, y1, red_d)
        cv.line(tx + 3, y0, tx - 3, y1, red_d)
    cv.rect(tx - 7, top - 2, 15, 3, red_d)
    cv.rect(tx - 6, top - 2, 13, 1, red_l)
    # pilar na água
    cv.rect(tx - 9, 83, 19, 8, (196, 196, 202))
    cv.rect(tx - 9, 83, 19, 1, (120, 122, 134))
    cv.rect(tx + 3, 84, 7, 7, (146, 148, 160))
    cv.rect(tx - 7, 91, 15, 1, (150, 90, 90))


def make_lisboa_canvas():
    W_, H_, GL = LIS_W, LIS_H, LIS_GL
    cv = Canvas(W_, H_, (30, 110, 60))
    rnd = random.Random(25)
    # céu
    for y in range(0, WATER_TOP + 1):
        t = y / WATER_TOP
        cv.rect(0, y, W_, 1, (int(92 + 74 * t), int(158 + 52 * t), int(226 + 16 * t)))
    for cx, cy, w in ((58, 22, 20), (150, 16, 26), (104, 38, 14), (196, 34, 16), (262, 20, 14)):
        _cloud(cv, cx, cy, w)
    for gx, gy in ((72, 12), (80, 16), (186, 26), (14, 40)):                 # gaivotas
        cv.px(gx, gy, (250, 250, 250)); cv.px(gx + 1, gy + 1, (250, 250, 250)); cv.px(gx + 2, gy, (250, 250, 250))
    # colina
    for x in range(W_):
        r = _ridge(x)
        for y in range(r, WATER_TOP):
            d = (y - r) / max(1, WATER_TOP - r)
            if y == r:
                c = (110, 168, 74)
            elif d < 0.25:
                c = (72, 134, 58)
            elif d < 0.65:
                c = (52, 110, 50)
            else:
                c = (36, 84, 46)
            v = rnd.random()
            if v < 0.10:
                c = (max(0, c[0] - 16), max(0, c[1] - 24), max(0, c[2] - 12))
            elif v > 0.94:
                c = (min(255, c[0] + 22), min(255, c[1] + 22), c[2])
            cv.px(x, y, c)
        if x < 165 or x > 190:
            cv.px(x, WATER_TOP - 1, (200, 180, 130))
            cv.px(x, WATER_TOP - 2, (176, 150, 104))
    cv.rect(26, 56, 24, 2, (96, 150, 66))
    _cristo_rei(cv, 38, _ridge(38) + 1)
    # rio
    for y in range(WATER_TOP, CANOPY_TOP):
        t = (y - WATER_TOP) / (CANOPY_TOP - WATER_TOP)
        base = (int(52 - 18 * t), int(128 - 30 * t), int(190 - 22 * t))
        cv.rect(0, y, W_, 1, base)
        for x in range(W_):
            if rnd.random() < 0.10:
                cv.px(x, y, (min(255, base[0] + 60), min(255, base[1] + 56), min(255, base[2] + 36)))
    cv.rect(0, WATER_TOP, W_, 1, (150, 196, 230))
    _ponte(cv)
    # bancadas
    cv.rect(0, STANDS_TOP, W_, BOARDS_TOP - STANDS_TOP, (22, 26, 58))
    palette = [(220, 60, 60), (240, 240, 240), (60, 160, 90), (240, 200, 60), (70, 120, 220), (230, 150, 110)]
    for y in range(STANDS_TOP, BOARDS_TOP):
        shade = 0.55 + 0.45 * (y - STANDS_TOP) / (BOARDS_TOP - STANDS_TOP)
        if (y - STANDS_TOP) % 7 == 6:
            cv.rect(0, y, W_, 1, (14, 16, 40))
            continue
        for x in range(W_):
            if x % 56 in (0, 1):
                cv.px(x, y, (14, 16, 40))
            elif rnd.random() < 0.62:
                c = rnd.choice(palette)
                cv.px(x, y, (int(c[0] * shade), int(c[1] * shade), int(c[2] * shade)))
    # bandeiras de Portugal
    for fx in (46, 100, 160, 214):
        cv.rect(fx, STANDS_TOP + 1, 1, 14, (220, 220, 228))
        cv.rect(fx + 1, STANDS_TOP + 1, 3, 4, (10, 110, 40))
        cv.rect(fx + 4, STANDS_TOP + 1, 4, 4, (210, 30, 30))
    # cobertura + pilares laterais
    cv.rect(0, CANOPY_TOP, W_, 4, (24, 28, 56))
    cv.rect(0, CANOPY_TOP, W_, 1, (70, 78, 120))
    for lx in range(6, W_, 14):
        cv.px(lx, CANOPY_TOP + 2, (255, 244, 170))
    cv.rect(0, 0, W_, 5, (22, 26, 54))
    cv.rect(0, 5, W_, 1, (70, 78, 120))
    for lx in range(8, W_, 12):
        cv.rect(lx, 2, 4, 2, (255, 244, 170))
    for px_ in (0, W_ - 4):
        cv.rect(px_, 5, 4, CANOPY_TOP - 5, (26, 30, 62))
        cv.rect(px_ + (3 if px_ == 0 else 0), 5, 1, CANOPY_TOP - 5, (70, 78, 120))
    # painéis de azulejo
    cv.rect(0, BOARDS_TOP - 1, W_, 1, (14, 16, 40))
    for x in range(W_):
        for y in range(BOARDS_TOP, GL):
            u, v = x % 8, y % 8
            d = abs(u - 3.5) + abs(v - 3.5)
            if d <= 1.0:
                c = (140, 184, 244)
            elif d <= 3.0 and d > 2.0:
                c = (36, 84, 170)
            elif u in (0, 7) and v in (0, 7):
                c = (36, 84, 170)
            else:
                c = (240, 245, 252)
            cv.px(x, y, c)
    return cv


# ------------------------------------------------------------------ utilitários
def disc(cv, cx, cy, r, c):
    for dy in range(-r, r + 1):
        w = int(math.sqrt(max(0, r * r - dy * dy)) + 0.5)
        cv.rect(cx - w, cy + dy, 2 * w + 1, 1, c)


FONT35 = {
    "A": ("010", "101", "111", "101", "101"), "C": ("011", "100", "100", "100", "011"),
    "D": ("110", "101", "101", "101", "110"), "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"), "G": ("011", "100", "101", "101", "011"),
    "I": ("111", "010", "010", "010", "111"), "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"), "N": ("110", "101", "101", "101", "101"),
    "O": ("111", "101", "101", "101", "111"), "P": ("110", "101", "110", "100", "100"),
    "R": ("110", "101", "110", "101", "101"), "S": ("011", "100", "010", "001", "110"),
    "T": ("111", "010", "010", "010", "010"), "U": ("101", "101", "101", "101", "111"),
    "X": ("101", "101", "010", "101", "101"), ".": ("000", "000", "000", "000", "010"),
    ",": ("000", "000", "000", "010", "100"), "!": ("010", "010", "010", "000", "010"),
}


def draw_text(cv, x, y, s, c, scale=1, gap=1):
    cx = x
    for ch in s:
        accent = ch == "Ó"
        g = FONT35.get("O" if accent else ch)
        if g is not None:
            for ry, row in enumerate(g):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        cv.rect(cx + rx * scale, y + ry * scale, scale, scale, c)
            if accent:
                cv.rect(cx + scale, y - 2 * scale, scale, scale, c)
        cx += (3 + gap) * scale
    return cx


def text_width(s, scale=1, gap=1):
    return len(s) * (3 + gap) * scale - gap * scale


def _stands(cv, rnd, boards):
    """Bancadas, cobertura, pilares e painéis (comuns aos estádios com paisagem)."""
    W_, GL = cv.w, LIS_GL
    cv.rect(0, STANDS_TOP, W_, BOARDS_TOP - STANDS_TOP, (22, 26, 58))
    palette = [(220, 60, 60), (240, 240, 240), (60, 160, 90), (240, 200, 60), (70, 120, 220), (230, 150, 110)]
    for y in range(STANDS_TOP, BOARDS_TOP):
        shade = 0.55 + 0.45 * (y - STANDS_TOP) / (BOARDS_TOP - STANDS_TOP)
        if (y - STANDS_TOP) % 7 == 6:
            cv.rect(0, y, W_, 1, (14, 16, 40))
            continue
        for x in range(W_):
            if x % 56 in (0, 1):
                cv.px(x, y, (14, 16, 40))
            elif rnd.random() < 0.62:
                c = rnd.choice(palette)
                cv.px(x, y, (int(c[0] * shade), int(c[1] * shade), int(c[2] * shade)))
    for fx in (46, 100, 160, 214):
        cv.rect(fx, STANDS_TOP + 1, 1, 14, (220, 220, 228))
        cv.rect(fx + 1, STANDS_TOP + 1, 3, 4, (10, 110, 40))
        cv.rect(fx + 4, STANDS_TOP + 1, 4, 4, (210, 30, 30))
    cv.rect(0, CANOPY_TOP, W_, 4, (24, 28, 56))
    cv.rect(0, CANOPY_TOP, W_, 1, (70, 78, 120))
    for lx in range(6, W_, 14):
        cv.px(lx, CANOPY_TOP + 2, (255, 244, 170))
    cv.rect(0, 0, W_, 5, (22, 26, 54))
    cv.rect(0, 5, W_, 1, (70, 78, 120))
    for lx in range(8, W_, 12):
        cv.rect(lx, 2, 4, 2, (255, 244, 170))
    for px_ in (0, W_ - 4):
        cv.rect(px_, 5, 4, CANOPY_TOP - 5, (26, 30, 62))
        cv.rect(px_ + (3 if px_ == 0 else 0), 5, 1, CANOPY_TOP - 5, (70, 78, 120))
    cv.rect(0, BOARDS_TOP - 1, W_, 1, (14, 16, 40))
    for i, bx in enumerate(range(0, W_, 28)):
        if boards == "piaget":
            cv.rect(bx, BOARDS_TOP, 27, 8, (150, 28, 38))
            draw_text(cv, bx + 2, BOARDS_TOP + 2, "PIAGET", (250, 238, 238))
        else:   # metro
            cv.rect(bx, BOARDS_TOP, 27, 8, (36, 56, 150))
            draw_text(cv, bx + (4 if i % 2 == 0 else 2), BOARDS_TOP + 1, "METRO" if i % 2 == 0 else "ALMADA", (248, 250, 255))
            cv.rect(bx, BOARDS_TOP + 7, 27, 1, (248, 250, 255))
        cv.rect(bx + 27, BOARDS_TOP, 1, 8, (14, 16, 40))


# ------------------------------------------------------------------ Instituto Piaget
def make_piaget_canvas():
    W_ = LIS_W
    cv = Canvas(W_, LIS_H, (30, 110, 60))
    rnd = random.Random(31)
    HZ = 90
    for y in range(0, 101):                                     # céu nublado
        t = y / 100
        cv.rect(0, y, W_, 1, (int(160 + 46 * t), int(170 + 42 * t), int(182 + 36 * t)))
    for x, y, w in ((6, 18, 64), (84, 12, 72), (176, 24, 84), (228, 10, 48), (30, 40, 52), (130, 36, 40)):
        cv.rect(x + 3, y, w - 6, 1, (150, 158, 170))
        cv.rect(x, y + 1, w, 2, (144, 152, 166))
        cv.rect(x + 4, y + 3, w - 8, 1, (182, 190, 200))
    for y in range(HZ, 101):                                    # relvado
        t = (y - HZ) / (101 - HZ)
        base = (int(120 - 24 * t), int(174 - 20 * t), int(62 - 8 * t))
        cv.rect(0, y, W_, 1, base)
        for x in range(W_):
            v = rnd.random()
            if v < 0.12:
                cv.px(x, y, (base[0] - 14, base[1] - 16, base[2] - 8))
            elif v > 0.95:
                cv.px(x, y, (base[0] + 16, base[1] + 14, base[2]))
    for bx, by, bw, bh in ((0, 80, 40, 10), (66, 84, 30, 6), (240, 80, 40, 10)):   # prédios cor-de-rosa
        cv.rect(bx, by, bw, bh, (224, 162, 152))
        cv.rect(bx, by - 2, bw, 2, (182, 90, 74))
        for wx in range(bx + 3, bx + bw - 3, 6):
            cv.rect(wx, by + 3, 3, 2, (70, 80, 100))
    cv.rect(44, 70, 1, 22, (160, 92, 60))                       # candeeiro
    disc(cv, 44, 69, 2, (248, 228, 172))
    # pinheiro-manso
    cv.rect(61, 66, 3, 26, (88, 68, 58))
    cv.rect(63, 66, 1, 26, (64, 50, 46))
    for ox, oy, r in ((52, 62, 8), (62, 57, 10), (72, 63, 8), (58, 66, 7), (68, 67, 7)):
        disc(cv, ox, oy, r, (44, 86, 52))
    for _ in range(90):
        x, y = rnd.randint(44, 80), rnd.randint(48, 72)
        if cv.get(x, y) == (44, 86, 52):
            cv.px(x, y, rnd.choice(((60, 112, 66), (30, 66, 42))))
    disc(cv, 18, 86, 6, (40, 90, 50))
    disc(cv, 28, 88, 5, (48, 100, 56))
    # --- painéis grandes
    cv.rect(90, 92, 150, 4, (216, 172, 162))                    # base cor-de-rosa
    cv.rect(90, 95, 150, 1, (176, 128, 122))
    cv.rect(236, 14, 11, 32, (150, 80, 58))                     # telhado e janela à direita
    cv.rect(240, 22, 5, 8, (230, 200, 120))
    cv.rect(236, 38, 26, 24, (136, 40, 50))
    cv.rect(249, 38, 13, 24, (70, 90, 150))
    for k in range(0, 24, 6):
        cv.line(236 + k, 61, 248 + k, 39, (240, 232, 232))
    cv.rect(236, 38, 26, 1, (236, 232, 232))
    # homem (esquerda)
    cv.rect(94, 40, 24, 54, (172, 198, 214))
    cv.rect(96, 70, 22, 24, (110, 172, 202))
    cv.rect(103, 72, 10, 22, (58, 62, 74))
    cv.rect(107, 66, 5, 6, (214, 164, 128))
    disc(cv, 109, 57, 7, (232, 182, 142))
    cv.rect(102, 49, 15, 4, (38, 30, 32)); cv.rect(102, 53, 3, 3, (38, 30, 32))
    cv.px(106, 57, (40, 30, 30)); cv.px(112, 57, (40, 30, 30))
    cv.rect(105, 62, 8, 1, (250, 248, 248))
    cv.rect(94, 88, 24, 6, (206, 166, 140))
    # painel vermelho central
    cv.rect(118, 6, 62, 88, (150, 26, 36))
    for y in range(52, 94):
        cv.rect(118, y, 62, 1, (146 - (y - 52) // 8, 24, 34))
    cx, cy = 149, 24
    disc(cv, cx, cy, 8, (246, 236, 236))
    disc(cv, cx, cy, 7, (150, 26, 36))
    for k in range(3):
        for i in range(22):
            a = k * 2.094 + i * 0.21
            r = 1 + i * 0.28
            cv.px(int(round(cx + r * math.cos(a))), int(round(cy + r * math.sin(a))), (246, 236, 236))
    draw_text(cv, cx - text_width("INSTITUTO") // 2, 40, "INSTITUTO", (250, 244, 244))
    draw_text(cv, cx - text_width("PIAGET", 2) // 2, 48, "PIAGET", (250, 244, 244), 2)
    draw_text(cv, cx - text_width("O FUTURO CERTO,") // 2, 66, "O FUTURO CERTO,", (240, 196, 204))
    draw_text(cv, cx - text_width("PRÓXIMO DE TI!") // 2, 73, "PRÓXIMO DE TI!", (240, 196, 204))
    draw_text(cv, cx - text_width("IPIAGET.ORG") // 2, 81, "IPIAGET.ORG", (250, 244, 244))
    # mulher (direita)
    cv.rect(180, 4, 56, 90, (232, 232, 238))
    disc(cv, 206, 29, 16, (150, 64, 44))
    disc(cv, 192, 38, 5, (150, 64, 44))
    disc(cv, 220, 38, 5, (150, 64, 44))
    for _ in range(80):
        x, y = rnd.randint(188, 224), rnd.randint(14, 44)
        if cv.get(x, y) == (150, 64, 44):
            cv.px(x, y, rnd.choice(((120, 46, 34), (176, 86, 56))))
    cv.rect(188, 54, 44, 40, (246, 246, 250))
    cv.rect(202, 44, 8, 9, (214, 164, 134))
    for i in range(6):
        cv.rect(202 - i // 2, 52 + i, 8 + i, 1, (214, 164, 134))
    disc(cv, 206, 35, 10, (236, 188, 162))
    cv.rect(200, 32, 3, 1, (60, 40, 40)); cv.rect(209, 32, 3, 1, (60, 40, 40))
    cv.px(201, 34, (50, 30, 30)); cv.px(210, 34, (50, 30, 30))
    cv.rect(202, 41, 8, 1, (204, 92, 104)); cv.rect(203, 42, 6, 1, (250, 244, 244))
    for y in range(54, 94):
        for x in range(216 + (y - 54) // 8, 236):
            cv.px(x, y, (30, 40, 92) if ((y - 54) // 3) % 2 == 0 else (232, 234, 242))
    # escultura e caminho
    cv.rect(131, 91, 14, 5, (180, 176, 170))
    cv.rect(131, 91, 14, 1, (210, 206, 200))
    cv.rect(133, 88, 10, 3, (84, 106, 74))
    cv.rect(134, 88, 4, 1, (130, 150, 110))
    for y in range(95, 101):
        cv.rect(0, y, 40 + (y - 95) * 10, 1, (180, 180, 184))
    _stands(cv, rnd, "piaget")
    return cv


# ------------------------------------------------------------------ Almada: fragata + Metro Sul do Tejo
def _fluffy(cv, cx, cy, s):
    for dx, dy, r in ((0, 0, 6), (-8, 2, 5), (8, 2, 5), (3, -4, 5), (-3, 3, 5), (12, 4, 4)):
        disc(cv, cx + dx * s // 2, cy + dy * s // 2, max(2, r * s // 2), (252, 253, 255))
    cv.rect(cx - 12 * s // 2, cy + 6 * s // 2, 28 * s // 2, max(1, s // 2), (206, 222, 240))


def _canhao(cv, x, yb):
    red, dark = (226, 60, 40), (30, 30, 36)
    cv.rect(x, yb - 3, 8, 2, red)
    cv.rect(x + 1, yb - 4, 5, 1, red)
    disc(cv, x + 2, yb - 1, 1, dark)
    disc(cv, x + 6, yb - 1, 1, dark)
    cv.line(x + 2, yb - 5, x + 12, yb - 9, dark)
    cv.line(x + 2, yb - 4, x + 12, yb - 8, dark)
    cv.rect(x + 11, yb - 10, 3, 3, dark)


def _fragata(cv):
    black, plank, white = (24, 24, 30), (36, 36, 44), (238, 238, 242)
    yellow, ydark, rig = (216, 172, 44), (156, 116, 30), (26, 26, 36)
    for x in range(30, 151):                                    # casco
        top = 78 if x < 118 else 78 - min(6, (x - 118) // 3)
        bottom = 96 if x >= 52 else 84 + int((x - 30) * 12 / 22)
        for y in range(top, bottom + 1):
            cv.px(x, y, plank if y % 3 == 0 else black)
    for x in range(40, 151):                                    # faixa branca e portinholas
        cv.px(x, 88, white)
        cv.px(x, 89, white)
        if x % 12 == 4:
            cv.rect(x, 88, 3, 2, black)
    cv.rect(31, 76, 3, 3, (240, 240, 244))                      # carranca
    cv.line(36, 77, 8, 52, yellow)                               # gurupés
    cv.line(36, 78, 8, 53, ydark)
    cv.line(37, 78, 9, 54, ydark)
    for mx, mtop, plat_y, plat_w in ((66, 14, 33, 20), (104, 20, 38, 17)):   # mastros
        cv.rect(mx - 1, mtop, 3, 78 - mtop, yellow)
        cv.rect(mx + 1, mtop, 1, 78 - mtop, ydark)
        cv.rect(mx - plat_w // 2, plat_y, plat_w, 3, (190, 150, 38))
        cv.rect(mx - plat_w // 2 + 2, plat_y + 3, plat_w - 4, 1, ydark)

    def ladder(a0, a1, b0, b1):
        cv.line(a0[0], a0[1], a1[0], a1[1], rig)
        cv.line(b0[0], b0[1], b1[0], b1[1], rig)
        for k in range(1, 10):
            t = k / 10
            cv.line(int(a0[0] + (a1[0] - a0[0]) * t), int(a0[1] + (a1[1] - a0[1]) * t),
                    int(b0[0] + (b1[0] - b0[0]) * t), int(b0[1] + (b1[1] - b0[1]) * t), rig)
    ladder((60, 36), (50, 78), (64, 36), (58, 78))
    ladder((72, 36), (84, 78), (68, 36), (76, 78))
    ladder((99, 41), (90, 77), (103, 41), (98, 77))
    ladder((109, 41), (120, 77), (105, 41), (112, 77))
    cv.line(67, 24, 8, 52, rig)                                  # estais
    cv.line(68, 26, 104, 30, rig)
    cv.line(105, 30, 138, 70, rig)
    cv.rect(141, 62, 1, 9, (200, 200, 208))                      # bandeira
    cv.rect(142, 62, 4, 3, (210, 30, 30))


def make_almada_canvas():
    W_ = LIS_W
    cv = Canvas(W_, LIS_H, (30, 110, 60))
    rnd = random.Random(44)
    for y in range(0, 102):                                     # céu
        t = y / 101
        cv.rect(0, y, W_, 1, (int(34 + 92 * t), int(100 + 84 * t), int(220 + 22 * t)))
    for cx, cy, s in ((40, 20, 4), (118, 14, 5), (190, 30, 4), (250, 16, 3), (84, 44, 3)):
        _fluffy(cv, cx, cy, s)
    cv.line(0, 10, W_, 50, (46, 56, 90))                         # fios da catenária
    cv.line(0, 24, W_, 62, (46, 56, 90))
    # torre de controlo (direita)
    cv.rect(251, 58, 6, 40, (198, 200, 206)); cv.rect(255, 58, 2, 40, (150, 152, 164))
    cv.rect(247, 96, 14, 4, (172, 174, 182))
    cv.rect(245, 48, 18, 2, (170, 172, 182)); cv.rect(246, 50, 16, 8, (216, 218, 224))
    cv.rect(247, 52, 14, 4, (40, 56, 84))
    cv.line(250, 48, 258, 38, (140, 96, 70)); cv.line(258, 48, 250, 38, (140, 96, 70))
    cv.rect(250, 36, 9, 2, (120, 122, 134)); cv.rect(254, 28, 1, 8, (120, 122, 134))
    _fragata(cv)
    # cais e carris
    cv.rect(0, 94, W_, 8, (178, 180, 184))
    cv.rect(0, 94, W_, 1, (208, 210, 214))
    for x in range(0, W_, 12):
        cv.rect(x, 95, 1, 6, (150, 152, 158))
    cv.rect(0, 100, W_, 1, (84, 86, 96))
    for x in (10, 38, 66):
        _canhao(cv, x, 98)
    # postes
    cv.rect(149, 30, 2, 66, (172, 176, 184)); cv.rect(151, 30, 1, 66, (122, 126, 136))
    cv.line(150, 32, 143, 31, (172, 176, 184)); cv.rect(140, 31, 4, 2, (240, 240, 250))
    cv.rect(212, 52, 1, 44, (160, 164, 172))
    _stands(cv, rnd, "metro")
    return cv


# ------------------------------------------------------------------ animações (funcionam em Canvas e em pygame via 'Pen')
def _mirror(d, x, length, flip):
    def r(u, v, w, h, c, y):
        px = x + (length - 1 - u - (w - 1)) if flip else x + u
        d.rect(int(px), int(y - v - h + 1), w, h, c)
    return r


def _ship_cargo(d, x, y, flip):
    r = _mirror(d, x, 36, flip)
    pal = [(206, 62, 50), (242, 200, 60), (62, 124, 204), (84, 172, 104), (236, 236, 236)]
    r(0, 0, 36, 1, (150, 44, 40), y)
    r(0, 1, 36, 2, (52, 58, 76), y)
    r(2, 3, 34, 1, (118, 122, 136), y)
    for i in range(5):
        for j in range(2 + (i * 7) % 2):
            r(5 + i * 5, 4 + j * 2, 4, 2, pal[(i * 3 + j) % 5], y)
    r(30, 4, 5, 6, (236, 238, 244), y)
    r(31, 8, 3, 1, (40, 50, 80), y)
    r(32, 10, 2, 2, (200, 60, 50), y)
    r(36, 0, 3, 1, (222, 238, 250), y)


def _ship_tanker(d, x, y, flip):
    r = _mirror(d, x, 26, flip)
    r(0, 0, 26, 2, (58, 58, 70), y)
    r(1, 2, 25, 1, (160, 64, 52), y)
    r(4, 3, 3, 1, (170, 170, 178), y); r(9, 3, 3, 1, (170, 170, 178), y); r(14, 3, 3, 1, (170, 170, 178), y)
    r(21, 3, 4, 4, (240, 240, 242), y)
    r(22, 5, 2, 1, (40, 50, 80), y)
    r(26, 0, 2, 1, (222, 238, 250), y)


def _ship_ferry(d, x, y, flip):
    r = _mirror(d, x, 17, flip)
    r(0, 0, 17, 3, (244, 244, 244), y)
    r(0, 1, 17, 1, (232, 120, 40), y)
    r(4, 3, 9, 3, (252, 252, 252), y)
    for u in (5, 7, 9, 11):
        r(u, 4, 1, 1, (50, 70, 110), y)
    r(8, 6, 1, 3, (80, 80, 90), y)
    r(17, 0, 2, 1, (222, 238, 250), y)


def _gull(d, x, y, flap):
    c = (252, 252, 252)
    if flap:
        d.px(x, y, c); d.px(x + 1, y + 1, c); d.px(x + 2, y, c)
    else:
        d.px(x, y + 1, c); d.px(x + 1, y, c); d.px(x + 2, y + 1, c)


def _draw_gulls(d, t, spec):
    for x0, y0, v, ph in spec:
        x = (x0 + v * t) % 330 - 25
        y = y0 + 3 * math.sin(t * 0.03 + ph)
        _gull(d, int(x), int(y), ((t // 9) + ph_int(ph)) % 2 == 0)


def ph_int(ph):
    return int(ph * 3)


def make_lisboa_anim():
    sparkles = [(random.Random(3).randint(6, 272), random.Random(i).randint(88, 100), i % 6) for i in range(60)]
    rr = random.Random(9)
    sparkles = [(rr.randint(6, 272), rr.randint(88, 100), rr.randint(0, 5)) for _ in range(60)]
    gulls = [(20, 16, 0.35, 0.0), (120, 30, 0.28, 1.7), (230, 12, 0.4, 3.1), (60, 44, 0.22, 4.4)]
    cars = [(0, -0.50, (210, 56, 50), 0), (46, -0.50, (240, 240, 244), 1), (88, -0.44, (60, 110, 210), 0),
            (20, 0.58, (240, 200, 60), 1), (70, 0.52, (70, 70, 80), 0), (104, 0.62, (80, 170, 100), 1)]

    def anim(d, t):
        for x, y, ph in sparkles:                                         # brilhos na água
            if (t // 10 + ph) % 6 == 0:
                d.px(x, y, (196, 228, 250))
        _ship_tanker(d, int((230 - 0.06 * t) % 340 - 40), 91, False)
        _ship_ferry(d, int((0.20 * t + 40) % 330 - 30), 96, True)
        _ship_cargo(d, int((0.10 * t + 20) % 350 - 45), 101, True)
        for x0, v, color, lane in cars:                                  # carros na ponte
            x = int(176 + (x0 + v * t) % 124)
            if x < 176:
                continue
            y0 = int(71 - (x - 172) * 3 / 108)
            d.rect(x, y0 - 2 - lane, 5, 2, color)
            d.rect(x + 1, y0 - 3 - lane, 3, 1, (max(0, color[0] - 60), max(0, color[1] - 60), max(0, color[2] - 60)))
            d.px(x + 1, y0 - 1 - lane, (24, 24, 30)); d.px(x + 3, y0 - 1 - lane, (24, 24, 30))
        _draw_gulls(d, t, gulls)
    return anim


def _tram(d, x, y):
    white, blue, glass, belt = (240, 244, 252), (36, 56, 150), (26, 32, 58), (70, 72, 82)
    nose = {0: 8, 1: 6, 2: 4, 3: 3, 4: 2, 5: 1}

    def row(u0, u1, dy, c, first=False):
        off = nose.get(dy, 0) if first else 0
        d.rect(x + u0 + off, y + dy, u1 - u0 - off, 1, c)
    for (u0, u1, first) in ((0, 58, True), (62, 100, False), (104, 132, False)):
        for dy in range(0, 3): row(u0, u1, dy, white, first)
        for dy in range(3, 5): row(u0, u1, dy, blue, first)
        for dy in range(5, 10): row(u0, u1, dy, glass, first)
        for dy in range(10, 13): row(u0, u1, dy, white, first)
        for dy in range(13, 15): row(u0, u1, dy, blue, first)
    for u in range(12, 56, 9):
        d.rect(x + u, y + 5, 1, 5, (60, 70, 104))
    for u in range(66, 98, 8):
        d.rect(x + u, y + 5, 1, 5, (60, 70, 104))
    for u in range(108, 130, 8):
        d.rect(x + u, y + 5, 1, 5, (60, 70, 104))
    for u in (40, 78, 112):                                              # portas
        d.rect(x + u, y + 4, 8, 9, (40, 70, 166))
        d.rect(x + u + 1, y + 5, 3, 7, glass); d.rect(x + u + 4, y + 5, 3, 7, glass)
    d.rect(x + 26, y + 3, 8, 1, (60, 210, 100))                          # destino "1 Cacilhas"
    d.rect(x + 3, y + 5, 7, 4, (70, 90, 130))                            # pára-brisas
    for u0 in (58, 100):                                                 # foles
        d.rect(x + u0, y + 1, 4, 14, belt)
        for k in range(2, 14, 3):
            d.rect(x + u0, y + k, 4, 1, (46, 48, 56))
    d.line(x + 66, y - 1, x + 72, y - 4, (30, 30, 40)); d.line(x + 72, y - 4, x + 78, y - 1, (30, 30, 40))
    d.rect(x + 68, y - 1, 8, 1, (30, 30, 40))                            # pantógrafo
    for u in (8, 46, 70, 92, 112):                                       # bogies
        d.rect(x + u, y + 15, 6, 1, (30, 30, 36))


def make_almada_anim():
    gulls = [(40, 22, 0.30, 0.6), (170, 40, 0.24, 2.2), (260, 14, 0.36, 4.0)]

    def anim(d, t):
        x = int(300 - 0.40 * t % 460)         # anda para a esquerda (a cabine vai à frente)
        _tram(d, x, 85)
        _draw_gulls(d, t, gulls)
    return anim


def make_piaget_anim():
    gulls = [(30, 20, 0.26, 1.0), (200, 30, 0.32, 2.8)]
    walkers = [(0.10, 40, (230, 80, 80)), (-0.08, 190, (70, 120, 220)), (0.07, 120, (240, 200, 60))]

    def anim(d, t):
        for v, x0, shirt in walkers:
            x = int((x0 + v * t) % 300 - 10)
            y = 100
            step = (t // 10) % 2
            d.rect(x, y - 7, 2, 2, (232, 184, 150))
            d.rect(x, y - 5, 2, 3, shirt)
            d.rect(x, y - 2, 1, 2, (40, 44, 70)); d.rect(x + 1, y - 2 + step, 1, 2 - step, (40, 44, 70))
        _draw_gulls(d, t, gulls)
    return anim


class Pen:
    """Mesma interface do Canvas, mas desenha numa Surface do pygame (com recorte)."""

    def __init__(self, surf, clip):
        self.s = surf
        self.s.set_clip(clip)

    def rect(self, x, y, w, h, c):
        pygame.draw.rect(self.s, c, (int(x), int(y), int(w), int(h)))

    def px(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < LW and 0 <= y < LH:
            self.s.set_at((x, y), c)

    def line(self, x0, y0, x1, y1, c):
        pygame.draw.line(self.s, c, (int(x0), int(y0)), (int(x1), int(y1)))

    def release(self):
        self.s.set_clip(None)


def run_anim(anim, low, t):
    """Desenha as animações do cenário (navios, carros, elétrico...) por cima do fundo."""
    pen = Pen(low, pygame.Rect(4, 6, LW - 8, 96))
    anim(pen, t)
    pen.release()
    draw_pitch(low)          # balizas por cima dos navios e do metro (ficam "atrás" da baliza)


def make_background():
    rnd = random.Random(7)
    bg = pygame.Surface((LW, LH))
    gl = I(GROUND)
    for y in range(gl):
        t = y / gl
        bg.fill((int(14 + 30 * t), int(18 + 34 * t), int(46 + 60 * t)), (0, y, LW, 1))
    crowd = [(220, 60, 60), (240, 200, 60), (60, 120, 230), (240, 240, 240),
             (230, 150, 110), (90, 200, 120), (160, 80, 200)]
    top = max(4, int(gl * 0.1))
    for y in range(top, gl - 8):
        shade = 0.35 + 0.65 * (y - top) / max(1, gl - 8 - top)
        for x in range(LW):
            if (y // 7) % 4 == 0:
                bg.set_at((x, y), (16, 18, 40))
            elif rnd.random() < 0.6:
                c = rnd.choice(crowd)
                bg.set_at((x, y), (int(c[0] * shade), int(c[1] * shade), int(c[2] * shade)))
    for _ in range(30):
        bg.set_at((rnd.randrange(LW), rnd.randrange(top + 4, gl - 10)), WHITE)
    board_cols = [(230, 70, 70), (240, 200, 60), (60, 130, 230), (80, 200, 120), (240, 240, 240)]
    for i, x in enumerate(range(0, LW, 28)):
        c = board_cols[i % len(board_cols)]
        pygame.draw.rect(bg, c, (x, gl - 8, 27, 7))
        pygame.draw.rect(bg, WHITE if c != (240, 240, 240) else OUTLINE, (x + 3, gl - 6, 21, 1))
        pygame.draw.rect(bg, WHITE if c != (240, 240, 240) else OUTLINE, (x + 3, gl - 4, 12, 1))
        pygame.draw.rect(bg, OUTLINE, (x + 27, gl - 8, 1, 7))
    return draw_pitch(bg)


def canvas_background(canvas):
    surf = canvas.to_surface()
    if surf.get_size() != (LW, LH):          # desenhado para PX = 4; outros valores são ampliados
        surf = pygame.transform.scale(surf, (LW, LH))
    return draw_pitch(surf)


def make_night_background(classic):
    n = classic.copy()
    n.fill((105, 115, 190), special_flags=pygame.BLEND_RGB_MULT)
    for x in range(14, LW, 36):                                   # holofotes
        pygame.draw.rect(n, (255, 250, 200), (x, 2, 8, 3))
        pygame.draw.rect(n, (210, 215, 160), (x + 1, 5, 6, 1))
    return n


def make_backgrounds():
    """Lista de (nome, fundo, animação ou None)."""
    classic = make_background()
    out = [("Clássico", classic, None),
           ("Lisboa", canvas_background(make_lisboa_canvas()), make_lisboa_anim()),
           ("Piaget", canvas_background(make_piaget_canvas()), make_piaget_anim()),
           ("Almada", canvas_background(make_almada_canvas()), make_almada_anim()),
           ("Noite", make_night_background(classic), None)]
    if (LW, LH) != (LIS_W, LIS_H):           # as animações estão desenhadas para PX = 4
        out = [(n, b_, None) for n, b_, _ in out]
    return out


STADIUM_FILE = os.path.join(HEAD_DIR, "estadio.txt")


def load_stadium_index():
    try:
        with open(STADIUM_FILE) as fh:
            return int(fh.read().strip())
    except Exception:
        return 0


def save_stadium_index(i):
    try:
        with open(STADIUM_FILE, "w") as fh:
            fh.write(str(i))
    except OSError:
        pass


# O texto do ecrã de baixa resolução é desenhado à resolução real da janela (nítido), por cima de tudo.
# main() regista aqui a superfície de baixa resolução e a letra de alta resolução de cada letra.
TEXTO_HD = {"low": None, "fontes": {}, "fila": []}
TEXTO_PIXEL = 2      # tamanho do "pixel" das letras: 1 = suave, 2 = pixelizado mas legível, 4 = como o cenário


def ptext(surf, font, msg, x, y, color=WHITE, align="center", shadow=True):
    if surf is TEXTO_HD["low"] and id(font) in TEXTO_HD["fontes"]:    # fica para desenhar nítido no fim
        TEXTO_HD["fila"].append((TEXTO_HD["fontes"][id(font)], msg, x * PX, y * PX, color, align, shadow))
        return
    img = font.render(msg, False, color)
    r = img.get_rect()
    if align == "center":
        r.center = (x, y)
    elif align == "left":
        r.midleft = (x, y)
    else:
        r.midright = (x, y)
    if shadow:
        sh = font.render(msg, False, OUTLINE)
        surf.blit(sh, r.move(1, 1))
    surf.blit(img, r)


def desenhar_textos(screen, ox=0, oy=0):
    """Desenha na janela, à resolução real, todo o texto guardado por ptext neste frame e esvazia a fila."""
    def render(msg, color):                                     # letra sem suavização, ampliada: fica pixelizada
        img = font.render(msg, False, color)
        return pygame.transform.scale(img, (img.get_width() * TEXTO_PIXEL, img.get_height() * TEXTO_PIXEL))
    for font, msg, x, y, color, align, shadow in TEXTO_HD["fila"]:
        img = render(msg, color)
        r = img.get_rect()
        if align == "center":
            r.center = (x + ox, y + oy)
        elif align == "left":
            r.midleft = (x + ox, y + oy)
        else:
            r.midright = (x + ox, y + oy)
        if shadow:
            screen.blit(render(msg, OUTLINE), r.move(TEXTO_PIXEL, TEXTO_PIXEL))
        screen.blit(img, r)
    TEXTO_HD["fila"].clear()


def alternar_ecra_inteiro():
    """Liga ou desliga o ecrã inteiro (F11). Devolve uma mensagem para o menu."""
    try:
        pygame.display.toggle_fullscreen()
        return "Ecrã inteiro: F11 para sair." if pygame.display.is_fullscreen() else "Modo janela."
    except (pygame.error, AttributeError):
        return "O ecrã inteiro não é suportado neste computador."


def draw_head(screen, sprite, cx, cy, flip=False):
    """As cabeças são desenhadas por cima do cenário, com mais detalhe que o resto."""
    r = sprite.get_width() // 2
    c = (int(cx), int(cy))
    pygame.draw.circle(screen, OUTLINE, c, r + 3)
    img = pygame.transform.flip(sprite, True, False) if flip else sprite
    screen.blit(img, img.get_rect(center=c))


def draw_leg(low, p, leg, team):
    h, k, f = [(I(a), I(b)) for a, b in p.leg_points(leg)]
    pygame.draw.line(low, OUTLINE, h, k, 5)
    pygame.draw.line(low, OUTLINE, k, f, 5)
    pygame.draw.line(low, SKIN_LEG, h, k, 3)
    pygame.draw.line(low, team["sock"], k, f, 3)
    bx = f[0] - 3 + (1 if p.facing == 1 else -1)
    by = f[1] - 2
    pygame.draw.rect(low, OUTLINE, (bx - 1, by - 1, 9, 6))
    pygame.draw.rect(low, (245, 245, 245), (bx, by, 7, 3))
    pygame.draw.rect(low, (60, 60, 70), (bx, by + 3, 7, 1))


def draw_arm(low, p, leg, team):
    sx, sy = I(p.x), I(p.y + HEAD_R - 4)
    ang = -leg.a * 0.8
    ex = sx + p.facing * math.sin(ang) * 7
    ey = sy + math.cos(ang) * 7
    pygame.draw.line(low, OUTLINE, (sx, sy), (round(ex), round(ey)), 4)
    pygame.draw.line(low, SKIN_LEG, (sx, sy), (round(ex), round(ey)), 2)


def draw_player(low, p):
    team = TEAMS[p.slot]
    gl = I(GROUND)
    feet_gap = GROUND - (p.y + HEAD_R + BODY_H)
    sw = max(10, int(30 - feet_gap / 10))
    pygame.draw.ellipse(low, SHADOW, (I(p.x) - sw // 2, gl - 1, sw, 4))
    draw_leg(low, p, p.legs[1], team)
    draw_arm(low, p, p.legs[1], team)
    top = I(p.y + HEAD_R - 8)
    bot = I(p.y + HEAD_R + HIP_DY + 4)
    body = pygame.Rect(I(p.x) - 5, top, 10, bot - top)
    pygame.draw.rect(low, OUTLINE, body.inflate(2, 2))
    pygame.draw.rect(low, team["shirt"], body)
    pygame.draw.rect(low, team["shorts"], (body.x, body.bottom - 3, body.w, 3))
    draw_leg(low, p, p.legs[0], team)
    draw_arm(low, p, p.legs[0], team)


def draw_ball(low, b):
    gl = I(GROUND)
    h = GROUND - (b.y + BALL_R)
    sw = max(4, int(12 - h / 40))
    pygame.draw.ellipse(low, SHADOW, (I(b.x) - sw // 2, gl - 1, sw, 3))
    c = (I(b.x), I(b.y))
    r = max(3, BALL_R // PX - 1)
    pygame.draw.circle(low, OUTLINE, c, r + 1)
    pygame.draw.circle(low, WHITE, c, r)
    for k in range(3):
        a = b.ang + k * 2.094
        px, py = c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6
        pygame.draw.rect(low, OUTLINE, (round(px) - 1, round(py) - 1, 2, 2))


def spawn(parts, x, y, n, colors, spread, up, life, size=1, grav=0.25):
    for _ in range(n):
        parts.append([x, y, random.uniform(-spread, spread), random.uniform(-up, 0),
                      random.choice(colors), life + random.randint(0, life // 2), size, grav])


def update_draw_particles(low, parts):
    for p in parts:
        p[0] += p[2]
        p[1] += p[3]
        p[3] += p[7]
        p[5] -= 1
        pygame.draw.rect(low, p[4], (I(p[0]), I(p[1]), p[6], p[6]))
    parts[:] = [p for p in parts if p[5] > 0]


# ---------------------------------------------------------------- principal
# ---------------------------------------------------------------- comandos (PS5, PS4, Xbox...)
class Pads:
    """Comandos por cabo ou Bluetooth. Usa o SDL GameController (os botões são iguais em todos os
    comandos: CRUZ = A, QUADRADO = X...) e, se não houver, o joystick genérico do pygame."""

    BTN = {0: "A", 1: "B", 2: "X", 3: "Y", 4: "BACK", 6: "START"}      # numeração do SDL GameController

    def __init__(self):
        self.ctl = None
        try:
            from pygame._sdl2 import controller as ctl
            ctl.init()
            self.ctl = ctl
        except Exception:
            self.ctl = None
        try:
            pygame.joystick.init()
        except Exception:
            pass
        self.devs, self.count = [], -1
        self.rescan()

    def rescan(self):
        for d in self.devs:
            if d["kind"] == "ctl":
                try:
                    d["obj"].quit()
                except Exception:
                    pass
        self.devs = []
        try:
            n = pygame.joystick.get_count()
        except Exception:
            n = 0
        for i in range(n):
            dev = None
            if self.ctl is not None:
                try:
                    if self.ctl.is_controller(i):
                        dev = {"kind": "ctl", "obj": self.ctl.Controller(i),
                               "name": str(self.ctl.name_forindex(i) or "Comando")}
                except Exception:
                    dev = None
            if dev is None:
                try:
                    j = pygame.joystick.Joystick(i)
                    iid = j.get_instance_id() if hasattr(j, "get_instance_id") else i
                    dev = {"kind": "joy", "obj": j, "name": j.get_name(), "iid": iid}
                except Exception:
                    continue
            self.devs.append(dev)
        self.count = n

    def update(self, tick):
        """Procura comandos novos (ou desligados) a cada segundo."""
        if tick % 60 == 0:
            try:
                n = pygame.joystick.get_count()
            except Exception:
                n = 0
            if n != self.count:
                self.rescan()

    def names(self):
        return [d["name"] for d in self.devs]

    def short_status(self):
        n = len(self.devs)
        return "" if n == 0 else ("Comando ligado" if n == 1 else f"{n} comandos ligados")

    @staticmethod
    def state_ctl(c):
        ax, ay = c.get_axis(0) / 32768.0, c.get_axis(1) / 32768.0
        left = ax < -0.35 or c.get_button(13)
        right = ax > 0.35 or c.get_button(14)
        jump = ay < -0.6 or c.get_button(0) or c.get_button(11)                   # analógico para cima, CRUZ ou seta
        kick = (c.get_button(2) or c.get_button(1) or c.get_button(10)             # QUADRADO, CÍRCULO, R1
                or c.get_axis(5) > 8000)                                           # R2
        return bool(left), bool(right), bool(jump), bool(kick)

    @staticmethod
    def state_joy(j):
        nb = j.get_numbuttons()
        ax = j.get_axis(0) if j.get_numaxes() > 0 else 0.0
        ay = j.get_axis(1) if j.get_numaxes() > 1 else 0.0
        hat = j.get_hat(0) if j.get_numhats() > 0 else (0, 0)
        btn = lambda b: b < nb and j.get_button(b)
        return (bool(ax < -0.35 or hat[0] < 0), bool(ax > 0.35 or hat[0] > 0),
                bool(ay < -0.6 or hat[1] > 0 or btn(0) or btn(1)), bool(btn(2) or btn(3)))

    def states(self):
        """(esquerda, direita, saltar, chutar) de cada comando ligado."""
        out = []
        for d in self.devs:
            try:
                out.append(self.state_ctl(d["obj"]) if d["kind"] == "ctl" else self.state_joy(d["obj"]))
            except Exception:
                out.append((False, False, False, False))
        return out

    def event_key(self, e, state):
        """Converte um botão do comando na tecla equivalente (para navegar nos menus)."""
        name = None
        if e.type == getattr(pygame, "CONTROLLERBUTTONDOWN", -1):
            name = self.BTN.get(e.button)
        elif e.type == pygame.JOYBUTTONDOWN:
            iid = getattr(e, "instance_id", None)
            if any(d["kind"] == "joy" and d.get("iid") == iid for d in self.devs):
                name = {0: "A", 1: "A", 2: "X", 3: "Y", 6: "START", 7: "START", 8: "BACK", 9: "BACK"}.get(e.button)
        if name is None:
            return None
        if state == "menu":
            return {"A": pygame.K_1, "Y": pygame.K_2, "X": pygame.K_b, "START": pygame.K_TAB}.get(name)
        if state == "controls":
            return pygame.K_ESCAPE if name in ("A", "B", "START", "BACK") else None
        if state == "game":
            return pygame.K_ESCAPE if name == "BACK" else None
        if state == "over":
            return {"A": pygame.K_RETURN, "START": pygame.K_RETURN, "BACK": pygame.K_ESCAPE}.get(name)
        if state in ("historico", "estatisticas"):
            return pygame.K_ESCAPE if name in ("A", "B", "START", "BACK") else None
        return None


def read_inputs(keys, pad_states, mode):
    """Junta teclado e comandos. 1 jogador: o comando controla o J1. 2 jogadores: com 1 comando
    ele controla o J2; com 2 comandos, cada um controla o seu jogador."""
    k1 = (keys[pygame.K_a], keys[pygame.K_d], keys[pygame.K_w], keys[pygame.K_SPACE])
    k2 = (keys[pygame.K_LEFT], keys[pygame.K_RIGHT], keys[pygame.K_UP], keys[pygame.K_RETURN])

    def merge(a, b):
        return tuple(bool(x or y) for x, y in zip(a, b))
    in1, in2 = k1, k2
    if mode == 1:
        if pad_states:
            in1 = merge(k1, pad_states[0])
    elif len(pad_states) >= 2:
        in1, in2 = merge(k1, pad_states[0]), merge(k2, pad_states[1])
    elif len(pad_states) == 1:
        in2 = merge(k2, pad_states[0])
    return in1, in2


# ---------------------------------------------------------------- lógica da partida
class Match:
    """Toda a lógica de uma partida (sem desenho), para ser fácil de testar."""

    def __init__(self, mode, heads, nivel=1, nomes=("Jogador 1", "Jogador 2"), clima="aleatorio"):
        """mode: 1 = contra o bot, 2 = dois jogadores, 3 = competitivo (bot do nível indicado)."""
        self.mode, self.nivel = mode, nivel
        self.p1 = Player(0, W * 0.25, 1, heads[0])
        self.p2 = Player(1, W * 0.75, -1, heads[1])
        self.ball = Ball()
        self.score = [0, 0]
        self.bot = nivel_bot(nivel if mode == 3 else 2)          # o modo 1 usa sempre o bot "Amador"
        self.nomes = list(nomes) if mode == 2 else [nomes[0], "Bot " + self.bot["nome"] if mode == 3 else "Bot"]
        self.time_left = float(TEMPO_COMPETITIVO if mode == 3 else MATCH_TIME)
        self.pw = {"lista": [], "espera": 300}                  # primeiro power-up aos 5 segundos
        self.aviso, self.aviso_t = "", 0
        self.clima = cl.novo_estado(clima, XMIN, XMAX)
        self.pause, self.banner = 0, ""
        self.parts, self.shake = [], 0.0
        self.stuck, self.last_touch, self.jumpball = 0, [99, 99], 0
        self.over = False

    def goal(self, scorer):
        self.score[scorer] += 1
        self.banner, self.pause, self.shake = f"GOLO de {self.nomes[scorer]}!", 110, 10
        gx = GOAL_W if scorer == 1 else W - GOAL_W
        spawn(self.parts, gx, CROSSBAR_Y, 90, [(255, 80, 80), (255, 230, 80), (80, 200, 255), WHITE], 6, 10, 50, 2)

    def step(self, in1, in2):
        p1, p2, ball = self.p1, self.p2, self.ball
        self.shake *= 0.85
        if self.pause > 0:
            self.pause -= 1
            if self.pause == 0:
                p1.reset(); p2.reset(); ball.reset()
                self.banner, self.stuck, self.last_touch = "", 0, [99, 99]
            return
        if self.jumpball == 0:
            self.time_left -= 1 / 60
        if self.aviso_t > 0:
            self.aviso_t -= 1
        fis = cl.params(self.clima)                             # física do clima atual
        ball.ressalto, ball.atrito = fis["ressalto"], fis["atrito"]
        p1.inercia = p2.inercia = fis["inercia"]
        p1.update(*in1, speed=SPEED * cl.velocidade(self.clima, p1))
        if self.mode in (1, 3):
            l, r, j, k = bot_controls(p2, ball, self.bot["chuto"], self.bot["salto"])
            p2.update(l, r, j, k, speed=self.bot["velocidade"] * cl.velocidade(self.clima, p2), face=-1)
        else:
            p2.update(*in2, speed=SPEED * cl.velocidade(self.clima, p2))
        if self.jumpball == 0:
            for tipo, x in cl.passo_clima(self.clima, (p1, p2), ball, GROUND - BALL_R):
                if tipo == "mudou":
                    self.aviso, self.aviso_t = x, 150
                elif tipo == "raio":
                    self.shake = 9
                    spawn(self.parts, x, GROUND - 4, 40, [(255, 255, 160), WHITE, (160, 200, 255)], 6, 8, 25, 1, 0.2)
                elif tipo == "fogo":
                    spawn(self.parts, x, GROUND - 4, 14, [(255, 120, 30), (255, 210, 60), (90, 80, 80)], 2.5, 5, 22, 1, -0.05)
                elif tipo == "chapinhar":
                    spawn(self.parts, x, GROUND - 2, 4, [(140, 190, 255), (210, 230, 255)], 2.5, 3, 14, 1, 0.25)
        if self.jumpball == 0:
            apanhado = pw.passo_powerups(self.pw, (p1, p2), XMIN, XMAX, GROUND - BODY_H - HEAD_R + 10)
            if apanhado:
                quem, texto = apanhado
                self.aviso, self.aviso_t = f"{self.nomes[quem.slot]}: {texto}!", 90
                spawn(self.parts, quem.x, quem.y, 30, [(255, 240, 120), WHITE, (120, 220, 255)], 4, 4, 30, 1, 0.1)
        d = p2.x - p1.x
        if abs(d) < HEAD_R * 1.6 and abs(p1.y - p2.y) < HEAD_R * 1.6:
            push = (HEAD_R * 1.6 - abs(d)) / 2 * (1 if d >= 0 else -1)
            p1.x -= push
            p2.x += push
        p1.clamp_x(); p2.clamp_x()

        if self.jumpball > 0:                                   # bola ao ar: a bola fica parada no ar
            self.jumpball -= 1
            ball.x, ball.y, ball.vx, ball.vy = W / 2, 190, 0, 0
            if self.jumpball == 0:
                ball.vy = -12.5                                 # e é lançada ao ar
        else:
            ball.forces()
            touched, impact = {0: False, 1: False}, 0.0
            for _ in range(3):                                  # sub-passos: a bola nunca atravessa ninguém
                ball.move(1 / 3)
                t, imp = resolve_ball(ball, (p1, p2))
                touched = {k: touched[k] or t[k] for k in touched}
                impact = max(impact, imp)
            if ball.bounce > 6:
                spawn(self.parts, ball.x, GROUND - 2, 6, [(200, 230, 190), (150, 200, 150)], 2.5, 2.5, 12, 1, 0.15)
            if impact > 9:
                spawn(self.parts, ball.x, ball.y, 6, [(255, 240, 120), WHITE], 3, 3, 10, 1, 0.1)
            self.last_touch = [0 if touched[0] else self.last_touch[0] + 1,
                               0 if touched[1] else self.last_touch[1] + 1]
            lo, hi = min(p1.x, p2.x), max(p1.x, p2.x)
            pinned = self.last_touch[0] < 8 and self.last_touch[1] < 8 and lo - 10 <= ball.x <= hi + 10
            self.stuck = self.stuck + 1 if pinned else max(0, self.stuck - 2)
            if self.stuck >= STUCK_FRAMES:                      # bola presa 3 s -> bola ao ar
                self.stuck, self.last_touch, self.jumpball = 0, [99, 99], JUMPBALL_FRAMES
                p1.reset(); p2.reset()
                ball.x, ball.y, ball.vx, ball.vy = W / 2, 190, 0, 0
            elif ball.y > CROSSBAR_Y and ball.x < GOAL_LINE:
                self.goal(1)
            elif ball.y > CROSSBAR_Y and ball.x > W - GOAL_LINE:
                self.goal(0)
        if self.time_left <= 0:
            self.over = True
            p1.reset(); p2.reset()


def draw_controls(low, fn, pads):
    """Aba de controlos do menu."""
    painel(low, 8, 3, LW - 16, 154, 215)
    ptext(low, fn["big"], "CONTROLOS", LW // 2, 14, (255, 230, 80))

    def block(x, y, title, color, lines, off):
        ptext(low, fn["sm"], title, x, y, color, align="left")
        for i, (k, v) in enumerate(lines):
            ptext(low, fn["sm"], k, x, y + 10 + i * 10, WHITE, align="left")
            ptext(low, fn["sm"], v, x + off, y + 10 + i * 10, (170, 210, 255), align="left")
    block(16, 29, "JOGADOR 1  (teclado)", (130, 180, 255), [("A / D", "mover"), ("W", "saltar"), ("ESPAÇO", "chutar")], 50)
    block(140, 29, "JOGADOR 2  (teclado)", (255, 140, 140),
          [("SETAS ESQ/DIR", "mover"), ("SETA CIMA", "saltar"), ("ENTER", "chutar")], 86)
    block(16, 72, "COMANDO  (PS5, PS4, Xbox...)", (160, 230, 160),
          [("Analógico esquerdo ou setas", "mover"), ("CRUZ (X)", "saltar"),
           ("QUADRADO, CÍRCULO, R1, R2", "chutar")], 168)
    for i, t in enumerate(("Menu: CRUZ = vs Bot  ·  TRIÂNGULO = 2 jogadores",
                           "QUADRADO = estádio  ·  OPTIONS = controlos",
                           "No jogo: CREATE = menu  ·  F11 = ecrã inteiro")):
        ptext(low, fn["sm"], t, 16, 114 + i * 10, (255, 240, 150), align="left")
    names = ", ".join(pads.names())
    status = ("Comandos: " + (names[:20] + ("…" if len(names) > 20 else ""))) if names else "Nenhum comando ligado"
    ptext(low, fn["sm"], status, 16, 148, (150, 230, 160), align="left")
    ptext(low, fn["sm"], "TAB / ESC  voltar", LW - 16, 148, WHITE, align="right")


def painel(low, x, y, w, h, alpha=200):
    """Retângulo escuro semitransparente para os ecrãs de texto."""
    p = pygame.Surface((w, h), pygame.SRCALPHA)
    p.fill((8, 10, 30, alpha))
    low.blit(p, (x, y))


def draw_powerups(low, fn, m, tick):
    """Desenha os power-ups no campo, o gelo nos jogadores congelados, os efeitos ativos e o aviso de quem apanhou."""
    for pu in m.pw["lista"]:
        if pu.vida < 120 and (tick // 6) % 2:                   # pisca antes de desaparecer
            continue
        texto, _, cor, _ = pw.TIPOS[pu.tipo]
        x, y = I(pu.x), I(pu.y) + int(math.sin(tick * 0.12) * 2)
        pygame.draw.circle(low, OUTLINE, (x, y), 8)
        pygame.draw.circle(low, cor, (x, y), 7)
        pygame.draw.circle(low, WHITE, (x - 2, y - 3), 2)
        simbolo = {"velocidade": ">>", "super_chuto": "!", "salto": "^", "gelo": "*"}[pu.tipo]
        ptext(low, fn["sm"], simbolo, x, y + 1, OUTLINE, shadow=False)
    for pl in (m.p1, m.p2):
        if "gelo" in pl.efeitos:
            gelo = pygame.Surface((I(HEAD_R * 2) + 6, I(HEAD_R * 2 + BODY_H) + 6), pygame.SRCALPHA)
            gelo.fill((150, 220, 255, 110))
            low.blit(gelo, (I(pl.x - HEAD_R) - 3, I(pl.y - HEAD_R) - 3))
        icones = [k for k in pl.efeitos if k in pw.TIPOS]          # (atordoado/queimado não têm barra)
        for n, k in enumerate(icones):                          # efeitos ativos por baixo do retrato
            cor = pw.TIPOS[k][2]
            bx = (LW // 2 - 76 - 20 * n) if pl.slot == 0 else (LW // 2 + 58 + 20 * n)
            frac = pl.efeitos[k] / pw.TIPOS[k][1]
            pygame.draw.rect(low, OUTLINE, (bx, 22, 18, 4))
            pygame.draw.rect(low, cor, (bx + 1, 23, max(1, int(16 * frac)), 2))
    if m.aviso_t > 0:
        ptext(low, fn["mid"], m.aviso, LW // 2, 49, (255, 240, 150))


def draw_clima_fundo(low, m, tick):
    """Desenha o clima no chão (por trás dos jogadores): poças, neve acumulada, fumo e fogo, aviso do relâmpago."""
    c, gl = m.clima, I(GROUND)
    for p in c["pocas"]:                                        # poças de água
        if p["larg"] > 4:
            w = max(2, I(p["larg"]))
            pygame.draw.ellipse(low, (40, 80, 160), (I(p["x"]) - w // 2 - 1, gl - 3, w + 2, 7))
            pygame.draw.ellipse(low, (80, 140, 225), (I(p["x"]) - w // 2, gl - 2, w, 5))
            pygame.draw.line(low, (190, 225, 255), (I(p["x"]) - w // 4, gl - 1), (I(p["x"]) + w // 6, gl - 1))
            if (tick + int(p["x"])) % 20 < 3:                       # pingos a cair na poça
                low.set_at((I(p["x"]) + (tick * 7) % max(1, w) - w // 2, gl - 3), (220, 240, 255))
    if c["neve_chao"] > 0.05:                                   # neve acumulada no relvado
        neve = pygame.Surface((LW, 4), pygame.SRCALPHA)
        neve.fill((245, 250, 255, int(230 * c["neve_chao"])))
        low.blit(neve, (0, gl - 1))
    for f in c["fogos"]:
        fx = I(f["x"])
        meia = I(cl.FOGO_LARG) // 2
        if f["aviso"] > 0:                                      # fumo: vai pegar fogo aqui
            for i in range(5):
                sobe = (tick + i * 11) % 30
                pygame.draw.circle(low, (110, 110, 110), (fx - meia + 3 + i * (meia * 2 - 6) // 4, gl - 2 - sobe // 3), 1 + sobe // 12)
        else:                                                   # fogo
            pygame.draw.rect(low, (60, 30, 20), (fx - meia, gl - 1, meia * 2, 2))
            for i in range(meia * 2):
                h = 6 + (i * 7 + tick // 3 * 13) % 9
                x = fx - meia + i
                pygame.draw.line(low, (220, 50, 20), (x, gl), (x, gl - h))
                pygame.draw.line(low, (255, 140, 30), (x, gl), (x, gl - h * 2 // 3))
                pygame.draw.line(low, (255, 230, 90), (x, gl), (x, gl - h // 3))
    if c["raio"] is not None and (tick // 5) % 2:               # aviso do relâmpago: alvo a piscar
        x, alc = I(c["raio"]["x"]), I(cl.RAIO_ALCANCE)
        zona = pygame.Surface((alc * 2, gl), pygame.SRCALPHA)           # coluna onde vai cair o raio
        zona.fill((255, 230, 60, 45))
        low.blit(zona, (x - alc, 0))
        pygame.draw.ellipse(low, (255, 230, 60), (x - alc, gl - 3, alc * 2, 7), 2)
        for y in range(0, gl - 4, 8):
            pygame.draw.line(low, (255, 230, 60), (x, y), (x, y + 3))


def draw_clima_frente(low, m, tick):
    """Desenha o clima por cima de tudo: chuva, neve, calor, relâmpago e jogadores atordoados."""
    c, atual = m.clima, m.clima["atual"]
    tons = {"chuva": (20, 30, 60, 50), "trovoada": (10, 15, 40, 90), "neve": (200, 220, 255, 35), "calor": (255, 140, 40, 35)}
    if atual in tons:
        veu = pygame.Surface((LW, LH), pygame.SRCALPHA)
        veu.fill(tons[atual])
        low.blit(veu, (0, 0))
    if atual in ("chuva", "trovoada"):
        n = 90 if atual == "chuva" else 140
        for i in range(n):
            x = (i * 53 + tick * 2) % (LW + 30) - 15
            y = (i * 97 + tick * 7) % (LH + 10) - 5
            pygame.draw.line(low, (170, 195, 240), (x, y), (x - 2, y + 5))
    elif atual == "neve":
        for i in range(80):
            x = int((i * 43 + math.sin(tick * 0.03 + i) * 6) % LW)
            y = int((i * 61 + tick * 0.7) % LH)
            low.fill((250, 250, 255), (x, y, 1 + (i % 3 == 0), 1 + (i % 3 == 0)))
    elif atual == "calor":
        for i in range(12):                                     # faúlhas a subir
            x = (i * 71 + tick // 2) % LW
            y = LH - 20 - (i * 29 + tick) % 90
            low.set_at((x, y), (255, 170, 60))
    for pl in (m.p1, m.p2):                                     # estrelas à volta de quem levou com um raio
        if "atordoado" in pl.efeitos:
            for k in range(3):
                a = tick * 0.2 + k * 2.1
                low.fill((255, 240, 80), (I(pl.x) + int(math.cos(a) * 10), I(pl.y - HEAD_R) - 3 + int(math.sin(a) * 2), 2, 2))
    if c["flash"] > 0:                                          # relâmpago
        x = I(c["ultimo_raio"] or W / 2)
        pts, y = [(x, 0)], 0
        while y < I(GROUND):
            y += 12
            pts.append((x + random.randint(-6, 6), min(y, I(GROUND))))
        pygame.draw.lines(low, (255, 255, 200), False, pts, 2)
        luz = pygame.Surface((LW, LH), pygame.SRCALPHA)
        luz.fill((255, 255, 255, 25 * c["flash"]))
        low.blit(luz, (0, 0))


def draw_nome(low, fn, texto, erro, tick):
    """Ecrã para escrever o nome do jogador (a conta)."""
    painel(low, 16, 30, LW - 32, 82)
    ptext(low, fn["big"], "QUEM VAI JOGAR?", LW // 2, 44, (255, 230, 80))
    ptext(low, fn["sm"], f"Escreve o teu nome (máx. {bd.NOME_MAX}) e carrega ENTER", LW // 2, 58, (170, 210, 255))
    pygame.draw.rect(low, OUTLINE, (LW // 2 - 60, 66, 120, 16))
    pygame.draw.rect(low, (240, 240, 250), (LW // 2 - 59, 67, 118, 14))
    cursor = "_" if (tick // 30) % 2 else " "
    ptext(low, fn["mid"], texto + cursor, LW // 2, 74, OUTLINE, shadow=False)
    if erro:
        ptext(low, fn["sm"], erro, LW // 2, 92, (255, 120, 120))
    else:
        ptext(low, fn["sm"], "Nome que já existe = continuas essa conta", LW // 2, 92, (200, 200, 200))
    ptext(low, fn["sm"], "ESC  voltar", LW // 2, 102, WHITE)


def draw_historico(low, fn, nome, hist):
    """Ecrã com as últimas 10 partidas do jogador."""
    painel(low, 8, 3, LW - 16, 152, 215)
    ptext(low, fn["big"], "HISTÓRICO", LW // 2, 16, (255, 230, 80))
    ptext(low, fn["sm"], nome, LW // 2, 33, (160, 200, 255))
    if not hist:
        ptext(low, fn["mid"], "Ainda não jogaste nenhuma partida.", LW // 2, 70)
    cores = {"V": (120, 230, 120), "E": (255, 220, 100), "D": (255, 120, 120)}
    for i, h in enumerate(hist[:10]):
        y = 45 + i * 10
        modo = f"Comp N{h['nivel']}" if h["nivel"] else {"2 jogadores": "2 jog."}.get(h["modo"], h["modo"])
        data = f"{h['data'][8:10]}/{h['data'][5:7]}"
        ptext(low, fn["sm"], data, 16, y, (200, 200, 200), align="left")
        ptext(low, fn["sm"], modo, 46, y, WHITE, align="left")
        ptext(low, fn["sm"], h["adversario"][:13], 92, y, WHITE, align="left")
        ptext(low, fn["sm"], f"{h['golos_marcados']} - {h['golos_sofridos']}", 186, y, WHITE)
        ptext(low, fn["sm"], bd.TEXTO_RESULTADO[h["resultado"]], LW - 16, y, cores[h["resultado"]], align="right")
    ptext(low, fn["sm"], "ESC  voltar", LW // 2, 146, WHITE)


def draw_estatisticas(low, fn, nome, est, top):
    """Ecrã com as estatísticas do jogador e o top 5 de todos os jogadores."""
    painel(low, 8, 3, LW - 16, 154, 215)
    ptext(low, fn["big"], "ESTATÍSTICAS", LW // 2, 16, (255, 230, 80))
    ptext(low, fn["sm"], nome, 80, 33, (160, 200, 255))
    linhas = [("Pontos", est["pontos"]), ("Partidas", est["partidas"]),
              ("Vitórias", f"{est['vitorias']}  ({est['percentagem_vitorias']}%)"), ("Empates", est["empates"]),
              ("Derrotas", est["derrotas"]), ("Golos marcados", est["golos_marcados"]),
              ("Golos sofridos", est["golos_sofridos"]), ("Média de golos", est["media_golos"]),
              ("Vitórias seguidas", est["melhor_sequencia"]), ("Melhor nível comp.", est["melhor_nivel"] or "-")]
    for i, (k, v) in enumerate(linhas):
        y = 44 + i * 10
        ptext(low, fn["sm"], k, 18, y, (200, 200, 200), align="left")
        ptext(low, fn["sm"], str(v), 140, y, WHITE, align="right")
    pygame.draw.rect(low, (80, 90, 140), (150, 30, 1, 108))
    ptext(low, fn["sm"], "TOP 5 (pontos)", 210, 33, (255, 230, 80))
    for i, (n, pts, vit) in enumerate(top):
        y = 46 + i * 12
        cor = (160, 230, 160) if n.lower() == nome.lower() else WHITE
        ptext(low, fn["sm"], f"{i + 1}. {n}", 158, y, cor, align="left")
        ptext(low, fn["sm"], str(pts), LW - 18, y, cor, align="right")
    ptext(low, fn["sm"], "ESC  voltar", LW // 2, 148, WHITE)


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.SCALED)    # SCALED: o ecrã inteiro mantém as proporções
    pygame.display.set_caption("Head Ball - cabeças da webcam")
    clock = pygame.time.Clock()
    low = pygame.Surface((LW, LH))
    backgrounds = make_backgrounds()
    bg_i = load_stadium_index() % len(backgrounds)
    bg, anim = backgrounds[bg_i][1], backgrounds[bg_i][2]
    pads = Pads()
    f_cap = pygame.font.SysFont("arial", 22, bold=True)
    tamanhos = {"big": 34, "score": 26, "mid": 20, "sm": 15, "menu": 17}
    fn = {k: pygame.font.Font(None, t) for k, t in tamanhos.items()}
    TEXTO_HD["low"] = low                                       # texto nítido: a mesma letra, PX vezes maior
    TEXTO_HD["fontes"] = {id(fn[k]): pygame.font.Font(None, round(t * PX / TEXTO_PIXEL)) for k, t in tamanhos.items()}
    heads, ports = load_heads()

    try:                                                        # base de dados das contas
        conn = bd.ligar()
        conta = bd.ultimo_jogador(conn)
    except Exception as erro:                                   # sem base de dados o jogo funciona na mesma
        conn, conta = None, None
        print("Base de dados indisponível:", erro)

    state, mode, msg = ("menu" if conta or conn is None else "nome"), 1, ""
    nome_txt, nome_erro = "", ""
    hist, est, top = [], None, []
    resumo, nivel = None, 1                                     # resultado da última partida e nível competitivo
    pts = None                                                  # pontos do jogador (lidos da base de dados quando mudam)
    clima_modo = "aleatorio"                                    # clima das partidas (tecla T no menu)
    m = None
    tick = 0
    teclas_menu = {pygame.K_ESCAPE, pygame.K_c, pygame.K_v, pygame.K_b, pygame.K_TAB, pygame.K_x, pygame.K_F11,
                   pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_h, pygame.K_e, pygame.K_n, pygame.K_t}

    def nova_partida(modo, n=1):
        nome = conta[1] if conta else "Jogador 1"
        return Match(modo, heads, n, (nome, "Jogador 2"), clima_modo)

    while True:
        pads.update(tick)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:  # ecrã inteiro em qualquer ecrã
                msg = alternar_ecra_inteiro()
                continue
            if state == "nome" and e.type == pygame.KEYDOWN:     # escrever o nome
                if e.key == pygame.K_RETURN:
                    ok, res = bd.validar_nome(nome_txt)
                    if ok:
                        conta = bd.entrar(conn, res)
                        msg, nome_txt, nome_erro, state, pts = f"Olá, {conta[1]}!", "", "", "menu", None
                    else:
                        nome_erro = res
                elif e.key == pygame.K_BACKSPACE:
                    nome_txt, nome_erro = nome_txt[:-1], ""
                elif e.key == pygame.K_ESCAPE:
                    if conta:
                        state, nome_txt, nome_erro = "menu", "", ""
                    else:
                        nome_erro = "Escreve um nome para criar a tua conta."
                elif e.unicode and e.unicode.isprintable():
                    if len(nome_txt) < bd.NOME_MAX:
                        nome_txt += e.unicode
                    else:
                        nome_erro = f"Máximo {bd.NOME_MAX} caracteres."
                continue
            key = e.key if e.type == pygame.KEYDOWN else pads.event_key(e, state)
            if key is None:
                continue
            if state == "menu":
                if key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if key in (pygame.K_c, pygame.K_v):
                    slot = 0 if key == pygame.K_c else 1
                    msg = capture_head(screen, clock, f_cap, slot)
                    heads, ports = load_heads()
                if key == pygame.K_b:                                   # trocar de estádio
                    bg_i = (bg_i + 1) % len(backgrounds)
                    bg, anim = backgrounds[bg_i][1], backgrounds[bg_i][2]
                    save_stadium_index(bg_i)
                if key == pygame.K_TAB:
                    state = "controls"
                if key == pygame.K_t:                                   # trocar o clima
                    clima_modo = cl.MODOS[(cl.MODOS.index(clima_modo) + 1) % len(cl.MODOS)]
                if key == pygame.K_x:
                    for pth in HEAD_PATHS:
                        if os.path.exists(pth):
                            os.remove(pth)
                    heads, ports = load_heads()
                    msg = "Fotos apagadas."
                if key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    mode = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}[key]
                    nivel = 1
                    m = nova_partida(mode, nivel)
                    state, msg = "game", ""
                if key in (pygame.K_h, pygame.K_e, pygame.K_n) and conn is None:
                    msg = "Base de dados indisponível."
                elif key == pygame.K_n:
                    state, nome_txt, nome_erro = "nome", "", ""
                elif key == pygame.K_h and conta:
                    hist, state = bd.ler_historico(conn, conta[0]), "historico"
                elif key == pygame.K_e and conta:
                    est, top, state = bd.ler_estatisticas(conn, conta[0]), bd.ranking(conn), "estatisticas"
                if key not in teclas_menu and e.type == pygame.KEYDOWN and e.unicode.isprintable() and e.unicode:
                    msg = "Tecla inválida! Usa as teclas do menu."
            elif state == "controls":
                if key in (pygame.K_ESCAPE, pygame.K_TAB, pygame.K_RETURN):
                    state = "menu"
            elif state in ("historico", "estatisticas"):
                if key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    state = "menu"
            elif state == "over" and key in (pygame.K_RETURN, pygame.K_ESCAPE):
                if key == pygame.K_RETURN and m.mode == 3 and resumo and resumo["resultado"] == "V":
                    nivel += 1                                          # competitivo: próximo nível
                    m, state = nova_partida(3, nivel), "game"
                else:
                    state = "menu"
            elif state == "game" and key == pygame.K_ESCAPE:
                state = "menu"

        keys = pygame.key.get_pressed()
        heads_draw = []
        tick += 1

        if state == "game":
            m.step(*read_inputs(keys, pads.states(), m.mode))
            if m.over:
                state = "over"
                resumo = {"resultado": bd.calcular_resultado(*m.score), "pontos": None}
                if conn is not None and conta:                         # guarda a partida na conta do J1
                    try:
                        modo_txt = {1: "vs Bot", 2: "2 jogadores", 3: "Competitivo"}[m.mode]
                        resumo = bd.guardar_partida(conn, conta[0], modo_txt, m.nomes[1], m.score[0], m.score[1],
                                                    m.nivel if m.mode == 3 else None)
                        bd.exportar_txt(conn)
                        pts = None
                    except Exception as erro:
                        print("Não foi possível guardar a partida:", erro)

        if state in ("menu", "controls", "game", "over", "nome", "historico", "estatisticas"):
            low.blit(bg, (0, 0))
            if anim:
                run_anim(anim, low, tick)

        if state == "menu":
            painel(low, 30, 5, LW - 60, 116, 150)
            ptext(low, fn["big"], "HEAD BALL", LW // 2, 18, (255, 230, 80))
            if conta:
                if pts is None:
                    pts = bd.ler_estatisticas(conn, conta[0])["pontos"]
                ptext(low, fn["sm"], f"Jogador: {conta[1]}   ·   {pts} pontos", LW // 2, 35, (150, 230, 160))
            else:
                ptext(low, fn["sm"], "cabeças da webcam", LW // 2, 35, (160, 200, 255))
            nome_clima = "Aleatório" if clima_modo == "aleatorio" else cl.NOMES[clima_modo]
            items = ["1  vs Bot        2  2 jogadores", f"3  Competitivo     T  clima: {nome_clima}",
                     "H  histórico     E  estatísticas", f"N  mudar jogador   B  {backgrounds[bg_i][0]}",
                     "C / V  fotos     X  apagar fotos", "TAB controlos  F11 ecrã inteiro  ESC sair"]
            for i, t in enumerate(items):
                ptext(low, fn["menu"], t, LW // 2, 47 + i * 11)
            if msg:
                mm = msg if len(msg) <= 60 else msg[:59] + "…"
                ptext(low, fn["sm"], mm, LW // 2, 113, (255, 240, 120))
            gl = I(GROUND)
            for i, cx in enumerate((LW // 2 - 62, LW // 2 + 62)):
                heads_draw.append((heads[i], cx * PX, (gl - 14) * PX, False))
                ptext(low, fn["sm"], (conta[1] if conta else "J1") if i == 0 else "J2 / BOT", cx, gl + 9)
            if pads.short_status():
                ptext(low, fn["sm"], pads.short_status(), LW // 2, gl + 9, (150, 230, 160))

        elif state == "nome":
            draw_nome(low, fn, nome_txt, nome_erro, tick)

        elif state == "historico":
            draw_historico(low, fn, conta[1], hist)

        elif state == "estatisticas":
            draw_estatisticas(low, fn, conta[1], est, top)

        elif state == "controls":
            draw_controls(low, fn, pads)

        elif state in ("game", "over"):
            draw_clima_fundo(low, m, tick)
            draw_powerups(low, fn, m, tick)
            draw_player(low, m.p1)
            draw_player(low, m.p2)
            draw_ball(low, m.ball)
            update_draw_particles(low, m.parts)
            draw_clima_frente(low, m, tick)
            ptext(low, fn["sm"], "Clima: " + cl.NOMES[m.clima["atual"]], 6, 32, (200, 220, 255), align="left")
            heads_draw += [(pl.head, pl.x, pl.y, pl.facing == -1) for pl in (m.p1, m.p2)]

            cx = LW // 2
            pygame.draw.rect(low, OUTLINE, (cx - 35, 1, 70, 19))
            pygame.draw.rect(low, (30, 36, 80), (cx - 34, 2, 68, 17))
            ptext(low, fn["score"], f"{m.score[0]} - {m.score[1]}", cx, 11, (255, 230, 80))
            pygame.draw.rect(low, OUTLINE, (cx - 11, 21, 22, 10))
            pygame.draw.rect(low, (30, 36, 80), (cx - 10, 22, 20, 8))
            ptext(low, fn["sm"], f"{max(0, int(m.time_left))}", cx, 26, WHITE, shadow=False)
            heads_draw += [(ports[0], (cx - 62) * PX, 14 * PX, False),
                           (ports[1], (cx + 62) * PX, 14 * PX, False)]
            ptext(low, fn["sm"], m.nomes[0][:12], cx - 76, 14, (130, 180, 255), align="right")
            ptext(low, fn["sm"], m.nomes[1][:12] if m.mode == 2 else "BOT", cx + 76, 14, (255, 130, 130), align="left")
            if m.mode == 3:
                ptext(low, fn["sm"], f"COMPETITIVO  ·  NÍVEL {m.nivel} ({m.bot['nome']})", cx, 37, (255, 200, 120))
            if m.banner:
                bounce = int(math.sin(m.pause * 0.3) * 2)
                ptext(low, fn["big"], "GOLO!", cx, 62 + bounce, (255, 230, 80))
                ptext(low, fn["mid"], m.banner, cx, 78, WHITE)
            if m.jumpball > 0 and state == "game":
                ptext(low, fn["mid"], "BOLA AO AR!", cx, 66, (255, 230, 80))
                ptext(low, fn["big"], str((m.jumpball + 59) // 60), cx, 83, WHITE)
            if state == "over":
                pygame.draw.rect(low, OUTLINE, (cx - 110, 44, 220, 64))
                pygame.draw.rect(low, (30, 36, 80), (cx - 109, 45, 218, 62))
                r = resumo["resultado"] if resumo else bd.calcular_resultado(*m.score)
                if m.mode == 2:
                    res = "EMPATE!" if r == "E" else f"VENCEU {m.nomes[0 if r == 'V' else 1].upper()}!"
                else:
                    res = {"V": "GANHASTE!", "E": "EMPATE!", "D": "PERDESTE!"}[r]
                ptext(low, fn["big"], res, cx, 57, (255, 230, 80))
                if resumo and resumo.get("pontos") is not None:
                    ptext(low, fn["mid"], f"+{resumo['pontos']} pontos para {m.nomes[0]}", cx, 74, (150, 230, 160))
                if m.mode == 3 and r == "V":
                    ptext(low, fn["sm"], f"Nível {m.nivel} superado!", cx, 87)
                    ptext(low, fn["sm"], f"ENTER = nível {m.nivel + 1}    ESC = menu", cx, 98)
                elif m.mode == 3:
                    ptext(low, fn["sm"], f"Fim da corrida: chegaste ao nível {m.nivel}", cx, 87)
                    ptext(low, fn["sm"], "ENTER = menu", cx, 98)
                else:
                    ptext(low, fn["mid"], "ENTER para voltar ao menu", cx, 92)

        shake = m.shake if (m is not None and state == "game") else 0.0
        ox = oy = 0
        if shake > 0.5:
            ox, oy = random.randint(-int(shake), int(shake)), random.randint(-int(shake), int(shake))
        screen.fill((0, 0, 0))
        screen.blit(pygame.transform.scale(low, (W, H)), (ox, oy))
        for spr, hx, hy, flip in heads_draw:
            draw_head(screen, spr, hx + ox, hy + oy, flip)
        desenhar_textos(screen, ox, oy)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
