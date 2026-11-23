# Nota de progresso · Sprint 1

**Projeto:** Head Ball Webcam · **UC:** Fundamentos de Programação · CTeSP em Cibersegurança, Instituto Piaget Almada

**Equipa:** Tiago Costa, André Filipe, Guilherme Lopes · **Entrega:** 24/11/2026

**Código entregue:** https://github.com/Tiago-Costa-git/headball-webcam · 5 ficheiros Python (`headball_webcam.py`, `base_dados.py`, `powerups.py`, `clima.py`, `testes/test_jogo.py`), 165 funções e métodos · Python 3 + pygame-ce, numpy, opencv-python, sqlite3

## 1. Resumo

O jogo é jogável do princípio ao fim e já vai além do protótipo mínimo:

- **Contas:** cada jogador entra com o seu nome. As partidas, os pontos e as estatísticas ficam guardados numa base de dados SQLite.
- **Três modos:** contra o bot, 2 jogadores e **competitivo**, contra bots cada vez mais difíceis até perder.
- **Durante a partida:** aparecem **power-ups** e o **clima** muda o jogo: chuva com poças, trovoada com relâmpagos, neve escorregadia e calor com fogo no relvado.
- **Ecrãs de consulta:** histórico das últimas partidas e estatísticas com o top 5.
- **Já existia:** cabeças pela webcam, 5 estádios e comandos PS5, PS4 e Xbox.

Os requisitos R1 (menu com validação) e R2 (funções e módulos) estão cumpridos. O R3 (lista de dados + ficheiro), que era o objetivo do Sprint 2, ficou adiantado: os dados vão para a base de dados e também para um ficheiro de texto. Para o R4 já existem 9 casos de teste automáticos.

## 2. R1: menu com validação de entrada

**Onde está:** na função `main()` de `headball_webcam.py`, no bloco `if state == "menu":` (a partir da linha 2051), e no ecrã do nome (linha 2027), que usa `validar_nome()` de `base_dados.py`.

| Tecla no menu | O que faz |
|---|---|
| 1 / 2 / 3 | Contra o bot / 2 jogadores / competitivo |
| H / E | Histórico / estatísticas |
| N | Mudar de jogador (outra conta) |
| B | Trocar de estádio (a escolha fica guardada) |
| C / V / X | Foto do J1 / foto do J2 / apagar as fotos |
| T | Escolher o clima (aleatório, limpo, chuva, trovoada, neve, calor) |
| TAB / F11 / ESC | Controlos / ecrã inteiro / sair |

**Entradas inválidas que o jogo trata:**

- **Tecla sem função no menu** (por exemplo Q): aparece "Tecla inválida! Usa as teclas do menu." e o jogo continua.
- **Nome vazio ou só com espaços:** aparece "Escreve um nome."
- **Nome com mais de 12 caracteres:** o jogo não deixa escrever mais e mostra "Máximo 12 caracteres."
- **Nome com símbolos** (por exemplo `Tiago!` ou `x'; DROP TABLE--`): aparece "Só letras, números, espaço, - e _."
  - As consultas à base de dados usam parâmetros (`?`), por isso mesmo um nome malicioso nunca seria executado como SQL.
  - Esta proteção está testada no teste 1.
- **Ficheiro `heads/estadio.txt` estragado** (por exemplo `abc`): o jogo usa o estádio 0.
- **Número de estádio fora do intervalo** (`99`): o valor passa por `% len(backgrounds)`.
- **Base de dados indisponível** (pasta sem permissão, ficheiro corrompido): o jogo abre na mesma e diz "Base de dados indisponível" quando se tenta abrir o histórico.
- **OpenCV em falta ou webcam com erro:** aparece uma mensagem em vez de o jogo fechar.

## 3. R2: funções e módulos

O código está dividido em **5 ficheiros**, com **165 funções e métodos**, todos descritos no **mapa de funções**:

