# Mapa de funções · Head Ball Webcam

Ficheiros: `headball_webcam.py`, `base_dados.py`, `powerups.py`, `testes/test_jogo.py` · 152 funções e métodos (incluindo as funções internas, definidas dentro de outras) · Sprint 1, FP 2026/27

Coluna *Recebe*: `self` não aparece nos métodos. "—" quer dizer que não recebe nada ou não devolve nada.

## Utilitários e webcam (fotos dos jogadores) · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `I(v)` | v: coordenada real (float) | int | Converte uma coordenada do jogo para a grelha de baixa resolução (divide por PX e arredonda). |
| `crop_box(frame, face)` | frame: imagem da câmara; face: (x, y, w, h) ou None | (cx, cy, tamanho) | Calcula o quadrado de recorte à volta da cara ou, se não houver cara, do centro da imagem. |
| `make_head_png(frame, face)` | frame: imagem; face: retângulo da cara ou None | imagem 256×256 com transparência | Recorta a cabeça e aplica-lhe uma máscara circular transparente. |
| `load_cascade()` | — | detetor de caras ou None | Carrega o detetor de caras do OpenCV; devolve None se a instalação não o tiver. |
| `save_png(path, img)` | path: caminho; img: imagem | None (lança RuntimeError se falhar) | Guarda a imagem em PNG, mesmo que o caminho tenha acentos. |
| `import_head_from_file(slot, cascade)` | slot: 0 ou 1; cascade: detetor ou None | mensagem (str) | Abre um seletor de ficheiros, deteta a cara na foto escolhida e guarda-a como cabeça do jogador. |
| `probe_camera(index, backend)` | index: nº da câmara; backend: tipo de acesso | câmara aberta ou None | Abre a câmara e confirma que ela devolve mesmo uma imagem. |
| `find_cameras()` | — | lista de dicionários {index, backend, name} | Procura as câmaras disponíveis no computador. |
| `open_from(start, cams)` | start: posição inicial; cams: lista de câmaras | (câmara ou None, posição, nomes saltados) | Abre a primeira câmara que funcione a partir da posição indicada. |
| `save_cam_index()` | — | None | Guarda o número da câmara escolhida em heads/camera.txt (ignora erros de escrita). |
| `capture_head(screen, clock, font, slot)` | ecrã, relógio, letra, slot do jogador | mensagem (str) | Chama _capture_head dentro de try/except para que um erro da webcam nunca feche o jogo. |
| `_capture_head(screen, clock, font, slot)` | ecrã, relógio, letra, slot do jogador | mensagem (str) | Mostra a webcam: TAB troca de câmara, ESPAÇO tira a foto, F importa um ficheiro, ESC cancela. |
| `pixelate_head(img, size)` | img: imagem do pygame; size: lado em píxeis | Surface (sprite) | Transforma a foto num sprite pixel art com paleta reduzida e borda nítida. |
| `default_head(slot, size)` | slot: 0 ou 1; size: lado em píxeis | Surface | Desenha uma cara por defeito (cabelo, olhos e boca) para quando não há foto. |
| `load_head(slot, size)` | slot: 0 ou 1; size: lado em píxeis | Surface | Carrega a foto do jogador se existir e for válida; senão usa a cara por defeito. |
| `load_heads()` | — | (cabeças do jogo, retratos do menu) | Carrega as duas cabeças em dois tamanhos: um para o jogo e outro para o menu. |

## Física: classe Ball (bola) · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `Ball.__init__(self)` | — | — | Cria a bola e põe-na na posição inicial. |
| `Ball.reset(self)` | — | None | Põe a bola no centro, no ar, com um pequeno empurrão aleatório para um dos lados. |
| `Ball.forces(self)` | — | None | Aplica a gravidade, faz a bola rodar e limita a velocidade máxima a 24. |
| `Ball.move(self, f)` | f: fração do frame (0 a 1) | None | Move a bola e trata os ressaltos no chão (perde 28%), no teto, nas paredes e nas barras das balizas. |
| `Ball.update(self)` | — | None | Faz um passo completo da bola (forces + move). |
| `Ball.clamp(self)` | — | None | Garante que a bola nunca sai dos limites do campo. |
| `Ball.collide_rect(self, rect, side)` | rect: retângulo; side: lado do campo (−1, 0, 1) | None | Faz a bola ressaltar num retângulo (barra da baliza) e, se ficar parada em cima, empurra-a para o campo. |
| `Ball.collide_circle(self, cx, cy, r, cvx, cvy, e)` | centro, raio e velocidade do círculo; e: elasticidade | bool | Resolve a colisão com um círculo em movimento; devolve True se houve contacto. |

