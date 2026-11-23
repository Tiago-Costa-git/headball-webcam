"""Contas de jogador, histórico de partidas e estatísticas, guardados numa base de dados SQLite.

Não precisa de instalar nada: o sqlite3 vem com o Python.
A base de dados fica em dados/headball.db (só no teu computador; está no .gitignore).
Depois de cada partida também é escrito dados/resultados.txt, uma linha por partida (requisito R3).
"""
import os
import sqlite3
from datetime import datetime

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
CAMINHO_BD = os.path.join(PASTA, "headball.db")
CAMINHO_TXT = os.path.join(PASTA, "resultados.txt")

NOME_MAX = 12
PONTOS = {"V": 3, "E": 1, "D": 0}          # vitória, empate, derrota
TEXTO_RESULTADO = {"V": "GANHOU", "E": "EMPATE", "D": "PERDEU"}


def ligar(caminho=CAMINHO_BD):
    """Abre (ou cria) a base de dados e garante que as tabelas existem."""
    if caminho != ":memory:":
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    criar_tabelas(conn)
    return conn


def criar_tabelas(conn):
    """Cria as tabelas jogadores e partidas, se ainda não existirem."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jogadores (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL UNIQUE COLLATE NOCASE,
            criado        TEXT NOT NULL,
            ultimo_acesso TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS partidas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id      INTEGER NOT NULL REFERENCES jogadores(id) ON DELETE CASCADE,
            data            TEXT NOT NULL,
            modo            TEXT NOT NULL,
            adversario      TEXT NOT NULL,
            golos_marcados  INTEGER NOT NULL CHECK (golos_marcados >= 0),
            golos_sofridos  INTEGER NOT NULL CHECK (golos_sofridos >= 0),
            resultado       TEXT NOT NULL CHECK (resultado IN ('V', 'E', 'D')),
            pontos          INTEGER NOT NULL,
            nivel           INTEGER
        );
    """)
    conn.commit()


def validar_nome(nome):
    """Valida o nome escrito pelo jogador. Devolve (True, nome limpo) ou (False, mensagem de erro)."""
    if not isinstance(nome, str):
        return False, "Nome inválido."
    nome = " ".join(nome.split())                      # tira espaços a mais
    if not nome:
        return False, "Escreve um nome."
    if len(nome) > NOME_MAX:
        return False, f"Máximo {NOME_MAX} caracteres."
    if not all(c.isalnum() or c in " -_" for c in nome):
        return False, "Só letras, números, espaço, - e _."
    return True, nome


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def entrar(conn, nome):
    """Entra na conta com este nome (cria-a se não existir). Devolve (id, nome como ficou guardado)."""
    ok, nome = validar_nome(nome)
    if not ok:
        raise ValueError(nome)
    agora = _agora()
    linha = conn.execute("SELECT id, nome FROM jogadores WHERE nome = ?", (nome,)).fetchone()
    if linha is None:
        cur = conn.execute("INSERT INTO jogadores (nome, criado, ultimo_acesso) VALUES (?, ?, ?)", (nome, agora, agora))
        conn.commit()
        return cur.lastrowid, nome
    conn.execute("UPDATE jogadores SET ultimo_acesso = ? WHERE id = ?", (agora, linha["id"]))
    conn.commit()
    return linha["id"], linha["nome"]


def ultimo_jogador(conn):
    """Devolve (id, nome) do último jogador que entrou, ou None se ainda não houver contas."""
    linha = conn.execute("SELECT id, nome FROM jogadores ORDER BY ultimo_acesso DESC, id DESC LIMIT 1").fetchone()
    return (linha["id"], linha["nome"]) if linha else None


def calcular_resultado(golos_marcados, golos_sofridos):
    """'V', 'E' ou 'D' conforme o marcador."""
    if golos_marcados > golos_sofridos:
        return "V"
    return "E" if golos_marcados == golos_sofridos else "D"


