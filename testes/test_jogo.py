"""Casos de teste do Head Ball (requisito R4).
Correr na pasta do projeto:  py -m unittest discover testes -v
Não abrem janela: testam a base de dados, os power-ups e os níveis do bot."""
import os
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base_dados as bd
import clima as cl
import powerups as pw


class JogadorFalso:
    """Só o que os power-ups e o clima precisam de um jogador."""
    def __init__(self, x, y):
        self.x, self.y, self.efeitos = x, y, {}
        self.vy, self.on_ground = 0.0, True


class BolaFalsa:
    def __init__(self, x, y):
        self.x, self.y, self.vx, self.vy = x, y, 0.0, 0.0


class TestNomes(unittest.TestCase):
    def test_1_validacao_do_nome(self):
        self.assertEqual(bd.validar_nome("  Tiago   Costa "), (True, "Tiago Costa"))
        self.assertFalse(bd.validar_nome("")[0])                  # vazio
        self.assertFalse(bd.validar_nome("   ")[0])               # só espaços
        self.assertFalse(bd.validar_nome("a" * 13)[0])            # demasiado comprido
        self.assertFalse(bd.validar_nome("Tiago!")[0])            # símbolo proibido
        self.assertFalse(bd.validar_nome("x'; DROP TABLE--")[0])  # tentativa de injeção de SQL


class TestBaseDados(unittest.TestCase):
    def setUp(self):
        self.conn = bd.ligar(":memory:")                         # base de dados temporária, só em memória

    def tearDown(self):
        self.conn.close()

    def test_2_conta_criada_e_reutilizada(self):
        id1, nome1 = bd.entrar(self.conn, "Tiago")
        id2, nome2 = bd.entrar(self.conn, "tiago")               # maiúsculas não contam
        self.assertEqual(id1, id2)
        self.assertEqual(nome2, "Tiago")
        self.assertEqual(bd.ultimo_jogador(self.conn), (id1, "Tiago"))
        with self.assertRaises(ValueError):
            bd.entrar(self.conn, "")

    def test_3_resultado_e_pontos(self):
        jid, _ = bd.entrar(self.conn, "Andre")
        self.assertEqual(bd.guardar_partida(self.conn, jid, "vs Bot", "Bot", 3, 1)["pontos"], 3)
        self.assertEqual(bd.guardar_partida(self.conn, jid, "vs Bot", "Bot", 2, 2)["resultado"], "E")
        self.assertEqual(bd.guardar_partida(self.conn, jid, "vs Bot", "Bot", 0, 4)["texto"], "PERDEU")
        self.assertEqual(bd.guardar_partida(self.conn, jid, "Competitivo", "Bot", 2, 0, nivel=3)["pontos"], 6)

    def test_4_historico_e_estatisticas(self):
        jid, _ = bd.entrar(self.conn, "Guilherme")
        for gm, gs in [(1, 0), (2, 1), (0, 0), (3, 2), (1, 4)]:
            bd.guardar_partida(self.conn, jid, "vs Bot", "Bot", gm, gs)
        est = bd.ler_estatisticas(self.conn, jid)
        self.assertEqual((est["partidas"], est["vitorias"], est["empates"], est["derrotas"]), (5, 3, 1, 1))
        self.assertEqual((est["golos_marcados"], est["golos_sofridos"], est["pontos"]), (7, 7, 10))
        self.assertEqual(est["melhor_sequencia"], 2)
        hist = bd.ler_historico(self.conn, jid, limite=3)
        self.assertEqual(len(hist), 3)
        self.assertEqual(hist[0]["resultado"], "D")             # a mais recente aparece primeiro
        outro, _ = bd.entrar(self.conn, "Tiago")
        self.assertEqual(bd.ranking(self.conn)[0][0], "Guilherme")
        self.assertEqual(bd.ler_estatisticas(self.conn, outro)["partidas"], 0)


