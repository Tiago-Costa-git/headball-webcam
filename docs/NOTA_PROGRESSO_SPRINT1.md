# Nota de progresso · Sprint 1

**Projeto:** Head Ball Webcam · **UC:** Fundamentos de Programação · CTeSP em Cibersegurança, Instituto Piaget Almada

**Equipa:** Tiago Costa, André Filipe, Guilherme Lopes · **Entrega:** 24/11/2026

**Código entregue:** `headball_webcam.py` (1991 linhas, Python 3 + pygame-ce, numpy, opencv-python) · **Repositório:** [link do GitHub a preencher]

## 1. Resumo

O jogo já é jogável do princípio ao fim: menu, partida de 60 segundos contra o computador ou entre dois jogadores, golos, fim de jogo e regresso ao menu. As cabeças dos jogadores podem ser fotografadas com a webcam ou importadas de um ficheiro, há 5 estádios à escolha e o jogo funciona com teclado ou com comandos (PS5, PS4, Xbox). O professor aceitou que o jogo seja gráfico (pygame) em vez de modo de texto.

Os requisitos R1 (menu com validação) e R2 (funções) estão cumpridos em grande parte, mas não totalmente: o menu ignora as teclas inválidas sem mostrar nenhuma mensagem, e o código ainda está todo num único ficheiro. O R3 (lista de resultados guardada num ficheiro) ainda não foi começado e é o objetivo do Sprint 2.

## 2. R1: menu com validação de entrada

**Onde está:** na função `main()`, no bloco `if state == "menu":` (linhas 1874 a 1897). O jogo tem 4 estados (`menu`, `controls`, `game`, `over`) e cada um só aceita as teclas que lhe pertencem.

| Tecla no menu | Comando | O que faz |
|---|---|---|
| 1 | CRUZ | Começa um jogo de 1 jogador contra o bot |
| 2 | TRIÂNGULO | Começa um jogo de 2 jogadores |
| B | QUADRADO | Troca de estádio e guarda a escolha |
| C / V | — | Tira a foto do Jogador 1 / Jogador 2 com a webcam |
| X | — | Apaga as fotos guardadas |
| TAB | OPTIONS | Abre o ecrã de controlos |
| ESC | — | Sai do jogo |

**Entradas inválidas que o jogo já trata (testadas):**

- **Tecla sem função no menu** (por exemplo Q, 9 ou P): é ignorada e o menu continua ativo. O jogo não fecha nem muda de estado.
- **Ficheiro `heads/estadio.txt` com texto em vez de número** (por exemplo `abc`): `load_stadium_index()` apanha o erro com `try/except` e usa o estádio 0 (Clássico).
- **Número de estádio fora do intervalo** (por exemplo `99`): em `main()` o valor passa por `% len(backgrounds)` (linha 1853), por isso fica sempre entre 0 e 4.
- **Ficheiro em falta:** o estádio fica o 0 e a câmara fica a 0.
- **OpenCV não instalado:** `capture_head()` devolve a mensagem "Falta instalar: pip install opencv-python numpy" em vez de fechar o jogo.
- **Erro da webcam** (câmara ocupada ou desligada): `capture_head()` apanha qualquer exceção e mostra a mensagem de erro no menu.
- **Foto inválida ao importar** (ficheiro que não é imagem): aparece "Não consegui ler essa imagem." e o jogo continua.
- **Comando com erro ou desligado a meio:** `Pads.states()` trata-o como "nada premido" e o jogo procura comandos novos a cada segundo.

**O que falta no R1 (honestamente):** quando se carrega numa tecla inválida no menu não aparece nenhuma mensagem. Se o professor exigir feedback visível, basta acrescentar no fim do bloco do menu um `else` que mostra "Tecla inválida: usa 1, 2, B, C, V, X, TAB ou ESC" (a variável `msg` já existe e já é mostrada no menu). Está planeado para o início do Sprint 2.

## 3. R2: funções e organização do código

O código tem **114 funções e métodos**, organizados em 7 classes (`Ball`, `Leg`, `Player`, `Canvas`, `Pen`, `Pads`, `Match`) e funções soltas por tema: webcam, física, lógica do jogo, estádios, cenários, desenho e programa principal. Todas estão descritas no **Mapa de funções** entregue em conjunto.

As funções mais importantes para o funcionamento do jogo são:

- `Match.step(in1, in2)`: avança a partida um frame (tempo, jogadores, bola, golos e fim).
- `resolve_ball(ball, players)`: colisões entre a bola e os jogadores.
- `bot_controls(bot, ball)`: inteligência do computador no modo 1 jogador.
- `read_inputs(keys, pad_states, mode)`: junta teclado e comandos.
- `capture_head(...)` e `import_head_from_file(...)`: fotos dos jogadores.
- `load_stadium_index()` e `save_stadium_index(i)`: guardar e ler o estádio escolhido.

A classe `Match` não desenha nada, só tem a lógica. Isso permitiu testar partidas completas sem janela (modo *headless*): uma partida de 1 jogador e outra de 2 jogadores chegaram ao fim sem erros.

**O que falta no R2:** o código ainda está todo num único ficheiro de 1991 linhas. A história 3 do backlog (separar em módulos, por exemplo `fisica.py`, `cenarios.py`, `webcam.py`, `comandos.py` e `main.py`) passou para o Sprint 2.

## 4. O que funciona e o que falta

**Funciona:**

