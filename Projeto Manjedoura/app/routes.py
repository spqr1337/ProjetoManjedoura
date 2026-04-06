from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

import pandas as pd
from flask import (
    Blueprint,
    Response,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from fpdf import FPDF
from werkzeug.security import check_password_hash

from .db import fetch_data, get_db_connection, get_nome_usuario


main_bp = Blueprint("main", __name__)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped_view


def verify_password(stored_password, provided_password):
    if not stored_password:
        return False

    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password, provided_password)

    return stored_password == provided_password


def excel_response(dataframe, filename, sheet_name):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def pdf_response(pdf, filename):
    raw_output = pdf.output(dest="S")
    if isinstance(raw_output, str):
        raw_output = raw_output.encode("latin-1")

    output = BytesIO(raw_output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


def build_simple_pdf(title, rows=None, empty_message=None):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(10)

    if empty_message:
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 8, empty_message)
        return pdf

    if rows:
        pdf.set_font("Arial", "", 10)
        for row in rows:
            pdf.multi_cell(0, 8, row)
            pdf.ln(1)

    return pdf


def calcular_previsao(segunda, sexta):
    with get_db_connection() as connection:
        registros = connection.execute(
            """
            SELECT
                cg.nome_gest,
                rc.data_cons,
                cp.tipo_prof
            FROM Registro_Consultas rc
            JOIN Gestacoes g ON g.id_gest = rc.id_gest
            JOIN Cadastro_Gestantes cg ON cg.cns = g.cns
            JOIN Cadastro_Profissionais cp ON cp.id_prof = rc.id_prof
            WHERE rc.id_cons IN (
                SELECT MAX(id_cons)
                FROM Registro_Consultas
                WHERE data_cons <= ?
                GROUP BY id_gest
            )
            """,
            (sexta.strftime("%Y-%m-%d"),),
        ).fetchall()

    previsao = []
    for registro in registros:
        ultima_consulta = datetime.strptime(registro["data_cons"], "%Y-%m-%d")
        ultimo_profissional = (registro["tipo_prof"] or "").strip().lower()
        proximo_profissional = (
            "Enfermeiro" if ultimo_profissional == "médico" else "Médico"
        )

        proxima_data = ultima_consulta + timedelta(weeks=4)
        if segunda <= proxima_data <= sexta:
            previsao.append(
                (registro["nome_gest"], proxima_data, proximo_profissional)
            )

    return previsao


@main_bp.context_processor
def inject_user_context():
    return {
        "nome_usuario": get_nome_usuario(),
        "is_authenticated": "usuario_id" in session,
    }


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        senha = request.form.get("senha", "")

        with get_db_connection() as connection:
            usuario = connection.execute(
                """
                SELECT id_prof, senha
                FROM Cadastro_Profissionais
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

        if usuario and verify_password(usuario["senha"], senha):
            session["usuario_id"] = usuario["id_prof"]
            return redirect(url_for("main.index"))

        return render_template("login.html", error="Usuario ou senha invalidos.")

    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    session.pop("usuario_id", None)
    return redirect(url_for("main.login"))


@main_bp.route("/")
@login_required
def index():
    return render_template("index.html")


@main_bp.route("/profissionais", methods=["GET", "POST"])
@login_required
def profissionais():
    with get_db_connection() as connection:
        if request.method == "POST":
            connection.execute(
                """
                INSERT INTO Cadastro_Profissionais (nome_prof, tipo_prof)
                VALUES (?, ?)
                """,
                (
                    request.form["nome_prof"],
                    request.form["tipo_prof"],
                ),
            )
            connection.commit()
            return redirect(url_for("main.profissionais"))

        profissionais_cadastrados = connection.execute(
            "SELECT * FROM Cadastro_Profissionais ORDER BY nome_prof ASC"
        ).fetchall()

    return render_template(
        "profissionais.html",
        profissionais=profissionais_cadastrados,
    )


@main_bp.route("/gestantes", methods=["GET", "POST"])
@login_required
def gestantes():
    with get_db_connection() as connection:
        if request.method == "POST":
            connection.execute(
                """
                INSERT INTO Cadastro_Gestantes (
                    nome_gest,
                    data_nasc,
                    cns,
                    pront,
                    blood_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request.form["nome_gest"],
                    request.form["data_nasc"],
                    request.form["cns"],
                    request.form["pront"],
                    request.form["blood_type"],
                ),
            )
            connection.commit()
            return redirect(url_for("main.gestantes"))

        gestantes_cadastradas = connection.execute(
            "SELECT * FROM Cadastro_Gestantes ORDER BY nome_gest ASC"
        ).fetchall()

    return render_template(
        "gestantes.html",
        gestantes=gestantes_cadastradas,
    )