class TestPowerUps(unittest.TestCase):
    def test_5_efeitos_e_apanhar(self):
        a, b = JogadorFalso(300, 400), JogadorFalso(800, 400)
        self.assertEqual(pw.aplicar("gelo", a, b), "GELO")
        self.assertIn("gelo", b.efeitos)                        # o gelo congela o adversário
        self.assertNotIn("gelo", a.efeitos)
        efeitos = {"velocidade": 2, "salto": 1}
        self.assertEqual(pw.atualizar_efeitos(efeitos), {"velocidade": 1})
        estado = {"lista": [pw.PowerUp("super_chuto", 300, 400)], "espera": 999}
        quem, texto = pw.passo_powerups(estado, (a, b), 100, 1000, 450, random.Random(1))
        self.assertIs(quem, a)
        self.assertEqual(texto, "SUPER CHUTO")
        self.assertIn("super_chuto", a.efeitos)
        self.assertEqual(estado["lista"], [])

    def test_6_powerup_aparece_e_desaparece(self):
        estado = {"lista": [], "espera": 1}
        longe = (JogadorFalso(-999, -999), JogadorFalso(-999, -999))
        pw.passo_powerups(estado, longe, 100, 1000, 450, random.Random(2))
        self.assertEqual(len(estado["lista"]), 1)
        for _ in range(pw.VIDA):
            pw.passo_powerups(estado, longe, 100, 1000, 450, random.Random(2))
        self.assertEqual(estado["lista"], [])                   # ninguém apanhou: desapareceu


class TestNiveis(unittest.TestCase):
    def test_7_bot_fica_mais_dificil(self):
        import headball_webcam as hb
        velocidades = [hb.nivel_bot(n)["velocidade"] for n in range(1, 10)]
        self.assertEqual(velocidades, sorted(velocidades))      # nunca fica mais fácil
        self.assertLessEqual(max(velocidades), 7.5)             # mas tem um limite
        self.assertEqual(hb.nivel_bot(2)["velocidade"], 4.4)    # nível 2 = bot normal do modo 1


class TestClima(unittest.TestCase):
    def test_8_chuva_faz_pocas_e_neve_escorrega(self):
        rnd = random.Random(4)
        est = cl.novo_estado("chuva", 100, 1000, rnd)
        j, bola = JogadorFalso(-999, 400), BolaFalsa(-999, 0)
        for _ in range(800):
            cl.passo_clima(est, (j, j), bola, 500, rnd)
        x = est["pocas"][0]["x"]
        self.assertTrue(cl.em_poca(est, x))                     # com chuva as poças crescem
        j.x = x
        self.assertLess(cl.velocidade(est, j), cl.params(est)["vel"])   # e quem lá está anda mais devagar
        neve = cl.novo_estado("neve", 100, 1000, rnd)
        self.assertLess(cl.params(neve)["inercia"], 1)           # neve: chão escorregadio
        self.assertGreater(cl.params(neve)["atrito"], cl.params(est)["atrito"])  # e a bola desliza mais

    def test_9_raio_e_fogo(self):
        rnd = random.Random(5)
        est = cl.novo_estado("trovoada", 100, 1000, rnd)
        j, longe, bola = JogadorFalso(500, 400), JogadorFalso(950, 400), BolaFalsa(-999, 0)
        est["raio"] = {"x": 510, "t": 1}                        # um raio prestes a cair ao lado do jogador
        eventos = cl.passo_clima(est, (j, longe), bola, 500, rnd)
        self.assertIn(("raio", 510), eventos)
        self.assertIn("atordoado", j.efeitos)                   # quem estava perto fica atordoado
        self.assertNotIn("atordoado", longe.efeitos)            # quem estava longe não
        calor = cl.novo_estado("calor", 100, 1000, rnd)
        calor["fogos"].append({"x": 300, "aviso": 0, "vida": 100})
        q = JogadorFalso(300, 400)
        cl.passo_clima(calor, (q, longe), bola, 500, rnd)
        self.assertLess(q.vy, 0)                                # pisou o fogo: salta
        self.assertIn("queimado", q.efeitos)


if __name__ == "__main__":
    unittest.main()
