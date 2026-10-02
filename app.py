from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

BANCO = "fila.db"


def conectar_banco():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_banco():
    conexao = conectar_banco()

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            prioridade TEXT NOT NULL,
            status TEXT NOT NULL,
            data_entrada TEXT NOT NULL,
            data_finalizacao TEXT
        )
    """)

    conexao.commit()
    conexao.close()


@app.route("/")
def index():
    conexao = conectar_banco()

    clientes = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE status != 'Concluído'
        AND status != 'Cancelado'
        ORDER BY
            CASE
                WHEN prioridade = 'Preferencial' THEN 0
                ELSE 1
            END,
            id ASC
    """).fetchall()

    conexao.close()

    return render_template("index.html", clientes=clientes)


@app.route("/adicionar", methods=["POST"])
def adicionar():
    nome = request.form["nome"]
    prioridade = request.form["prioridade"]

    data_entrada = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    conexao = conectar_banco()

    conexao.execute("""
        INSERT INTO clientes
        (nome, prioridade, status, data_entrada)
        VALUES (?, ?, ?, ?)
    """, (nome, prioridade, "Aguardando", data_entrada))

    conexao.commit()
    conexao.close()

    return redirect(url_for("index"))


@app.route("/chamar_proximo")
def chamar_proximo():
    conexao = conectar_banco()

    # Verifica se já existe alguém em atendimento
    atendimento_atual = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE status = 'Em Atendimento'
        LIMIT 1
    """).fetchone()

    if atendimento_atual:
        conexao.close()
        return redirect(url_for("index"))

    # Preferenciais aparecem primeiro.
    # Dentro da mesma prioridade, é respeitada a ordem de chegada.
    proximo = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE status = 'Aguardando'
        ORDER BY
            CASE
                WHEN prioridade = 'Preferencial' THEN 0
                ELSE 1
            END,
            id ASC
        LIMIT 1
    """).fetchone()

    if proximo:
        conexao.execute("""
            UPDATE clientes
            SET status = 'Em Atendimento'
            WHERE id = ?
        """, (proximo["id"],))

        conexao.commit()

    conexao.close()

    return redirect(url_for("index"))


@app.route("/status/<int:id>/<novo_status>")
def alterar_status(id, novo_status):
    conexao = conectar_banco()

    if novo_status == "Concluído":
        data_finalizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        conexao.execute("""
            UPDATE clientes
            SET status = ?, data_finalizacao = ?
            WHERE id = ?
        """, (novo_status, data_finalizacao, id))

    else:
        conexao.execute("""
            UPDATE clientes
            SET status = ?
            WHERE id = ?
        """, (novo_status, id))

    conexao.commit()
    conexao.close()

    return redirect(url_for("index"))


@app.route("/cancelar/<int:id>")
def cancelar(id):
    conexao = conectar_banco()

    data_finalizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    conexao.execute("""
        UPDATE clientes
        SET status = 'Cancelado',
            data_finalizacao = ?
        WHERE id = ?
    """, (data_finalizacao, id))

    conexao.commit()
    conexao.close()

    return redirect(url_for("index"))


@app.route("/historico")
def historico():
    conexao = conectar_banco()

    clientes = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE status = 'Concluído'
        OR status = 'Cancelado'
        ORDER BY id DESC
    """).fetchall()

    conexao.close()

    return render_template("historico.html", clientes=clientes)


if __name__ == "__main__":
    criar_banco()

    app.run(debug=True)