@main_bp.route("/gestacoes", methods=["GET", "POST"])
@login_required
def gestacoes():
    with get_db_connection() as connection:
        if request.method == "POST":
            cns = request.form["cns"]
            dum = request.form["dum"]
            dpp = request.form["dpp"]
            num_gestas = request.form["num_gestas"]
            risco = request.form.get("risco")

            doencas = request.form.get("doencas", "").split(",")
            cpar = request.form.get("cpar", "").split(",")
            vacinas = request.form.get("vacinas", "").split(",")
            data_diagnostico = request.form.get("data_diagnostico")

            connection.execute(
                """
                INSERT INTO Gestacoes (cns, dum, dpp, num_gestas, risco)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cns, dum, dpp, num_gestas, risco),
            )
            gestacao_id = connection.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            for doenca_id in doencas:
                if doenca_id:
                    connection.execute(
                        """
                        INSERT INTO Gestacoes_Doencas (
                            id_gest,
                            id_doenca,
                            data_diagnostico
                        )
                        VALUES (?, ?, ?)
                        """,
                        (gestacao_id, doenca_id, data_diagnostico),
                    )

            for condicao_id in cpar:
                if condicao_id:
                    connection.execute(
                        """
                        INSERT INTO Gestacoes_Condicoes (
                            id_gest,
                            id_condicao,
                            data_diagnostico
                        )
                        VALUES (?, ?, ?)
                        """,
                        (gestacao_id, condicao_id, data_diagnostico),
                    )

            for vacina_id in vacinas:
                if vacina_id:
                    connection.execute(
                        """
                        INSERT INTO Gestacoes_Vacinas (id_gest, id_vacina)
                        VALUES (?, ?)
                        """,
                        (gestacao_id, vacina_id),
                    )

            connection.commit()
            return redirect(url_for("main.gestacoes"))

        doencas = connection.execute(
            "SELECT id_doenca, nome_doenca FROM Doencas ORDER BY nome_doenca ASC"
        ).fetchall()
        cpar = connection.execute(
            "SELECT id_condicao, nome_condicao FROM CPAR ORDER BY nome_condicao ASC"
        ).fetchall()
        vacinas = connection.execute(
            "SELECT id_vacina, nome_vacina FROM Vacinas ORDER BY nome_vacina ASC"
        ).fetchall()
        gestantes_cadastradas = connection.execute(
            """
            SELECT cns, nome_gest
            FROM Cadastro_Gestantes
            ORDER BY nome_gest ASC
            """
        ).fetchall()
        gestacoes_cadastradas = connection.execute(
            """
            SELECT g.id_gest, cg.nome_gest, g.cns, g.dum, g.dpp, g.risco
            FROM Gestacoes g
            JOIN Cadastro_Gestantes cg ON g.cns = cg.cns
            ORDER BY g.dum DESC
            """
        ).fetchall()

    return render_template(
        "gestacoes.html",
        gestantes=gestantes_cadastradas,
        gestacoes=gestacoes_cadastradas,
        doencas=doencas,
        cpar=cpar,
        vacinas=vacinas,
    )


@main_bp.route("/consultas", methods=["GET"])
@login_required
def lista_gestacoes_ativas():
    with get_db_connection() as connection:
        gestacoes_ativas = connection.execute(
            """
            SELECT
                g.id_gest,
                g.cns,
                g.dum,
                cg.nome_gest,
                CAST(((julianday('now') - julianday(g.dum)) / 7) AS INTEGER) AS semanas
            FROM Gestacoes g
            JOIN Cadastro_Gestantes cg ON g.cns = cg.cns
            WHERE (julianday('now') - julianday(g.dum)) / 7 < 42
            ORDER BY cg.nome_gest ASC
            """
        ).fetchall()

    return render_template("lista_gestacoes.html", gestacoes_ativas=gestacoes_ativas)


@main_bp.route("/consultas/<int:id_gest>", methods=["GET", "POST"])
@login_required
def registrar_consulta(id_gest):
    id_prof = session["usuario_id"]

    with get_db_connection() as connection:
        if request.method == "POST":
            data_cons = request.form.get("data_cons")
            peso = request.form.get("peso")
            press_art = request.form.get("press_art")
            bat_fet = request.form.get("bat_fet")
            alt_ute = request.form.get("alt_ute")
            obs = request.form.get("obs")

            connection.execute(
                """
                INSERT INTO Registro_Consultas (
                    id_gest,
                    id_prof,
                    data_cons,
                    peso,
                    press_art,
                    bat_fet,
                    alt_ute,
                    obs
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (id_gest, id_prof, data_cons, peso, press_art, bat_fet, alt_ute, obs),
            )

            doencas_selecionadas = request.form.get("doencas", "").split(",")
            connection.execute(
                "DELETE FROM Gestacoes_Doencas WHERE id_gest = ?",
                (id_gest,),
            )

            for doenca_id in doencas_selecionadas:
                if doenca_id:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO Gestacoes_Doencas (
                            id_gest,
                            id_doenca,
                            data_diagnostico
                        )
                        VALUES (?, ?, ?)
                        """,
                        (id_gest, doenca_id, data_cons),
                    )

            connection.commit()
            return redirect(url_for("main.lista_gestacoes_ativas"))

        gestacao = connection.execute(
            """
            SELECT
                g.id_gest,
                g.cns,
                g.dum,
                cg.nome_gest,
                CAST(((julianday('now') - julianday(g.dum)) / 7) AS INTEGER) AS semanas
            FROM Gestacoes g
            JOIN Cadastro_Gestantes cg ON g.cns = cg.cns
            WHERE g.id_gest = ?
            """,
            (id_gest,),
        ).fetchone()
        doencas = connection.execute(
            "SELECT id_doenca, nome_doenca FROM Doencas ORDER BY nome_doenca ASC"
        ).fetchall()
        doencas_selecionadas = connection.execute(
            "SELECT id_doenca FROM Gestacoes_Doencas WHERE id_gest = ?",
            (id_gest,),
        ).fetchall()
        consultas = connection.execute(
            """
            SELECT c.data_cons, p.nome_prof, c.peso, c.press_art, c.obs
            FROM Registro_Consultas c
            JOIN Cadastro_Profissionais p ON c.id_prof = p.id_prof
            WHERE c.id_gest = ?
            ORDER BY c.data_cons DESC
            """,
            (id_gest,),
        ).fetchall()

    return render_template(
        "consultas.html",
        gestacao=gestacao,
        doencas=doencas,
        doencas_selecionadas=[row["id_doenca"] for row in doencas_selecionadas],
        consultas=consultas,
    )


@main_bp.route("/relatorios")
@login_required
def pagina_relatorios():
    return render_template("relatorios.html")


@main_bp.route("/relatorios/gestacoes_acompanhamento")
@login_required
def gerar_relatorio_gestacoes():
    query = """
        SELECT
            g.id_gest AS ID,
            gest.nome_gest AS Nome,
            g.cns AS CNS,
            g.dum AS DUM,
            g.dpp AS DPP,
            CAST((julianday('now') - julianday(g.dum)) / 7 AS INTEGER) AS Semanas,
            (SELECT COUNT(*) FROM Registro_Consultas rc WHERE rc.id_gest = g.id_gest) AS Numero_Consultas,
            (
                SELECT COUNT(*)
                FROM Registro_Consultas rc
                JOIN Cadastro_Profissionais cp ON rc.id_prof = cp.id_prof
                WHERE rc.id_gest = g.id_gest AND cp.tipo_prof = 'Médico'
            ) AS Consultas_Medico,
            (
                SELECT COUNT(*)
                FROM Registro_Consultas rc
                JOIN Cadastro_Profissionais cp ON rc.id_prof = cp.id_prof
                WHERE rc.id_gest = g.id_gest AND cp.tipo_prof = 'Enfermeiro'
            ) AS Consultas_Enfermeiro
        FROM Gestacoes g
        JOIN Cadastro_Gestantes gest ON g.cns = gest.cns
        WHERE (julianday('now') - julianday(g.dum)) / 7 BETWEEN 1 AND 40
        ORDER BY gest.nome_gest ASC;
    """

    with get_db_connection() as connection:
        dataframe = pd.read_sql_query(query, connection)

    if not dataframe.empty:
        dataframe["ECC"] = dataframe.apply(
            lambda row: (
                "Normal"
                if row["Numero_Consultas"] == row["Semanas"] // 4
                else (
                    "Abaixo"
                    if row["Numero_Consultas"] < row["Semanas"] // 4
                    else "Acima"
                )
            ),
            axis=1,
        )
    else:
        dataframe = pd.DataFrame(
            columns=[
                "ID",
                "Nome",
                "CNS",
                "DUM",
                "DPP",
                "Semanas",
                "Numero_Consultas",
                "Consultas_Medico",
                "Consultas_Enfermeiro",
                "ECC",
            ]
        )

    return excel_response(
        dataframe,
        "gestacoes_em_acompanhamento.xlsx",
        "Acompanhamento",
    )


@main_bp.route("/relatorios/previsao_demanda")
@login_required
def gerar_previsao_demanda():
    query = """
        SELECT
            id_gest,
            dum,
            julianday('now') - julianday(dum) AS dias_gestacionais
        FROM Gestacoes
        WHERE (julianday('now') - julianday(dum)) / 7 BETWEEN 1 AND 40;
    """

    with get_db_connection() as connection:
        gestacoes = pd.read_sql_query(query, connection)

    if gestacoes.empty:
        pdf = build_simple_pdf(
            "Relatorio de Previsao de Demanda",
            empty_message="Nenhuma gestacao ativa encontrada para o periodo atual.",
        )
        return pdf_response(pdf, "previsao_demanda.pdf")

    gestacoes["dum"] = pd.to_datetime(gestacoes["dum"])
    primeira_semana_inicio = gestacoes["dum"].min()
    ultima_semana = 40
    data_atual = primeira_semana_inicio

    semanas = []
    consultas_enfermeiro = []
    consultas_medico = []

    while data_atual <= (primeira_semana_inicio + timedelta(weeks=ultima_semana)):
        semana_inicio = data_atual
        semana_fim = semana_inicio + timedelta(days=4)

        semanas.append(
            f"{semana_inicio.strftime('%d/%m/%y')} a {semana_fim.strftime('%d/%m/%y')}"
        )

        semana_enfermeiro = 0
        semana_medico = 0

        for _, row in gestacoes.iterrows():
            semanas_gestacionais = (semana_inicio - row["dum"]).days // 7 + 1
            if 1 <= semanas_gestacionais <= 28:
                if semanas_gestacionais % 4 == 1:
                    semana_enfermeiro += 1
                else:
                    semana_medico += 1
            elif 29 <= semanas_gestacionais <= 40:
                semana_medico += 1

        consultas_enfermeiro.append(semana_enfermeiro)
        consultas_medico.append(semana_medico)
        data_atual += timedelta(weeks=1)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Relatorio de Previsao de Demanda", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(70, 10, "Semana", border=1, align="C")
    pdf.cell(60, 10, "Consultas Enfermeiro", border=1, align="C")
    pdf.cell(60, 10, "Consultas Medico", border=1, align="C")
    pdf.ln()

    pdf.set_font("Arial", "", 10)
    for semana, enfermeiro, medico in zip(
        semanas, consultas_enfermeiro, consultas_medico
    ):
        pdf.cell(70, 10, semana, border=1, align="C")
        pdf.cell(60, 10, str(enfermeiro), border=1, align="C")
        pdf.cell(60, 10, str(medico), border=1, align="C")
        pdf.ln()

    return pdf_response(pdf, "previsao_demanda.pdf")


@main_bp.route("/relatorios/consultas", methods=["POST"])
@login_required
def gerar_txt():
    prontuario = request.form["prontuario"]
    gestante, consultas = fetch_data(prontuario)

    if not gestante:
        return "Gestante nao encontrada.", 404

    report_lines = [
        f"{gestante['nome_gest']} - CNS: {gestante['cns']} - PRONTUARIO: {gestante['pront']}",
        "=" * 80,
    ]

    for consulta in consultas:
        report_lines.append(
            f"DATA: {consulta['data_cons']}  PROFISSIONAL: {consulta['nome_prof'] or 'Nao registrado'}"
        )

        doencas = (
            consulta["doencas_associadas"].split(",")
            if consulta["doencas_associadas"]
            else ["NENHUMA"]
        )
        cpar = (
            consulta["cpar_associadas"].split(",")
            if consulta["cpar_associadas"]
            else ["NENHUMA"]
        )

        report_lines.append(
            "Doencas associadas: "
            + ", ".join([item.strip() for item in doencas[:5]])
            + (" e outros..." if len(doencas) > 5 else "")
        )
        report_lines.append(
            "Condicoes para alto risco: "
            + ", ".join([item.strip() for item in cpar[:5]])
            + (" e outros..." if len(cpar) > 5 else "")
        )
        report_lines.append(
            f"Registro de consulta: {consulta['obs'] or 'Nenhuma observacao registrada.'}"
        )
        report_lines.append("-" * 80)

    buffer = BytesIO()
    buffer.write("\n".join(report_lines).encode("utf-8"))
    buffer.seek(0)

    return Response(
        buffer,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=relatorio_consultas.txt"},
    )


@main_bp.route("/relatorios/previsao_detalhada", methods=["POST"])
@login_required
def previsao_detalhada():
    segunda = request.form.get("segunda")
    sexta = request.form.get("sexta")

    if not segunda or not sexta:
        return "Por favor, forneca ambas as datas.", 400

    segunda_dt = datetime.strptime(segunda, "%Y-%m-%d")
    sexta_dt = datetime.strptime(sexta, "%Y-%m-%d")

    if segunda_dt > sexta_dt:
        return "A data inicial deve ser anterior ou igual a data final.", 400

    resultados = calcular_previsao(segunda_dt, sexta_dt)
    dataframe = pd.DataFrame(
        {
            "Nome": [resultado[0] for resultado in resultados],
            "Data da Consulta": [
                resultado[1].strftime("%d/%m/%Y") for resultado in resultados
            ],
            "Profissional": [resultado[2] for resultado in resultados],
        }
    )

    if dataframe.empty:
        dataframe = pd.DataFrame(
            columns=["Nome", "Data da Consulta", "Profissional"]
        )

    return excel_response(dataframe, "previsao_detalhada.xlsx", "Previsao")


@main_bp.route("/relatorios/gestantes_atrasadas", methods=["POST"])
@login_required
def gestantes_atrasadas():
    hoje = datetime.now()

    with get_db_connection() as connection:
        registros = connection.execute(
            """
            SELECT
                cg.nome_gest,
                g.dum,
                MAX(rc.data_cons) AS ultima_consulta
            FROM Gestacoes g
            JOIN Cadastro_Gestantes cg ON cg.cns = g.cns
            JOIN Registro_Consultas rc ON rc.id_gest = g.id_gest
            GROUP BY g.id_gest, cg.nome_gest, g.dum
            """
        ).fetchall()

    atrasadas = []
    for registro in registros:
        ultima_consulta = datetime.strptime(registro["ultima_consulta"], "%Y-%m-%d")
        dum = datetime.strptime(registro["dum"], "%Y-%m-%d")
        semanas_gestacao = max(1, (hoje - dum).days // 7)

        if semanas_gestacao <= 28:
            intervalo = timedelta(weeks=4)
        elif 29 <= semanas_gestacao <= 36:
            intervalo = timedelta(weeks=2)
        else:
            intervalo = timedelta(weeks=1)

        if hoje - ultima_consulta > intervalo:
            atrasadas.append(
                (
                    registro["nome_gest"],
                    ultima_consulta.strftime("%d/%m/%Y"),
                )
            )

    output = BytesIO()
    lines = [
        "Relatorio de Gestantes Atrasadas",
        "",
        f"Data de geracao: {hoje.strftime('%d/%m/%Y')}",
        "",
        "Nome da Gestante\tUltima Consulta",
        "-" * 40,
    ]
    lines.extend([f"{nome}\t{data}" for nome, data in atrasadas])
    output.write("\n".join(lines).encode("utf-8"))
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="gestantes_atrasadas.txt",
        mimetype="text/plain",
    )