## Física: classes Leg e Player (jogadores) · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `Leg.__init__(self)` | — | — | Cria uma perna com coxa e canela paradas. |
| `Leg.step(self, a_target, r_target, k, damp)` | ângulos-alvo da coxa e do joelho; k: força da mola; damp: amortecimento | None | Move a coxa como uma mola e a canela com atraso (efeito chicote), com limites no joelho. |
| `Player.__init__(self, slot, x, facing, head)` | slot, posição x inicial, lado para onde olha, sprite da cabeça | — | Cria o jogador e põe-no na posição inicial. |
| `Player.reset(self)` | — | None | Repõe posição, velocidade, pernas, remate e power-ups do jogador (usado depois de cada golo). |
| `Player.hip (propriedade)` | — | (x, y) | Devolve a posição da anca, de onde saem as pernas. |
| `Player.leg_points(self, leg)` | leg: perna | (anca, joelho, pé) | Calcula os três pontos da perna a partir dos ângulos. |
| `Player.leg_circles(self)` | — | lista de (chave, centro, raio) | Devolve os círculos de colisão ao longo das duas pernas. |
| `Player.track(self)` | — | None | Guarda a velocidade de cada parte da perna para que um remate com a perna em movimento seja mais forte. |
| `Player.update_legs(self, ax)` | ax: aceleração horizontal | None | Escolhe a pose das pernas (parado, a andar, no ar ou a rematar) e anima-as. |
| `Player.update(self, left, right, jump, kick, speed, face)` | 4 botões (bool), velocidade, lado forçado (opcional) | None | Aplica os comandos e os power-ups (gelo, velocidade, salto): move, salta, remata, aplica a gravidade e atualiza as pernas. |
| `Player.clamp_x(self)` | — | None | Mantém o jogador dentro dos limites horizontais do campo. |
| `Player.colliders(self)` | — | lista de formas de colisão | Devolve as formas sólidas do jogador (cabeça, tronco, pernas e botas), iguais ao que está desenhado. |
| `Player.on_impact(self, key, ball, cvel)` | parte do corpo, bola, velocidade da parte | None | Se a perna que remata bate na bola durante o remate, chuta e levanta a bola (mais forte com o super chuto). |

## Lógica do jogo · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `resolve_ball(ball, players)` | ball: bola; players: os dois jogadores | ({jogador: tocou}, força do impacto) | Resolve as colisões da bola com os jogadores, tratando primeiro o contacto mais fundo. |
| `nivel_bot(n)` | n: nível do modo competitivo (1, 2, 3…) | dicionário {nome, velocidade, chuto, salto} | Devolve a dificuldade do bot nesse nível; depois do nível 5 o bot continua a ficar mais rápido, até um limite. |
| `bot_controls(bot, ball, chuto, salto)` | bot, bola, probabilidade de chutar e de saltar | (esquerda, direita, saltar, chutar) | Decide os comandos do bot: posiciona-se atrás da bola, salta e remata com uma probabilidade que depende do nível. |
| `read_inputs(keys, pad_states, mode)` | teclas premidas, estados dos comandos, modo (1 ou 2) | (comandos J1, comandos J2) | Junta teclado e comandos e decide que comando controla cada jogador. |
| `read_inputs.merge(a, b) (interna)` | dois tuplos de 4 bool | tuplo de 4 bool | Combina dois conjuntos de botões (basta um estar premido). |
| `Match.__init__(self, mode, heads, nivel, nomes)` | mode: 1 = vs bot, 2 = 2 jogadores, 3 = competitivo; sprites; nível; nomes | — | Cria uma partida: jogadores, bola, resultado [0, 0], bot do nível, tempo (60 s, ou 45 s no competitivo) e power-ups. |
| `Match.goal(self, scorer)` | scorer: 0 ou 1 | None | Soma o golo, mostra a faixa com o nome de quem marcou, faz tremer o ecrã e lança confettis. |
| `Match.step(self, in1, in2)` | comandos do J1 e do J2 | None | Avança um frame: tempo, jogadores, bot, power-ups, bola, golos, "bola ao ar" e fim da partida. |