| Ficheiro | O que tem |
|---|---|
| `headball_webcam.py` | Jogo: física, jogadores, bot, partida, estádios, desenho, ecrãs e ciclo principal |
| `base_dados.py` | Contas, histórico, estatísticas, ranking e exportação para texto. Não usa pygame |
| `powerups.py` | Lógica dos power-ups. Não usa pygame |
| `clima.py` | Lógica do clima (poças, relâmpagos, neve, fogo). Não usa pygame |
| `testes/test_jogo.py` | 9 casos de teste automáticos |

Separámos a base de dados, os power-ups e o clima do pygame. Assim conseguimos testá-los sem abrir a janela, e a classe `Match` continua a ter só lógica.

**O que falta no R2:** o `headball_webcam.py` ainda tem cerca de 2200 linhas. Separar também a física, os cenários e a webcam em módulos próprios fica para o Sprint 2.

## 4. O que funciona e o que falta

**Funciona:**

- **Contas:** ao abrir pela primeira vez, o jogo pede o nome. Depois entra sempre na última conta, e a tecla N muda de conta.
- **Base de dados SQLite** (`dados/headball.db`) com duas tabelas:
  - `jogadores`: nome, data de criação e último acesso;
  - `partidas`: data, modo, adversário, golos, resultado, pontos e nível.
  - **Pontos:** vitória 3, empate 1, derrota 0. No competitivo, cada vitória vale mais o número do nível.
- **Histórico** das últimas 10 partidas, com GANHOU, EMPATE ou PERDEU.
- **Estatísticas:** pontos, partidas, vitórias (com %), empates, derrotas, golos marcados e sofridos, média de golos, maior sequência de vitórias, melhor nível no competitivo e **top 5** de todos os jogadores.
- **Modo competitivo:** 5 níveis de bot, de Estreante a Lenda, e depois "Lenda +1", "+2"…
  - Em cada nível o bot fica mais rápido, chuta e salta mais vezes.
  - Ganhar passa ao nível seguinte. Perder ou empatar acaba a corrida.
  - As partidas duram 45 s.
- **Power-ups** que aparecem a cada 8 a 12 segundos:
  - **Velocidade:** ×1,45 durante 6 s.
  - **Super chuto:** ×1,8 durante 6 s.
  - **Super salto:** ×1,3 durante 6 s.
  - **Gelo:** congela o adversário 2,5 s.
- **Ficheiro de texto** `dados/resultados.txt`, reescrito depois de cada partida, com uma linha por partida (requisito R3).
- **Clima** (tecla T; por defeito é aleatório e muda a meio da partida):
  - **Chuva:** jogadores 8% mais lentos, a bola ressalta menos e formam-se poças que travam a bola e os jogadores.
  - **Trovoada:** chuva e relâmpagos. Antes de cada raio aparece um aviso amarelo no chão; quem lá ficar é atordoado 1,5 s e a bola é atirada ao ar.
  - **Neve:** o chão fica escorregadio (os jogadores demoram a travar) e a bola desliza mais.
  - **Calor:** aparecem zonas a arder (primeiro fumo, depois fogo); quem pisa o fogo salta de dor e a bola é projetada para cima.
- **Ecrã inteiro (F11)** e letras pixelizadas mas legíveis, desenhadas à resolução da janela.
- **Tudo o que já existia:** física com pernas articuladas, "bola ao ar", fotos pela webcam ou de ficheiro, 5 estádios animados e comandos.

**Falta:**

- **Jogo online:** decidimos não o fazer neste sprint.
  - Um jogo de física em tempo real online precisa de um servidor, de sincronizar a bola 60 vezes por segundo e de lidar com o atraso da rede.
  - Também obriga a abrir portas e a validar tudo o que chega da rede. Feito à pressa, ficava instável e inseguro.
  - Fica como objetivo possível do Sprint 3, começando por **rede local (LAN)**.
