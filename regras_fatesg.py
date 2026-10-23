"""
Regras oficiais de Atividades Complementares - Faculdade SENAI Fatesg.
Define categorias, critérios de cálculo de carga horária e validações de regulamento.
"""

from typing import Dict, Any, Optional, Tuple

CATEGORIAS = {
    "Seminários/Simpósios (Outras instituições)": {
        "tipo": "fixo",
        "valor": 1.0,
        "minimo_exigido": None,
    },
    "Seminários/Simpósios (Fatesg)": {
        "tipo": "fixo",
        "valor": 2.0,
        "minimo_exigido": None,
    },
    "Cursos de acessibilidade e inclusão": {
        "tipo": "fixo",
        "valor": 20.0,
        "minimo_exigido": None,
    },
    "Monitoria Acadêmica": {
        "tipo": "fixo",
        "valor": 30.0,
        "minimo_exigido": None,
    },
    "Visita Técnica": {
        "tipo": "fixo",
        "valor": 2.0,
        "minimo_exigido": None,
    },
    "Visita em Feiras": {
        "tipo": "fixo",
        "valor": 4.0,
        "minimo_exigido": None,
    },
    "Ministrante de Curso": {
        "tipo": "fixo",
        "valor": 20.0,
        "minimo_exigido": None,
    },
    "Pesquisa ou Iniciação Científica": {
        "tipo": "fixo",
        "valor": 30.0,
        "minimo_exigido": None,
    },
    "Apresentação oral em eventos técnicos": {
        "tipo": "fixo",
        "valor": 2.0,
        "minimo_exigido": None,
    },
    "Participação e organização de eventos": {
        "tipo": "fixo",
        "valor": 4.0,
        "minimo_exigido": None,
    },
    "Congressos (Fatesg)": {
        "tipo": "fixo",
        "valor": 4.0,
        "minimo_exigido": None,
    },
    "Congressos (Outras instituições)": {
        "tipo": "fixo",
        "valor": 2.0,
        "minimo_exigido": None,
    },
    "Cursos/minicursos na área (Outras instituições)": {
        "tipo": "percentual",
        "fator": 0.10,  # 10% da carga horária declarada
        "minimo_exigido": None,
    },
    "Cursos/minicursos (SENAI com certificado Fatesg)": {
        "tipo": "percentual",
        "fator": 0.25,  # 25% da carga horária declarada
        "minimo_exigido": None,
    },
    "Curso de língua estrangeira": {
        "tipo": "fixo",
        "valor": 10.0,
        "minimo_exigido": 40.0,  # Exige mínimo de 40h declaradas
    },
    "Ouvinte em bancas (TCC/Projetos)": {
        "tipo": "fixo",
        "valor": 2.0,
        "minimo_exigido": None,
    },
}


def calcular_horas(categoria: str, horas_declaradas: Optional[float]) -> Tuple[float, str]:
    """
    Calcula as horas complementares válidas de acordo com a categoria e carga horária declarada.
    Retorna (horas_computadas, status_validacao).
    """
    if not categoria or categoria not in CATEGORIAS:
        return 0.0, "DADOS_FALTANTES"

    regra = CATEGORIAS[categoria]

    if horas_declaradas is None or horas_declaradas <= 0:
        return 0.0, "DADOS_FALTANTES"

    # Verificar mínimo exigido
    minimo = regra.get("minimo_exigido")
    if minimo is not None and horas_declaradas < minimo:
        return 0.0, "REJEITADO_REGULAMENTO"

    tipo = regra["tipo"]
    if tipo == "fixo":
        horas_computadas = float(regra["valor"])
    elif tipo == "percentual":
        horas_computadas = round(horas_declaradas * regra["fator"], 2)
        if horas_computadas.is_integer():
            horas_computadas = int(horas_computadas)
    else:
        horas_computadas = 0.0

    return horas_computadas, "SUCESSO"

def formatar_tempo(horas: Optional[float]) -> Dict[str, Any]:
    """Converte horas decimais em minutos inteiros e representação textual legível."""
    if horas is None or horas <= 0:
        return {
            "horas_decimal": 0.0,
            "minutos": 0,
            "texto_legivel": "0 minutos",
            "resumo": "0h (0 min)",
        }

    total_minutos = int(round(horas * 60))
    h = total_minutos // 60
    m = total_minutos % 60

    if h == 0:
        texto = f"{m} minuto{'s' if m != 1 else ''}"
        resumo = f"{horas}h ({m} min)"
    elif m == 0:
        texto = f"{h} hora{'s' if h != 1 else ''}"
        resumo = f"{h}h ({total_minutos} min)"
    else:
        texto = f"{h}h {m}min ({h} hora{'s' if h != 1 else ''} e {m} minuto{'s' if m != 1 else ''})"
        resumo = f"{horas}h ({total_minutos} min)"

    return {
        "horas_decimal": horas,
        "minutos": total_minutos,
        "texto_legivel": texto,
        "resumo": resumo,
    }


def detalhar_computo(categoria: str, horas_declaradas: Optional[float]) -> Dict[str, Any]:
    """Retorna o cômputo detalhado com minutos, horas decimais e texto explicativo."""
    horas_comp, status = calcular_horas(categoria, horas_declaradas)
    info_tempo = formatar_tempo(horas_comp)

    explicacao = ""
    if status == "DADOS_FALTANTES":
        explicacao = "Dados vitais incompletos para cálculo."
    elif status == "REJEITADO_REGULAMENTO":
        minimo = CATEGORIAS.get(categoria, {}).get("minimo_exigido", 0)
        explicacao = f"Rejeitado: carga declarada ({horas_declaradas or 0}h) inferior ao mínimo de {minimo}h."
    else:
        regra = CATEGORIAS.get(categoria, {})
        if regra.get("tipo") == "percentual":
            pct = int(regra["fator"] * 100)
            explicacao = (
                f"Foram contados {info_tempo['texto_legivel']} ({horas_comp}h) "
                f"das {horas_declaradas}h declaradas ({pct}% de {horas_declaradas}h)."
            )
        else:
            explicacao = (
                f"Foram contados {info_tempo['texto_legivel']} ({horas_comp}h) "
                f"conforme valor fixo do regulamento."
            )

    return {
        "horas_computadas": horas_comp,
        "status_leitura": status,
        "minutos_computados": info_tempo["minutos"],
        "tempo_formatado": info_tempo["texto_legivel"],
        "tempo_resumo": info_tempo["resumo"],
        "explicacao_calculo": explicacao,
    }