## Comandos (PS5, PS4, Xbox…): classe Pads · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `Pads.__init__(self)` | — | — | Inicia o suporte a comandos (GameController do SDL, ou joystick genérico se não houver). |
| `Pads.rescan(self)` | — | None | Volta a procurar os comandos ligados e abre cada um. |
| `Pads.update(self, tick)` | tick: nº do frame | None | Uma vez por segundo verifica se algum comando foi ligado ou desligado. |
| `Pads.names(self)` | — | lista de str | Devolve os nomes dos comandos ligados. |
| `Pads.short_status(self)` | — | str | Devolve um texto curto como "Comando ligado" (vazio se não houver nenhum). |
| `Pads.state_ctl(c)` | c: comando GameController | (esq, dir, saltar, chutar) | Lê o analógico e os botões de um comando reconhecido. |
| `Pads.state_joy(j)` | j: joystick genérico | (esq, dir, saltar, chutar) | Lê eixos, setas e botões de um joystick genérico. |
| `Pads.states(self)` | — | lista de tuplos de 4 bool | Devolve o estado de todos os comandos; um comando com erro conta como "nada premido". |
| `Pads.event_key(self, e, state)` | e: evento; state: ecrã atual | tecla do pygame ou None | Traduz um botão do comando na tecla equivalente do menu, do jogo, do histórico ou das estatísticas. |

## Estádios e persistência · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `make_backgrounds()` | — | lista de (nome, fundo, animação ou None) | Cria os 5 estádios: Clássico, Lisboa, Piaget, Almada e Noite. |
| `load_stadium_index()` | — | int | Lê o estádio guardado em heads/estadio.txt; se faltar ou for inválido, devolve 0. |
| `save_stadium_index(i)` | i: índice do estádio | None | Guarda o estádio escolhido em heads/estadio.txt (ignora erros de escrita). |
| `make_background()` | — | Surface | Desenha o estádio Clássico (céu, público e painéis) e o relvado. |
| `canvas_background(canvas)` | canvas: tela de pixel art | Surface | Converte uma tela num fundo do tamanho certo e acrescenta o relvado. |
| `make_night_background(classic)` | classic: fundo Clássico | Surface | Cria o estádio Noite: escurece o Clássico e acrescenta holofotes. |
| `draw_pitch(bg)` | bg: fundo | o mesmo fundo | Desenha o relvado, as linhas e as balizas (iguais em todos os estádios). |
| `run_anim(anim, low, t)` | anim: função de animação; low: ecrã; t: frame | None | Desenha as animações do cenário (navios, metro, gaivotas…) e volta a desenhar o relvado e as balizas por cima delas. |

## Cenários em pixel art: classes Canvas e Pen · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `Canvas.__init__(self, w, h, fill)` | largura, altura, cor de fundo | — | Cria uma tela de píxeis em memória, sem pygame. |
| `Canvas.px(self, x, y, c)` | posição e cor | None | Pinta um píxel (se estiver dentro da área de recorte). |
| `Canvas.get(self, x, y)` | posição | cor (r, g, b) | Lê a cor de um píxel. |
| `Canvas.rect(self, x, y, w, h, c)` | posição, tamanho e cor | None | Pinta um retângulo cheio. |
| `Canvas.line(self, x0, y0, x1, y1, c)` | dois pontos e cor | None | Desenha uma linha píxel a píxel (algoritmo de Bresenham). |
| `Canvas.to_surface(self)` | — | Surface | Converte a tela numa imagem do pygame. |
| `Pen.__init__(self, surf, clip)` | surf: imagem; clip: área de recorte | — | Prepara o desenho direto numa imagem do pygame, com recorte. |
| `Pen.rect(self, x, y, w, h, c)` | posição, tamanho e cor | None | Pinta um retângulo. |
| `Pen.px(self, x, y, c)` | posição e cor | None | Pinta um píxel se estiver dentro do ecrã. |
| `Pen.line(self, x0, y0, x1, y1, c)` | dois pontos e cor | None | Desenha uma linha. |
| `Pen.release(self)` | — | None | Retira a área de recorte. |