- **Tempo da partida:** continua a ser contado por frames. Num PC lento, a partida demora mais do que o tempo indicado.
- **Fotos:** o jogo ainda não pede consentimento antes de tirar a foto.
- **Modo 2 jogadores:** a partida só fica na conta do J1. O J2 não tem conta própria.

## 5. Product Backlog atualizado

| # | História | Req. | Estado |
|---|---|---|---|
| 1 | Como jogador, quero um menu que só aceite opções válidas. | R1 | **Feito** |
| 2 | Como jogador, quero jogar uma partida contra o computador ou contra um amigo. | R2 | **Feito** |
| 3 | Como programador, quero o código separado em módulos. | R2 | **Em curso** (3 módulos + testes) |
| 4 | Como jogador, quero que os resultados fiquem guardados num ficheiro e ver o top 5. | R3 | **Feito** (SQLite + resultados.txt) |
| 5 | Como jogador, quero dar consentimento antes da foto e que ela seja apagada no fim. | Extra | **Em curso** (X apaga as fotos) |
| 6 | Como jogador, quero escolher o estádio. | Extra | **Feito** |
| 7 | Como jogador, quero escolher a dificuldade do bot e ter um tempo real. | Extra | **Em curso** (níveis no competitivo; tempo ainda por frames) |
| 8 | Como professor, quero um README e 5 casos de teste. | R4 | **Feito** (7 testes; README atualizado) |
| 9 | Como jogador, quero jogar com um comando. | Extra | **Feito** |
| 10 | Como jogador, quero usar uma foto do computador se não tiver webcam. | Extra | **Feito** |
| 11 | Como jogador, quero que a bola não fique presa entre os jogadores. | Extra | **Feito** |
| 12 | Como jogador, quero ter uma conta com o meu nome e os meus pontos. | Extra | **Feito** |
| 13 | Como jogador, quero ver o histórico das minhas partidas. | Extra | **Feito** |
| 14 | Como jogador, quero ver as minhas estatísticas. | Extra | **Feito** |
| 15 | Como jogador, quero power-ups durante a partida. | Extra | **Feito** |
| 16 | Como jogador, quero um modo competitivo contra bots cada vez mais difíceis. | Extra | **Feito** |
| 17 | Como jogador, quero jogar contra outra pessoa noutro computador. | Extra | **Por fazer** (Sprint 3, LAN) |
| 18 | Como jogador, quero que o clima mude a partida (chuva, trovoada, neve, calor). | Extra | **Feito** |

## 6. Registo do Sprint

**Período:** [a preencher] a 24/11/2026 · **Esforço total estimado:** 16 h

| Membro | Papel no sprint | O que fez | Horas |
|---|---|---|---|
| Tiago Costa | [a preencher] | [a preencher] | [ ] |
| André Filipe | [a preencher] | [a preencher] | [ ] |
| Guilherme Lopes | [a preencher] | [a preencher] | [ ] |

**Dificuldades e decisões:** [a preencher: por exemplo, porque escolheram SQLite, porque deixaram o jogo online para depois]

## 7. Uso de IA

| Ferramenta | Para que foi usada | Como verificámos |
|---|---|---|
| Claude (Anthropic) | Apoio na escrita de partes do código (incluindo a base de dados, os power-ups, o clima e o modo competitivo) | Lemos e percebemos o código antes de o integrar, corremos os 9 testes e testámos a jogar |
| Claude (Anthropic) | Deteção e correção de erros (por exemplo, as animações do cenário passavam por cima das balizas) | Aplicámos as correções e testámos o jogo nos 5 estádios |
| Claude (Anthropic) | Apoio na documentação: mapa de funções, nota de progresso e README, feitos a partir do código | Revimos os textos; o mapa foi comparado automaticamente com o código (165 = 165) |

A ideia, as decisões de design, os testes a jogar e a integração final foram feitos pela equipa.
