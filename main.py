"""
Sistema de Auditoria Acadêmica de Atividades Complementares - Faculdade SENAI Fatesg.
Processa certificados (PDF, Imagens OCR, Texto), classifica segundo o regulamento,
calcula as horas e gera relatórios em JSON e Excel (.xlsx).
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

from auditor import AuditorCertificados
from regras_fatesg import CATEGORIAS

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def criar_pasta_certificados_se_nao_existir(pasta: Path) -> None:
    """Cria a pasta de certificados se ela não existir, mantendo-a vazia."""
    pasta.mkdir(parents=True, exist_ok=True)


def exportar_excel(resultados: List[Dict[str, Any]], caminho_saida: Path) -> None:
    """Gera uma planilha Excel (.xlsx) profissional com os certificados auditados."""
    if not OPENPYXL_AVAILABLE:
        print("[AVISO] Pacote openpyxl não disponível para exportar Excel. Instale com: pip install openpyxl")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Auditoria Fatesg"

    # Cores SENAI/Fatesg
    cor_azul_senai = "002F6C"
    cor_azul_claro = "E8F1FA"
    cor_sucesso = "C6EFCE"
    cor_texto_sucesso = "006100"
    cor_rejeitado = "FFC7CE"
    cor_texto_rejeitado = "9C0006"
    cor_dados_faltantes = "FFEB9C"
    cor_texto_faltantes = "9C6500"

    cabecalhos = [
        "Arquivo / Origem",
        "Nome do Aluno",
        "CPF do Aluno",
        "Nome do Evento / Curso",
        "Entidade Emissora",
        "Carga Horária Declarada",
        "Categoria Identificada",
        "Horas Computadas",
        "Status da Auditoria",
    ]

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9'),
    )

    # Agrupar resultados por aluno para auditoria estritamente individual
    from collections import OrderedDict
    grupos_alunos = OrderedDict()
    for r in resultados:
        nome = (r.get("nome_aluno") or "Aluno Não Identificado").strip()
        cpf = (r.get("cpf_aluno") or "Não informado").strip()
        chave = (nome, cpf)
        if chave not in grupos_alunos:
            grupos_alunos[chave] = []
        grupos_alunos[chave].append(r)

    # 1. Página Consolidada com seções separadas por aluno
    ws.title = "Auditoria Consolidada"
    linha_atual = 1

    # Título do Relatório Geral
    ws.merge_cells("A1:I1")
    celula_titulo = ws["A1"]
    celula_titulo.value = "FACULDADE SENAI FATESG - AUDITORIA DE ATIVIDADES COMPLEMENTARES"
    celula_titulo.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    celula_titulo.fill = PatternFill(start_color=cor_azul_senai, end_color=cor_azul_senai, fill_type="solid")
    celula_titulo.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35
    linha_atual = 3

    for (nome_aluno, cpf_aluno), lista_cursos in grupos_alunos.items():
        # Banner do Aluno
        ws.merge_cells(start_row=linha_atual, start_column=1, end_row=linha_atual, end_column=9)
        banner = ws.cell(row=linha_atual, column=1)
        banner.value = f"EXTRATO INDIVIDUAL DO ALUNO: {nome_aluno.upper()}  |  CPF: {cpf_aluno}"
        banner.font = Font(name="Calibri", size=12, bold=True, color="002F6C")
        banner.fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
        banner.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[linha_atual].height = 26
        linha_atual += 1

        # Cabeçalhos da Tabela do Aluno
        for col_num, cab in enumerate(cabecalhos, 1):
            cell = ws.cell(row=linha_atual, column=col_num)
            cell.value = cab
            cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[linha_atual].height = 22
        linha_atual += 1

        total_horas_aluno = 0.0
        total_decl_aluno = 0.0

        for r in lista_cursos:
            status = r.get("status_leitura", "DADOS_FALTANTES")
            horas_comp = float(r.get("carga_horaria_computada") or 0.0)
            horas_decl = float(r.get("carga_horaria_declarada") or 0.0)
            min_comp = int(r.get("minutos_computados") or round(horas_comp * 60))
            total_horas_aluno += horas_comp
            total_decl_aluno += horas_decl

            linha = [
                r.get("origem") or r.get("arquivo_origem", "Texto Direto"),
                nome_aluno,
                cpf_aluno,
                r.get("nome_evento", "-"),
                r.get("entidade_emissora", "-"),
                f"{horas_decl}h ({int(horas_decl * 60)} min)",
                r.get("categoria_identificada", "-"),
                f"{horas_comp}h ({min_comp} min)",
                status,
            ]
            for col_num, val in enumerate(linha, 1):
                c = ws.cell(row=linha_atual, column=col_num)
                c.value = val
                c.border = thin_border
                if col_num in [6, 8]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                elif col_num in [3, 9]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")

            # Estilo status
            cell_status = ws.cell(row=linha_atual, column=9)
            if status == "SUCESSO":
                cell_status.fill = PatternFill(start_color=cor_sucesso, end_color=cor_sucesso, fill_type="solid")
                cell_status.font = Font(name="Calibri", size=10, bold=True, color=cor_texto_sucesso)
            elif status == "REJEITADO_REGULAMENTO":
                cell_status.fill = PatternFill(start_color=cor_rejeitado, end_color=cor_rejeitado, fill_type="solid")
                cell_status.font = Font(name="Calibri", size=10, bold=True, color=cor_texto_rejeitado)
            else:
                cell_status.fill = PatternFill(start_color=cor_dados_faltantes, end_color=cor_dados_faltantes, fill_type="solid")
                cell_status.font = Font(name="Calibri", size=10, bold=True, color=cor_texto_faltantes)

            ws.row_dimensions[linha_atual].height = 20
            linha_atual += 1

        # Linha de Total Individual do Aluno (Meta 100h)
        total_min_aluno = int(round(total_horas_aluno * 60))
        pct_meta_aluno = min(100.0, (total_horas_aluno / 100.0) * 100.0)
        faltam_horas = max(0.0, 100.0 - total_horas_aluno)
        faltam_min = int(round(faltam_horas * 60))

        ws.merge_cells(start_row=linha_atual, start_column=1, end_row=linha_atual, end_column=7)
        cell_tot_label = ws.cell(row=linha_atual, column=1)
        cell_tot_label.value = (
            f"TOTAL DO ALUNO {nome_aluno.upper()} (META 100H): "
            f"Faltam {faltam_horas:.1f}h ({faltam_min} min)  |  Progresso: {pct_meta_aluno:.1f}%"
        )
        cell_tot_label.font = Font(name="Calibri", size=10, bold=True, color="000000")
        cell_tot_label.alignment = Alignment(horizontal="right", vertical="center")

        cell_tot_val = ws.cell(row=linha_atual, column=8)
        cell_tot_val.value = f"{total_horas_aluno:.1f}h ({total_min_aluno} min)"
        cell_tot_val.font = Font(name="Calibri", size=11, bold=True, color="002F6C")
        cell_tot_val.alignment = Alignment(horizontal="center", vertical="center")
        cell_tot_val.fill = PatternFill(start_color=cor_azul_claro, end_color=cor_azul_claro, fill_type="solid")
        cell_tot_val.border = thin_border

        cell_status_meta = ws.cell(row=linha_atual, column=9)
        cell_status_meta.value = "META CONCLUÍDA" if faltam_horas == 0 else f"Faltam {faltam_horas:.1f}h"
        cell_status_meta.font = Font(name="Calibri", size=10, bold=True, color="006100" if faltam_horas == 0 else "002F6C")
        cell_status_meta.alignment = Alignment(horizontal="center", vertical="center")
        cell_status_meta.fill = PatternFill(start_color=cor_azul_claro, end_color=cor_azul_claro, fill_type="solid")
        cell_status_meta.border = thin_border

        ws.row_dimensions[linha_atual].height = 24
        linha_atual += 3  # Espaço para o próximo aluno

    # Ajuste automático de largura de colunas
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

    wb.save(caminho_saida)
    print(f"[OK] Relatorio Excel exportado com sucesso: {caminho_saida.name}")


def exportar_json(resultados: List[Dict[str, Any]], caminho_saida: Path) -> None:
    """Exporta os resultados para um arquivo JSON formatado."""
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"[OK] Relatorio JSON exportado com sucesso: {caminho_saida.name}")


def exibir_tabela_terminal(resultados: List[Dict[str, Any]]) -> None:
    """Exibe um resumo visual limpo no terminal."""
    print("\n" + "=" * 90)
    print("  RELATÓRIO DE AUDITORIA DE ATIVIDADES COMPLEMENTARES - SENAI FATESG")
    print("=" * 90)
    print(f"{'Aluno':<18} | {'Evento/Curso':<25} | {'Declarado':<9} | {'Computado':<9} | {'Status':<15}")
    print("-" * 90)

    total_computadas = 0.0
    for r in resultados:
        aluno = (r.get("nome_aluno") or "Não identificado")[:18]
        evento = (r.get("nome_evento") or "Não identificado")[:25]
        decl = f"{r.get('carga_horaria_declarada') or 0}h"
        comp = f"{r.get('carga_horaria_computada') or 0}h"
        status = r.get("status_leitura", "-")

        total_computadas += float(r.get("carga_horaria_computada") or 0)
        print(f"{aluno:<18} | {evento:<25} | {decl:<9} | {comp:<9} | {status:<15}")

    print("-" * 90)
    print(f"TOTAL DE HORAS VÁLIDAS APROVADAS: {total_computadas:.1f}h")
    print("=" * 90 + "\n")


def processar_pasta(pasta: Path, auditor: AuditorCertificados) -> List[Dict[str, Any]]:
    """Processa todos os certificados suportados (.pdf, .txt, imagens) na pasta."""
    extensoes_validas = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    arquivos = [f for f in pasta.iterdir() if f.is_file() and f.suffix.lower() in extensoes_validas]

    if not arquivos:
        print(f"[AVISO] Nenhum certificado encontrado na pasta: {pasta}")
        return []

    print(f"\n[INFO] Encontrados {len(arquivos)} arquivo(s) na pasta '{pasta.name}'. Processando...")
    resultados = []

    for arq in arquivos:
        try:
            res = auditor.analisar_arquivo(arq)
            res["arquivo_origem"] = arq.name
            resultados.append(res)
            print(f" -> Processado: {arq.name} | Status: {res['status_leitura']} | Horas: {res['carga_horaria_computada']}h")
        except Exception as e:
            print(f" [ERRO] Falha ao processar {arq.name}: {e}")
            resultados.append({
                "arquivo_origem": arq.name,
                "nome_aluno": None,
                "nome_evento": None,
                "entidade_emissora": None,
                "carga_horaria_declarada": None,
                "categoria_identificada": None,
                "carga_horaria_computada": 0,
                "status_leitura": "DADOS_FALTANTES",
                "erro": str(e)
            })

    return resultados


def menu_interativo(diretorio_base: Path):
    """Interface interativa de linha de comando."""
    pasta_certificados = diretorio_base / "certificados"
    criar_pasta_certificados_se_nao_existir(pasta_certificados)
    auditor = AuditorCertificados()

    while True:
        print("\n" + "=" * 55)
        print("   SISTEMA DE AUDITORIA ACADÊMICA - SENAI FATESG")
        print("=" * 55)
        print("1. Processar todos os certificados da pasta 'certificados/'")
        print("2. Processar um arquivo específico (PDF, Imagem ou TXT)")
        print("3. Inserir/Colar texto OCR de um certificado manualmente")
        print("4. Executar bateria de testes automatizados")
        print("5. Sair")
        print("=" * 55)

        opcao = input("Escolha uma opção (1-5): ").strip()

        if opcao == "1":
            resultados = processar_pasta(pasta_certificados, auditor)
            if resultados:
                exibir_tabela_terminal(resultados)
                exportar_json(resultados, diretorio_base / "relatorio_auditoria.json")
                exportar_excel(resultados, diretorio_base / "relatorio_auditoria.xlsx")
        elif opcao == "2":
            caminho_input = input("Digite o caminho completo ou relativo do arquivo: ").strip(' "\'')
            p = Path(caminho_input)
            if not p.is_absolute():
                p = diretorio_base / p
            if not p.exists():
                print(f"[ERRO] Arquivo não encontrado: {p}")
                continue
            try:
                res = auditor.analisar_arquivo(p)
                res["arquivo_origem"] = p.name
                print("\nResultado JSON:")
                print(json.dumps(res, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"[ERRO] Falha ao ler arquivo: {e}")
        elif opcao == "3":
            print("\nCole o texto OCR abaixo (digite FIM em uma nova linha para finalizar):")
            linhas = []
            while True:
                linha = input()
                if linha.strip().upper() == "FIM":
                    break
                linhas.append(linha)
            texto_colado = "\n".join(linhas)
            res = auditor.analisar_texto(texto_colado)
            print("\nResultado JSON gerado:")
            print(json.dumps(res, ensure_ascii=False, indent=2))
        elif opcao == "4":
            print("\nExecutando testes automatizados...")
            import unittest
            import test_auditor
            suite = unittest.defaultTestLoader.loadTestsFromModule(test_auditor)
            runner = unittest.TextTestRunner(verbosity=2)
            runner.run(suite)
        elif opcao == "5":
            print("\nEncerrando o sistema. Bons estudos e boas auditorias!")
            break
        else:
            print("[ERRO] Opção inválida. Digite de 1 a 5.")


def main():
    diretorio_base = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Auditor de Certificados Acadêmicos SENAI Fatesg")
    parser.add_argument("--pasta", type=str, help="Caminho da pasta contendo os certificados para processamento em lote")
    parser.add_argument("--arquivo", type=str, help="Caminho de um arquivo específico para auditar")
    parser.add_argument("--texto", type=str, help="Texto bruto OCR diretamente na linha de comando")

    args = parser.parse_args()
    auditor = AuditorCertificados()

    if args.texto:
        resultado = auditor.analisar_texto(args.texto)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.arquivo:
        caminho = Path(args.arquivo)
        if not caminho.is_absolute():
            caminho = diretorio_base / caminho
        resultado = auditor.analisar_arquivo(caminho)
        resultado["arquivo_origem"] = caminho.name
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.pasta:
        pasta = Path(args.pasta)
        if not pasta.is_absolute():
            pasta = diretorio_base / pasta
        resultados = processar_pasta(pasta, auditor)
        if resultados:
            exibir_tabela_terminal(resultados)
            exportar_json(resultados, diretorio_base / "relatorio_auditoria.json")
            exportar_excel(resultados, diretorio_base / "relatorio_auditoria.xlsx")
        sys.exit(0)

    # Se nenhum argumento for passado via linha de comando, roda o menu interativo
    menu_interativo(diretorio_base)


if __name__ == "__main__":
    main()