## Cenários: Lisboa, Piaget e Almada · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `_ridge(x)` | x: coluna | int (altura) | Calcula a altura da linha das colinas da margem sul em cada coluna. |
| `_cloud(cv, cx, cy, w)` | tela, centro, largura | None | Desenha uma nuvem. |
| `_cristo_rei(cv, cx, by)` | tela, centro, base | None | Desenha o Cristo Rei. |
| `_ponte(cv, tx)` | tela, posição da torre | None | Desenha a Ponte 25 de Abril. |
| `make_lisboa_canvas()` | — | Canvas | Desenha o estádio Lisboa (céu, rio, margem sul e bancadas). |
| `disc(cv, cx, cy, r, c)` | tela, centro, raio, cor | None | Desenha um círculo cheio. |
| `draw_text(cv, x, y, s, c, scale, gap)` | tela, posição, texto, cor, escala, espaço | int (x final) | Escreve texto com uma letra pixel art de 3×5. |
| `text_width(s, scale, gap)` | texto, escala, espaço | int | Calcula a largura que um texto vai ocupar. |
| `_stands(cv, rnd, boards)` | tela, gerador aleatório, painéis | Canvas | Desenha bancadas, cobertura, pilares e painéis comuns aos estádios com paisagem. |
| `make_piaget_canvas()` | — | Canvas | Desenha o estádio Piaget. |
| `_fluffy(cv, cx, cy, s)` | tela, centro, tamanho | None | Desenha uma nuvem grande e fofa. |
| `_canhao(cv, x, yb)` | tela, posição, base | None | Desenha um canhão. |
| `_fragata(cv)` | tela | None | Desenha a fragata (navio à vela) do cenário de Almada. |
| `_fragata.ladder(a0, a1, b0, b1) (interna)` | extremos de duas linhas | None | Desenha os degraus de uma enxárcia (cordas) da fragata. |
| `make_almada_canvas()` | — | Canvas | Desenha o estádio Almada. |
| `_mirror(d, x, length, flip)` | superfície, posição, comprimento, virar | função r | Cria uma função de desenho que pode espelhar a figura (navios para os dois lados). |
| `_mirror.r(u, v, w, h, c, y) (interna)` | retângulo relativo, cor, linha de água | None | Desenha um retângulo, espelhado se for preciso. |
| `_ship_cargo(d, x, y, flip)` | superfície, posição, virar | None | Desenha um porta-contentores. |
| `_ship_tanker(d, x, y, flip)` | superfície, posição, virar | None | Desenha um petroleiro. |
| `_ship_ferry(d, x, y, flip)` | superfície, posição, virar | None | Desenha um cacilheiro. |
| `_gull(d, x, y, flap)` | superfície, posição, asa em cima/baixo | None | Desenha uma gaivota. |
| `_draw_gulls(d, t, spec)` | superfície, frame, lista de gaivotas | None | Move e desenha um bando de gaivotas. |
| `ph_int(ph)` | ph: fase (float) | int | Converte a fase de uma gaivota num inteiro para alternar o bater das asas. |
| `make_lisboa_anim()` | — | função anim | Prepara a animação de Lisboa (brilhos no rio, navios, carros na ponte e gaivotas). |
| `make_lisboa_anim.anim(d, t) (interna)` | superfície, frame | None | Desenha um frame da animação de Lisboa. |
| `_tram(d, x, y)` | superfície, posição | None | Desenha o metro de superfície ("1 Cacilhas"). |
| `_tram.row(u0, u1, dy, c, first) (interna)` | início, fim, linha, cor, 1.ª carruagem | None | Desenha uma linha horizontal de uma carruagem (com o nariz arredondado). |
| `make_almada_anim()` | — | função anim | Prepara a animação de Almada (metro e gaivotas). |
| `make_almada_anim.anim(d, t) (interna)` | superfície, frame | None | Desenha um frame da animação de Almada. |
| `make_piaget_anim()` | — | função anim | Prepara a animação do Piaget (pessoas a andar e gaivotas). |
| `make_piaget_anim.anim(d, t) (interna)` | superfície, frame | None | Desenha um frame da animação do Piaget. |

