"""
Motor de extração de texto, classificação acadêmica e auditoria para a Faculdade SENAI Fatesg.
Suporta leitura direta de arquivos PDF, Imagens (OCR) e Texto puro.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

from regras_fatesg import CATEGORIAS, calcular_horas, formatar_tempo, detalhar_computo

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


class AuditorCertificados:
    """Auditor acadêmico para validação e cômputo de horas complementares."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd and PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        elif PYTESSERACT_AVAILABLE:
            # Tentar caminhos padrão do Tesseract no Windows se não estiver no PATH
            padroes = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            ]
            for p in padroes:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def extrair_texto_arquivo(self, caminho_arquivo: Union[str, Path]) -> str:
        """
        Extrai o texto bruto do arquivo fornecido (.pdf, .txt, .png, .jpg, .jpeg).
        """
        caminho = Path(caminho_arquivo)
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        ext = caminho.suffix.lower()

        if ext == ".txt":
            return caminho.read_text(encoding="utf-8", errors="ignore")

        if ext == ".pdf":
            if not PYPDF_AVAILABLE:
                raise ImportError("Biblioteca 'pypdf' não instalada. Execute: pip install pypdf")
            reader = PdfReader(str(caminho))
            texto = ""
            for pagina in reader.pages:
                texto_pag = pagina.extract_text() or ""
                texto += texto_pag + "\n"
            return texto.strip()

        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]:
            if not PYTESSERACT_AVAILABLE:
                raise ImportError(
                    "Biblioteca 'pillow' e/ou 'pytesseract' não instaladas. "
                    "Execute: pip install pillow pytesseract"
                )
            imagem = Image.open(str(caminho))
            try:
                texto = pytesseract.image_to_string(imagem, lang="por")
            except Exception:
                # Tenta sem especificar idioma se der erro com 'por'
                texto = pytesseract.image_to_string(imagem)
            return texto.strip()

        raise ValueError(f"Extensão de arquivo não suportada: {ext}. Use .pdf, .txt ou imagens (.png, .jpg)")

    def extrair_nome_aluno(self, texto: str) -> Optional[str]:
        """Extrai o nome do aluno usando padrões formais de certificados, tolerando quebras de linha."""
        # Normalizar quebras de linha e múltiplos espaços para não quebrar nomes compostos divididos em linhas
        texto_norm = re.sub(r"[ \t]*\r?\n[ \t]*", " ", texto)
        texto_norm = re.sub(r"\s+", " ", texto_norm).strip()

        verbos_parada = (
            r"(?:\s+(?:pela\s+conclusão|pela\s+conclusao|pela\s+participação|pela\s+participacao|"
            r"pela|pelo|para|participou|concluiu|ministrou|realizou|frequentou|compareceu|"
            r"apresentou|atuou|obteve|cumpriu|portador\(?a\)?|inscrito\(?a\)?|sob|"
            r"cpf|rg|nascido\(?a\)?|durante|no\s+período|no\s+periodo|com\s+aproveitamento|"
            r"na\s+qualidade|como|pelo|na|no|em)\b|[,\.;])"
        )

        padroes = [
            rf"certificamos\s+que\s+([^,\.;]+?){verbos_parada}",
            rf"declaramos\s+que\s+([^,\.;]+?){verbos_parada}",
            rf"atestamos\s+que\s+([^,\.;]+?){verbos_parada}",
            rf"confere(?:\s+o\s+presente\s+certificado)?\s+a\s+([^,\.;]+?){verbos_parada}",
            rf"conferido(?:\s+o\s+presente\s+certificado)?\s+a\s+([^,\.;]+?){verbos_parada}",
            rf"outorga(?:\s+o\s+presente\s+certificado)?\s+a\s+([^,\.;]+?){verbos_parada}",
            rf"(?:aluno|participante|estudante|nome)(?:\(a\))?:\s*([^,\.;]+?){verbos_parada}",
            rf"(?:aluno|participante|estudante|nome)(?:\(a\))?:\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõçA-ZÁÉÍÓÚÂÊÔÃÕÇ\s']+)",
        ]

        for padrao in padroes:
            match = re.search(padrao, texto_norm, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                # Limpar eventuais pontuações ou resíduos
                nome = re.sub(r"[\.,;]+$", "", nome).strip()
                # Validar tamanho razoável de nome (mínimo 2 palavras ou 5 caracteres)
                if len(nome) >= 4 and not re.search(r"\b(curso|evento|horas|fatesg|senai)\b", nome, re.IGNORECASE):
                    return nome
        return None

    def extrair_cpf_aluno(self, texto: str) -> Optional[str]:
        """Extrai o CPF do aluno se presente no texto do documento."""
        padroes = [
            r"(?:cpf|sob\s+o\s+n[ºo]|n[ºo]\s+de\s+cpf|inscrito\(?a\)?\s+no\s+cpf)[\s:]*([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})",
            r"\b([0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2})\b",
            r"\bcpf[\s:]*([0-9]{11})\b",
        ]
        for padrao in padroes:
            m = re.search(padrao, texto, re.IGNORECASE)
            if m:
                cpf_raw = re.sub(r"\D", "", m.group(1))
                if len(cpf_raw) == 11:
                    return f"{cpf_raw[:3]}.{cpf_raw[3:6]}.{cpf_raw[6:9]}-{cpf_raw[9:]}"
        return None

    def extrair_entidade_emissora(self, texto: str) -> str:
        """Identifica se é 'Fatesg', 'SENAI' ou 'Outras instituições'."""
        texto_lower = texto.lower()
        tem_fatesg = "fatesg" in texto_lower
        tem_senai = "senai" in texto_lower

        if tem_fatesg:
            return "Fatesg"
        elif tem_senai:
            return "SENAI"
        return "Outras instituições"

    def extrair_carga_horaria_declarada(self, texto: str) -> Optional[int]:
        """Extrai a carga horária impressa no documento (apenas número inteiro)."""
        padroes = [
            r"carga\s+hor[áa]ria(?:\s+total)?(?:\s+de)?:\s*(\d+)",
            r"com\s+dura[çc][ãa]o\s+(?:total\s+)?de\s*(\d+)\s*(?:horas|hora|h\b|hrs)",
            r"totalizando\s*(\d+)\s*(?:horas|hora|h\b|hrs)",
            r"cumprindo\s*(\d+)\s*(?:horas|hora|h\b|hrs)",
            r"(\d+)\s*(?:horas|hora|hrs)\b",
            r"(\d+)\s*h\b",
        ]

        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def extrair_nome_evento(self, texto: str) -> Optional[str]:
        """Extrai o título do curso, evento, palestra ou atividade."""
        texto_norm = re.sub(r"[ \t]*\r?\n[ \t]*", " ", texto)
        texto_norm = re.sub(r"\s+", " ", texto_norm).strip()

        delimitadores_parada = (
            r"(?:\s+promovido|\s+realizado|\s+no\s+dia|\s+com\s+carga|\s+com\s+dura[çc][ãa]o|"
            r"\s+ministrado|\s+concluído|\s+concluido|[,\.;]|$)"
        )

        padroes = [
            rf"participou\s+do\s+evento\s+[\"“']?([^,\.;]+?)[\"”']?{delimitadores_parada}",
            rf"concluiu\s+o\s+curso\s+(?:de\s+)?[\"“']?([^,\.;]+?)[\"”']?{delimitadores_parada}",
            rf"participou\s+d[ao]\s+[\"“']?([^,\.;]+?)[\"”']?{delimitadores_parada}",
            rf"ministrou\s+(?:o\s+curso|a\s+palestra|o\s+minicurso)\s+(?:de\s+)?[\"“']?([^,\.;]+?)[\"”']?{delimitadores_parada}",
            rf"curso(?:\s+de)?\s+[\"“']?([^,\.;]+?)[\"”']?{delimitadores_parada}",
            rf"evento\s+[\"“']?([^,\.;]+?)[\"”']?{delimitadores_parada}",
        ]

        for padrao in padroes:
            match = re.search(padrao, texto_norm, re.IGNORECASE)
            if match:
                evento = match.group(1).strip()
                evento = re.sub(r"^[\"“']|[\"”']$", "", evento)
                evento = re.sub(r"[\.,;]+$", "", evento).strip()
                if len(evento) >= 3:
                    return evento

        # Padrão estrito para eventos no formato 'Semana de...'
        match_semana = re.search(r"\b(Semana\s+de\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõçA-ZÁÉÍÓÚÂÊÔÃÕÇ\s]+?)(?=\s+promovido|\s+realizado|\s+com\s+carga|[,\.\n\r]|$)", texto_norm, re.IGNORECASE)
        if match_semana:
            return match_semana.group(1).strip()

        return None

    def classificar_categoria(self, texto: str, entidade: str) -> Optional[str]:
        """Classifica a atividade em uma das 16 categorias oficiais da Fatesg."""
        t = texto.lower()
        eh_fatesg = (entidade == "Fatesg")
        eh_senai = (entidade == "SENAI")

        # 1. Ouvinte em bancas
        if any(k in t for k in ["ouvinte em banca", "banca examinadora", "banca de tcc", "banca avaliadora"]):
            return "Ouvinte em bancas (TCC/Projetos)"

        # 2. Monitoria Acadêmica
        if any(k in t for k in ["monitoria acadêmica", "monitoria academica", "atuou como monitor", "programa de monitoria"]):
            return "Monitoria Acadêmica"

        # 3. Pesquisa ou Iniciação Científica
        if any(k in t for k in ["iniciação científica", "iniciacao cientifica", "pibic", "pesquisa científica", "pesquisa cientifica"]):
            return "Pesquisa ou Iniciação Científica"

        # 4. Ministrante de Curso
        if any(k in t for k in ["ministrante", "como ministrante", "ministrou o curso", "ministrou a palestra", "na qualidade de instrutor"]):
            return "Ministrante de Curso"

        # 5. Apresentação oral em eventos técnicos
        if any(k in t for k in ["apresentação oral", "apresentou oralmente", "apresentação de trabalho", "apresentação de artigo", "apresentou o artigo"]):
            return "Apresentação oral em eventos técnicos"

        # 6. Visita Técnica
        if "visita técnica" in t or "visita tecnica" in t:
            return "Visita Técnica"

        # 7. Visita em Feiras
        if any(k in t for k in ["visita em feira", "visita à feira", "visita a feira", "feira de tecnologia", "feira de negócios"]):
            return "Visita em Feiras"

        # 8. Cursos de acessibilidade e inclusão
        if any(k in t for k in ["acessibilidade", "inclusão", "inclusao", "libras", "braille", "tecnologia assistiva"]):
            return "Cursos de acessibilidade e inclusão"

        # 9. Curso de língua estrangeira
        if any(k in t for k in ["língua estrangeira", "lingua estrangeira", "inglês", "ingles", "espanhol", "idiomas", "idioma", "french", "francês", "english"]):
            return "Curso de língua estrangeira"

        # 10. Congressos
        if "congresso" in t:
            return "Congressos (Fatesg)" if eh_fatesg else "Congressos (Outras instituições)"

        # 11. Seminários/Simpósios
        if any(k in t for k in ["seminário", "seminario", "simpósio", "simposio"]):
            return "Seminários/Simpósios (Fatesg)" if eh_fatesg else "Seminários/Simpósios (Outras instituições)"

        # 12. Cursos/minicursos
        if any(k in t for k in ["curso", "minicurso", "capacitação", "capacitacao", "treinamento", "workshop", "bootcamp"]):
            if eh_senai or eh_fatesg:
                return "Cursos/minicursos (SENAI com certificado Fatesg)"
            else:
                return "Cursos/minicursos na área (Outras instituições)"

        # 13. Participação e organização de eventos
        if any(k in t for k in ["evento", "semana", "jornada", "encontro", "participou", "organização de evento", "participação"]):
            return "Participação e organização de eventos"

        return None

    def analisar_texto(self, texto: str) -> Dict[str, Any]:
        """
        Executa a auditoria acadêmica completa sobre o texto OCR ou extraído.
        Retorna o dicionário exatamente no formato exigido pelo regulamento.
        """
        if not texto or not texto.strip() or texto.strip() == "{texto_ocr}":
            return {
                "nome_aluno": None,
                "cpf_aluno": None,
                "nome_evento": None,
                "entidade_emissora": None,
                "carga_horaria_declarada": None,
                "categoria_identificada": None,
                "carga_horaria_computada": 0,
                "minutos_computados": 0,
                "tempo_formatado": "0 minutos",
                "explicacao_calculo": "Dados vitais ausentes ou ilegíveis.",
                "status_leitura": "DADOS_FALTANTES",
            }

        nome_aluno = self.extrair_nome_aluno(texto)
        cpf_aluno = self.extrair_cpf_aluno(texto)
        nome_evento = self.extrair_nome_evento(texto)
        entidade = self.extrair_entidade_emissora(texto)
        horas_declaradas = self.extrair_carga_horaria_declarada(texto)
        categoria = self.classificar_categoria(texto, entidade)

        # Se campos vitais estiverem ausentes
        if not nome_aluno or horas_declaradas is None or not categoria:
            status = "DADOS_FALTANTES"
            horas_computadas = 0
            if not nome_aluno and horas_declaradas is None:
                entidade = None
            minutos = 0
            tempo_fmt = "0 minutos"
            explicacao = "Dados vitais ausentes ou ilegíveis no certificado."
        else:
            info_det = detalhar_computo(categoria, float(horas_declaradas))
            horas_computadas = info_det["horas_computadas"]
            status = info_det["status_leitura"]
            minutos = info_det["minutos_computados"]
            tempo_fmt = info_det["tempo_formatado"]
            explicacao = info_det["explicacao_calculo"]

        return {
            "nome_aluno": nome_aluno,
            "cpf_aluno": cpf_aluno,
            "nome_evento": nome_evento,
            "entidade_emissora": entidade,
            "carga_horaria_declarada": horas_declaradas,
            "categoria_identificada": categoria,
            "carga_horaria_computada": horas_computadas,
            "minutos_computados": minutos,
            "tempo_formatado": tempo_fmt,
            "explicacao_calculo": explicacao,
            "status_leitura": status,
        }

    def analisar_arquivo(self, caminho_arquivo: Union[str, Path]) -> Dict[str, Any]:
        """Extrai o texto do arquivo e executa a auditoria acadêmica."""
        texto = self.extrair_texto_arquivo(caminho_arquivo)
        return self.analisar_texto(texto)
