"""
Servidor Web Flask para Auditoria Acadêmica de Atividades Complementares - Faculdade SENAI Fatesg.
Permite upload de arquivos, leitura OCR, correções visuais em tempo real e exportação.
"""

import os
import io
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from auditor import AuditorCertificados
from regras_fatesg import CATEGORIAS, calcular_horas, formatar_tempo, detalhar_computo
from main import exportar_excel

app = Flask(__name__)
app.config["SECRET_KEY"] = "fatesg-horas-complementares-2026"
app.config["UPLOAD_FOLDER"] = Path(__file__).resolve().parent / "uploads"
app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max
app.config["TEMPLATES_AUTO_RELOAD"] = True


auditor = AuditorCertificados()

# Armazenamento em memória da sessão de auditoria atual
lote_auditoria = []


@app.route("/")
def index():
    return render_template("index.html", categorias=CATEGORIAS)


@app.route("/api/categorias", methods=["GET"])
def get_categorias():
    """Retorna a lista de categorias e suas regras para o frontend."""
    return jsonify(CATEGORIAS)


@app.route("/api/auditar-texto", methods=["POST"])
def auditar_texto():
    """Audita o texto bruto extraído de um certificado."""
    dados = request.get_json() or {}
    texto = dados.get("texto", "")
    resultado = auditor.analisar_texto(texto)
    resultado["texto_bruto"] = texto
    resultado["origem"] = "Texto Manual / OCR"
    return jsonify(resultado)


@app.route("/api/auditar-upload", methods=["POST"])
def auditar_upload():
    """Processa um ou múltiplos arquivos enviados (PDF, TXT, Imagens)."""
    if "arquivos" not in request.files and "arquivo" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado."}), 400

    arquivos = request.files.getlist("arquivos") or [request.files["arquivo"]]
    novos_resultados = []

    for arq in arquivos:
        if not arq or not arq.filename:
            continue
        nome_seguro = secure_filename(arq.filename)
        caminho_salvo = app.config["UPLOAD_FOLDER"] / nome_seguro
        arq.save(str(caminho_salvo))

        try:
            texto = auditor.extrair_texto_arquivo(caminho_salvo)
            res = auditor.analisar_texto(texto)
            res["texto_bruto"] = texto
            res["origem"] = nome_seguro

            # Verificar se este arquivo já existe no lote de auditoria
            encontrado = False
            for idx, it in enumerate(lote_auditoria):
                it_origem = it.get("origem") or it.get("arquivo_origem")
                if it_origem and it_origem.lower() == nome_seguro.lower():
                    res["id"] = it.get("id")
                    lote_auditoria[idx] = res
                    encontrado = True
                    break
            if not encontrado:
                novo_id = max([it.get("id", 0) for it in lote_auditoria], default=0) + 1
                res["id"] = novo_id
                lote_auditoria.append(res)

            novos_resultados.append(res)
        except Exception as e:
            novos_resultados.append({
                "origem": nome_seguro,
                "nome_aluno": None,
                "nome_evento": None,
                "entidade_emissora": None,
                "carga_horaria_declarada": None,
                "categoria_identificada": None,
                "carga_horaria_computada": 0,
                "status_leitura": "DADOS_FALTANTES",
                "texto_bruto": f"Erro na leitura: {str(e)}",
                "erro": str(e)
            })

    return jsonify(novos_resultados)


@app.route("/api/recalcular", methods=["POST"])
def recalcular():
    """
    Recalcula as horas computadas, minutos exatos e explicação clara com base em edições manuais
    feitas pelo usuário na interface visual.
    """
    dados = request.get_json() or {}
    categoria = dados.get("categoria_identificada")
    horas_declaradas = dados.get("carga_horaria_declarada")
    nome_aluno = dados.get("nome_aluno")

    try:
        horas_float = float(horas_declaradas) if horas_declaradas is not None and str(horas_declaradas).strip() != "" else None
    except ValueError:
        horas_float = None

    if not nome_aluno or horas_float is None or not categoria or categoria not in CATEGORIAS:
        return jsonify({
            "carga_horaria_computada": 0,
            "minutos_computados": 0,
            "tempo_formatado": "0 minutos",
            "tempo_resumo": "0h (0 min)",
            "explicacao_calculo": "Dados vitais incompletos para cálculo.",
            "status_leitura": "DADOS_FALTANTES"
        })

    info = detalhar_computo(categoria, horas_float)

    return jsonify({
        "carga_horaria_computada": info["horas_computadas"],
        "minutos_computados": info["minutos_computados"],
        "tempo_formatado": info["tempo_formatado"],
        "tempo_resumo": info["tempo_resumo"],
        "explicacao_calculo": info["explicacao_calculo"],
        "status_leitura": info["status_leitura"]
    })