## Desenho no ecrã · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `ptext(surf, font, msg, x, y, color, align, shadow)` | ecrã, letra, texto, posição, cor, alinhamento, sombra | None | Escreve texto alinhado, com sombra; no ecrã principal guarda-o para ser desenhado nítido à resolução real. |
| `desenhar_textos(screen, ox, oy)` | janela, deslocamento do tremor do ecrã | None | Desenha à resolução real todo o texto guardado neste frame (letras nítidas) e esvazia a lista. |
| `alternar_ecra_inteiro()` | — | mensagem (str) | Liga ou desliga o ecrã inteiro (F11) e diz se não for suportado. |
| `draw_head(screen, sprite, cx, cy, flip)` | ecrã, sprite, centro, virar | None | Desenha a cabeça do jogador com contorno, virada para o lado certo. |
| `draw_leg(low, p, leg, team)` | ecrã, jogador, perna, cores da equipa | None | Desenha a perna (coxa, meia e bota). |
| `draw_arm(low, p, leg, team)` | ecrã, jogador, perna, cores da equipa | None | Desenha o braço, que balança ao contrário da perna. |
| `draw_player(low, p)` | ecrã, jogador | None | Desenha a sombra, o corpo, as pernas e os braços do jogador. |
| `draw_ball(low, b)` | ecrã, bola | None | Desenha a bola a rodar e a sua sombra. |
| `spawn(parts, x, y, n, colors, spread, up, life, size, grav)` | lista de partículas, posição, quantidade, cores, … | None | Acrescenta partículas (confettis, relva, faíscas) à lista. |
| `update_draw_particles(low, parts)` | ecrã, lista de partículas | None | Move, desenha e apaga as partículas que já acabaram. |
| `draw_controls(low, fn, pads)` | ecrã, letras, comandos | None | Desenha o ecrã de controlos do menu (teclado, comando e F11). |
| `draw_controls.block(x, y, title, color, lines, off) (interna)` | posição, título, cor, linhas, espaço | None | Desenha um bloco de controlos (título + tecla → ação). |

## Ecrãs novos: contas, power-ups, histórico e estatísticas · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `painel(low, x, y, w, h, alpha)` | ecrã, posição, tamanho, transparência | None | Desenha um retângulo escuro semitransparente por trás do texto. |
| `draw_powerups(low, fn, m, tick)` | ecrã, letras, partida, frame | None | Desenha os power-ups no campo, o gelo nos jogadores congelados, as barras dos efeitos ativos e o aviso de quem apanhou. |
| `draw_nome(low, fn, texto, erro, tick)` | ecrã, letras, texto escrito, mensagem de erro, frame | None | Desenha o ecrã onde o jogador escreve o nome da conta. |
| `draw_historico(low, fn, nome, hist)` | ecrã, letras, nome, lista de partidas | None | Desenha as últimas 10 partidas com data, modo, adversário, marcador e GANHOU/EMPATE/PERDEU. |
| `draw_estatisticas(low, fn, nome, est, top)` | ecrã, letras, nome, estatísticas, top 5 | None | Desenha as estatísticas do jogador e o top 5 de pontos. |

## Programa principal · `headball_webcam.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `main()` | — | None | Abre a janela (redimensionável para ecrã inteiro), liga a base de dados e corre o ciclo do jogo com 7 ecrãs (nome, menu, controlos, jogo, fim, histórico, estatísticas) a 60 frames por segundo. |
| `main.nova_partida(modo, n) (interna)` | modo (1, 2 ou 3), nível | Match | Cria uma partida com o nome do jogador que está na conta. |