- Partida completa de 60 s: 1 jogador contra o bot ou 2 jogadores no mesmo teclado.
- Física com pernas articuladas (coxa e canela), remate, salto e colisões que não deixam a bola atravessar os jogadores.
- Regra "bola ao ar": se a bola ficar presa entre os dois jogadores durante 3 s, há uma contagem 3-2-1 e a bola é lançada ao ar.
- Fotos das cabeças pela webcam (com deteção de cara e troca de câmara) ou a partir de um ficheiro.
- 5 estádios (Clássico, Lisboa, Piaget, Almada, Noite), três deles com animações (navios, metro de superfície, gaivotas). O estádio escolhido fica guardado.
- Suporte para comandos PS5, PS4 e Xbox, por cabo ou Bluetooth, com deteção automática.
- Ecrã de controlos e ecrã de fim de jogo.

**Falta:**

- **R3 (objetivo do Sprint 2):** não há nenhuma lista de resultados nem nenhum ficheiro de pontuações. Os resultados perdem-se quando o jogo fecha.
- **R4:** ainda não há casos de teste escritos nem README final (o README do repositório é um primeiro rascunho).
- Mensagem visível para teclas inválidas no menu (ver secção 2).
- Separar o código em módulos (ver secção 3).
- O tempo da partida é contado por frames (`time_left -= 1/60`). Num computador lento o jogo fica abaixo de 60 frames por segundo e a partida demora mais do que 60 segundos reais.
- Privacidade das fotos: o jogo não pede consentimento antes de tirar a foto e as fotos só são apagadas quando se carrega em X. Numa exposição pública isto é importante.
- Pormenor de limpeza: em `make_lisboa_anim()` a lista `sparkles` é calculada duas vezes e a primeira linha não serve para nada.

**Plano para o R3 no Sprint 2:**

1. No fim de cada partida, criar um resultado com a data, o modo, o nome dos jogadores e o marcador, e acrescentá-lo a uma **lista** `resultados`.
2. Guardar em `resultados.txt`, uma linha por partida, por exemplo `2026-12-01 14:30;1 jogador;Tiago;Bot;6;5`.
3. Criar as funções `guardar_resultado(ficheiro, resultado)`, `ler_resultados(ficheiro) -> lista` e `top5(resultados) -> lista`.
4. Em `ler_resultados`, ignorar as linhas estragadas com `try/except`, em vez de o jogo falhar.
5. Acrescentar ao menu uma opção "P = Pontuações" que mostra o top 5.
6. Opcional, e reforça o R1: pedir o nome do jogador com validação (máximo 12 caracteres, só letras e números; se ficar vazio usa "Jogador 1"), mostrando "Nome inválido" quando for preciso.

## 5. Product Backlog atualizado

| # | História | Requisito | Estado | Observações |
|---|---|---|---|---|
| 1 | Como jogador, quero um menu que só aceite opções válidas, para não estragar o jogo sem querer. | R1 | **Em curso** | Teclas inválidas ignoradas e ficheiros inválidos tratados; falta a mensagem visível. |
| 2 | Como jogador, quero jogar uma partida de 60 segundos contra o computador ou contra um amigo. | R2 | **Feito** | Testada em modo 1 e modo 2. |
| 3 | Como programador, quero o código separado em módulos com funções, para ser fácil de manter. | R2 | **Por fazer** | Já há 114 funções e 7 classes, mas está tudo num ficheiro. |
| 4 | Como jogador, quero que os resultados fiquem guardados num ficheiro e ver o top 5. | R3 | **Por fazer** | Objetivo do Sprint 2 (plano na secção 4). |
| 5 | Como jogador, quero dar consentimento antes da foto e que ela seja apagada no fim. | Extra | **Em curso** | A tecla X já apaga as fotos; falta o consentimento e apagar automaticamente ao sair. |
| 6 | Como jogador, quero escolher o estádio. | Extra | **Feito** | 5 estádios; a escolha fica guardada em `heads/estadio.txt`. |
| 7 | Como jogador, quero escolher a dificuldade do bot e ter um tempo real de 60 s. | Extra | **Por fazer** | O bot tem uma única velocidade (4.4); o tempo é contado por frames. |
| 8 | Como professor, quero um README e 5 casos de teste. | R4 | **Em curso** | Há um rascunho do README; os testes ainda não estão escritos. |
| 9 | Como jogador, quero jogar com um comando de PS5, PS4 ou Xbox. | Extra | **Feito** | História nova, feita neste sprint. |
| 10 | Como jogador, quero usar uma foto do computador se não tiver webcam. | Extra | **Feito** | História nova (tecla F no ecrã da câmara). |
| 11 | Como jogador, quero que a bola não fique presa entre os dois jogadores. | Extra | **Feito** | História nova: regra "bola ao ar" ao fim de 3 s. |

## 6. Registo do Sprint

**Período:** [a preencher] a 24/11/2026 · **Esforço total estimado:** 16 h

| Membro | Papel no sprint | O que fez | Horas |
|---|---|---|---|
| Tiago Costa | [a preencher] | [a preencher] | [ ] |
| André Filipe | [a preencher] | [a preencher] | [ ] |
| Guilherme Lopes | [a preencher] | [a preencher] | [ ] |

**Dificuldades e decisões:** [a preencher: por exemplo, porque mudaram de modo de texto para pygame, problemas com a webcam ou com os comandos]

## 7. Uso de IA

| Ferramenta | Para que foi usada | Como verificámos o resultado |
|---|---|---|
| Claude (Anthropic) | Gerar o mapa de funções e o rascunho desta nota a partir do código, e preparar o README e o repositório do GitHub. | O número de funções do mapa foi comparado automaticamente com o código (114 = 114). [a preencher: a equipa leu e corrigiu as descrições?] |
| [a preencher] | [a preencher: por exemplo, partes do código, física, webcam] | [a preencher: por exemplo, testámos a jogar, lemos e percebemos o código] |

Os testes sem janela referidos nas secções 2 e 3 também foram feitos com a ajuda da IA. A equipa deve repeti-los ou confirmá-los a jogar antes de entregar.
