import sqlite3

from flask import current_app, session


def get_db_connection():
    connection = sqlite3.connect(str(current_app.config["DATABASE_PATH"]))
    connection.row_factory = sqlite3.Row
    return connection


def get_nome_usuario():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None

    with get_db_connection() as connection:
        usuario = connection.execute(
            "SELECT nome_prof FROM Cadastro_Profissionais WHERE id_prof = ?",
            (usuario_id,),
        ).fetchone()

    return usuario["nome_prof"] if usuario else None


def fetch_data(prontuario):
    with get_db_connection() as connection:
        gestante = connection.execute(
            """
            SELECT nome_gest, cns, pront
            FROM Cadastro_Gestantes
            WHERE pront = ?
            """,
            (prontuario,),
        ).fetchone()

        if not gestante:
            return None, []

        consultas = connection.execute(
            """
            SELECT
                rc.data_cons,
                cp.nome_prof,
                GROUP_CONCAT(DISTINCT d.nome_doenca) AS doencas_associadas,
                GROUP_CONCAT(DISTINCT cpar.nome_condicao) AS cpar_associadas,
                rc.obs
            FROM Registro_Consultas rc
            LEFT JOIN Cadastro_Profissionais cp ON rc.id_prof = cp.id_prof
            LEFT JOIN Gestacoes g ON rc.id_gest = g.id_gest
            LEFT JOIN Gestacoes_Doencas gd ON g.id_gest = gd.id_gest
            LEFT JOIN Doencas d ON gd.id_doenca = d.id_doenca
            LEFT JOIN Gestacoes_Condicoes gc ON g.id_gest = gc.id_gest
            LEFT JOIN CPAR cpar ON gc.id_condicao = cpar.id_condicao
            WHERE g.cns = ?
            GROUP BY rc.id_cons, rc.data_cons, cp.nome_prof, rc.obs
            ORDER BY rc.data_cons DESC
            """,
            (gestante["cns"],),
        ).fetchall()

    return gestante, consultas