def guardar_partida(conn, jogador_id, modo, adversario, golos_marcados, golos_sofridos, nivel=None):
    """Guarda uma partida e devolve um dicionário com o resultado e os pontos ganhos.
    No modo competitivo cada vitória vale 3 pontos mais o número do nível."""
    resultado = calcular_resultado(golos_marcados, golos_sofridos)
    pontos = PONTOS[resultado] + (nivel if (nivel and resultado == "V") else 0)
    conn.execute("""INSERT INTO partidas (jogador_id, data, modo, adversario, golos_marcados, golos_sofridos,
                    resultado, pontos, nivel) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (jogador_id, _agora(), modo, adversario, int(golos_marcados), int(golos_sofridos), resultado, pontos, nivel))
    conn.commit()
    return {"resultado": resultado, "texto": TEXTO_RESULTADO[resultado], "pontos": pontos}


def ler_historico(conn, jogador_id, limite=10):
    """Lista das últimas partidas do jogador (a mais recente primeiro), como dicionários."""
    linhas = conn.execute("""SELECT data, modo, adversario, golos_marcados, golos_sofridos, resultado, pontos, nivel
                             FROM partidas WHERE jogador_id = ? ORDER BY id DESC LIMIT ?""", (jogador_id, limite))
    return [dict(l) for l in linhas]


def melhor_sequencia(resultados):
    """Maior número de vitórias seguidas numa lista de resultados ('V', 'E', 'D') por ordem."""
    melhor = atual = 0
    for r in resultados:
        atual = atual + 1 if r == "V" else 0
        melhor = max(melhor, atual)
    return melhor


def ler_estatisticas(conn, jogador_id):
    """Estatísticas do jogador: partidas, vitórias, empates, derrotas, golos, pontos, etc."""
    l = conn.execute("""SELECT COUNT(*) AS partidas,
                               COALESCE(SUM(resultado = 'V'), 0) AS vitorias,
                               COALESCE(SUM(resultado = 'E'), 0) AS empates,
                               COALESCE(SUM(resultado = 'D'), 0) AS derrotas,
                               COALESCE(SUM(golos_marcados), 0) AS golos_marcados,
                               COALESCE(SUM(golos_sofridos), 0) AS golos_sofridos,
                               COALESCE(SUM(pontos), 0) AS pontos,
                               COALESCE(MAX(nivel), 0) AS melhor_nivel
                        FROM partidas WHERE jogador_id = ?""", (jogador_id,)).fetchone()
    est = dict(l)
    ordem = [r["resultado"] for r in conn.execute("SELECT resultado FROM partidas WHERE jogador_id = ? ORDER BY id", (jogador_id,))]
    est["melhor_sequencia"] = melhor_sequencia(ordem)
    est["percentagem_vitorias"] = round(100 * est["vitorias"] / est["partidas"]) if est["partidas"] else 0
    est["media_golos"] = round(est["golos_marcados"] / est["partidas"], 1) if est["partidas"] else 0.0
    return est


def ranking(conn, limite=5):
    """Top de jogadores por pontos: lista de (nome, pontos, vitórias)."""
    linhas = conn.execute("""SELECT j.nome, COALESCE(SUM(p.pontos), 0) AS pontos, COALESCE(SUM(p.resultado = 'V'), 0) AS vitorias
                             FROM jogadores j LEFT JOIN partidas p ON p.jogador_id = j.id
                             GROUP BY j.id ORDER BY pontos DESC, vitorias DESC, j.nome LIMIT ?""", (limite,))
    return [(l["nome"], l["pontos"], l["vitorias"]) for l in linhas]


def exportar_txt(conn, caminho=CAMINHO_TXT):
    """Escreve todas as partidas num ficheiro de texto, uma por linha (data;jogador;modo;adversário;marcador;resultado;pontos)."""
    linhas = conn.execute("""SELECT p.data, j.nome, p.modo, p.adversario, p.golos_marcados, p.golos_sofridos, p.resultado, p.pontos
                             FROM partidas p JOIN jogadores j ON j.id = p.jogador_id ORDER BY p.id""")
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("data;jogador;modo;adversario;golos_marcados;golos_sofridos;resultado;pontos\n")
            for l in linhas:
                f.write(";".join(str(x) for x in tuple(l)) + "\n")
        return True
    except OSError:
        return False                                   # sem permissão de escrita: o jogo continua