## Base de dados (contas, histórico, estatísticas) · `base_dados.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `ligar(caminho)` | caminho do ficheiro (por defeito dados/headball.db) | ligação SQLite | Abre ou cria a base de dados e garante que as tabelas existem. |
| `criar_tabelas(conn)` | ligação | None | Cria as tabelas jogadores e partidas, com regras que impedem valores inválidos. |
| `validar_nome(nome)` | nome escrito pelo jogador | (True, nome limpo) ou (False, mensagem) | Valida o nome: não vazio, máximo 12 caracteres, só letras, números, espaço, - e _. |
| `_agora()` | — | str | Devolve a data e hora atuais no formato AAAA-MM-DD HH:MM. |
| `entrar(conn, nome)` | ligação, nome | (id, nome) | Entra na conta com esse nome, criando-a se ainda não existir (maiúsculas não contam). |
| `ultimo_jogador(conn)` | ligação | (id, nome) ou None | Devolve o último jogador que entrou, para o jogo abrir já com essa conta. |
| `calcular_resultado(golos_marcados, golos_sofridos)` | dois inteiros | "V", "E" ou "D" | Decide se foi vitória, empate ou derrota. |
| `guardar_partida(conn, jogador_id, modo, adversario, golos_marcados, golos_sofridos, nivel)` | ligação, conta, dados da partida | {resultado, texto, pontos} | Guarda a partida e calcula os pontos (3/1/0, mais o nível no competitivo). |
| `ler_historico(conn, jogador_id, limite)` | ligação, conta, nº de partidas | lista de dicionários | Devolve as últimas partidas do jogador, a mais recente primeiro. |
| `melhor_sequencia(resultados)` | lista de "V"/"E"/"D" | int | Conta o maior número de vitórias seguidas. |
| `ler_estatisticas(conn, jogador_id)` | ligação, conta | dicionário | Calcula partidas, vitórias, empates, derrotas, golos, pontos, % de vitórias, média de golos, melhor sequência e melhor nível. |
| `ranking(conn, limite)` | ligação, nº de jogadores | lista de (nome, pontos, vitórias) | Devolve o top de jogadores por pontos. |
| `exportar_txt(conn, caminho)` | ligação, caminho (por defeito dados/resultados.txt) | bool | Escreve todas as partidas num ficheiro de texto, uma por linha; devolve False se não conseguir escrever. |

## Power-ups · `powerups.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `PowerUp.__init__(self, tipo, x, y)` | tipo, posição | — | Cria um power-up no campo com 8 segundos de vida. |
| `novo_powerup(xmin, xmax, y_chao, rnd)` | limites do campo, altura, gerador aleatório | PowerUp | Cria um power-up aleatório num sítio que se apanha a andar ou a saltar. |
| `atualizar_efeitos(efeitos)` | dicionário {efeito: frames} | dicionário | Desconta um frame a cada efeito e tira os que acabaram. |
| `aplicar(tipo, jogador, adversario)` | tipo, quem apanhou, adversário | texto (str) | Dá o efeito a quem apanhou (ou ao adversário, no caso do gelo). |
| `apanhou(pu, jogador)` | power-up, jogador | bool | Verifica se a cabeça ou o corpo do jogador toca no power-up. |
| `passo_powerups(estado, jogadores, xmin, xmax, y_chao, rnd)` | estado dos power-ups, jogadores, limites | (jogador, texto) ou None | Avança um frame: faz aparecer, envelhecer e apanhar power-ups. |

## Casos de teste (R4) · `testes/test_jogo.py`

| Função | Recebe | Devolve | O que faz |
|---|---|---|---|
| `JogadorFalso.__init__(self, x, y)` | posição | — | Jogador simplificado só para testar os power-ups. |
| `TestNomes.test_1_validacao_do_nome(self)` | — | — | Nomes válidos, vazios, compridos, com símbolos e com tentativa de injeção de SQL. |
| `TestBaseDados.setUp(self)` | — | — | Cria uma base de dados temporária em memória antes de cada teste. |
| `TestBaseDados.tearDown(self)` | — | — | Fecha a base de dados temporária depois de cada teste. |
| `TestBaseDados.test_2_conta_criada_e_reutilizada(self)` | — | — | O mesmo nome (com outras maiúsculas) entra na mesma conta. |
| `TestBaseDados.test_3_resultado_e_pontos(self)` | — | — | Vitória, empate, derrota e bónus do nível competitivo dão os pontos certos. |
| `TestBaseDados.test_4_historico_e_estatisticas(self)` | — | — | Estatísticas, melhor sequência, ordem do histórico e ranking estão certos. |
| `TestPowerUps.test_5_efeitos_e_apanhar(self)` | — | — | O gelo vai para o adversário, os efeitos expiram e apanhar um power-up funciona. |
| `TestPowerUps.test_6_powerup_aparece_e_desaparece(self)` | — | — | Um power-up aparece e desaparece se ninguém o apanhar. |
| `TestNiveis.test_7_bot_fica_mais_dificil(self)` | — | — | O bot nunca fica mais fácil de nível para nível e tem um limite de velocidade. |