@app.route("/api/lote", methods=["GET", "POST", "DELETE"])
def gerenciar_lote():
    """Gerencia a lista atual de certificados auditados, impedindo duplicatas."""
    global lote_auditoria

    if request.method == "GET":
        return jsonify(lote_auditoria)

    if request.method == "POST":
        item = request.get_json() or {}
        item_id = item.get("id")
        origem = item.get("origem") or item.get("arquivo_origem")
        aluno = (item.get("nome_aluno") or "").strip().lower()
        evento = (item.get("nome_evento") or "").strip().lower()

        # Procurar se já existe este mesmo certificado no lote
        indice_existente = -1
        for idx, it in enumerate(lote_auditoria):
            # 1. Se tem o mesmo ID numérico
            if item_id and it.get("id") == item_id:
                indice_existente = idx
                break
            # 2. Se tem o mesmo nome de arquivo (e não é texto manual)
            it_origem = it.get("origem") or it.get("arquivo_origem")
            if origem and it_origem and origem != "Texto Manual / OCR" and origem.lower() == it_origem.lower():
                indice_existente = idx
                break
            # 3. Se tem o mesmo aluno e mesmo evento (evita reenviar o mesmo certificado com outro nome)
            it_aluno = (it.get("nome_aluno") or "").strip().lower()
            it_evento = (it.get("nome_evento") or "").strip().lower()
            if aluno and evento and it_aluno == aluno and it_evento == evento:
                indice_existente = idx
                break

        if indice_existente >= 0:
            # Preserva o ID original e atualiza o certificado existente sem duplicar linha
            item["id"] = lote_auditoria[indice_existente]["id"]
            lote_auditoria[indice_existente] = item
            return jsonify({
                "sucesso": True,
                "atualizado": True,
                "mensagem": "Certificado existente atualizado com sucesso no lote.",
                "lote": lote_auditoria
            })
        else:
            # Adiciona como novo certificado único
            proximo_id = max([it.get("id", 0) for it in lote_auditoria], default=0) + 1
            item["id"] = proximo_id
            lote_auditoria.append(item)
            return jsonify({
                "sucesso": True,
                "atualizado": False,
                "mensagem": "Novo certificado adicionado ao lote com sucesso.",
                "lote": lote_auditoria
            })

    if request.method == "DELETE":
        lote_auditoria = []
        return jsonify({"sucesso": True, "mensagem": "Lote esvaziado."})


@app.route("/api/lote/<int:item_id>", methods=["DELETE"])
def remover_item_lote(item_id):
    """Remove um item específico do lote."""
    global lote_auditoria
    lote_auditoria = [it for it in lote_auditoria if it.get("id") != item_id]
    return jsonify({"sucesso": True, "lote": lote_auditoria})


@app.route("/api/exportar-json", methods=["GET"])
def exportar_lote_json():
    """Exporta o lote atual para arquivo JSON."""
    conteudo = json.dumps(lote_auditoria, ensure_ascii=False, indent=2)
    buffer = io.BytesIO(conteudo.encode("utf-8"))
    return send_file(
        buffer,
        as_attachment=True,
        download_name="relatorio_auditoria_fatesg.json",
        mimetype="application/json"
    )


@app.route("/api/exportar-excel", methods=["GET"])
def exportar_lote_excel():
    """Exporta o lote atual para uma planilha Excel estilizada."""
    caminho_temp = app.config["UPLOAD_FOLDER"] / "relatorio_temporario.xlsx"
    exportar_excel(lote_auditoria, caminho_temp)
    return send_file(
        str(caminho_temp),
        as_attachment=True,
        download_name="relatorio_auditoria_fatesg.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SERVIDOR DE AUDITORIA ACADÊMICA SENAI FATESG INICIADO")
    print("  Acesse no navegador: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
