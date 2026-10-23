# Sistema de Auditoria Acadêmica de Atividades Complementares
### Faculdade SENAI Fatesg

Sistema em **Python** desenvolvido para analisar textos brutos e certificados (extraídos via OCR ou arquivos PDF/imagens), classificar as atividades de acordo com o **Regulamento Oficial de Atividades Complementares da Faculdade SENAI Fatesg** e calcular automaticamente a carga horária computada.

---

## Estrutura do Projeto

- **[regras_fatesg.py](file:///c:/Users/Aluno/Desktop/horas%20complementares/regras_fatesg.py)**: Tabela de regras oficiais, categorias da Fatesg, fatores de cômputo (horas fixas e percentuais) e validação de requisitos mínimos.
- **[auditor.py](file:///c:/Users/Aluno/Desktop/horas%20complementares/auditor.py)**: Motor de extração de texto (PDF nativo com `pypdf`, imagens com `pytesseract` e texto bruto) e inteligência de classificação para gerar o JSON estrito.
- **[main.py](file:///c:/Users/Aluno/Desktop/horas%20complementares/main.py)**: Script executável principal com menu interativo, processamento em lote e exportação de relatórios.
- **[test_auditor.py](file:///c:/Users/Aluno/Desktop/horas%20complementares/test_auditor.py)**: Bateria de testes unitários automatizados validando todos os cenários e regras.
- **`certificados/`**: Pasta onde você pode colocar seus arquivos de certificados (`.pdf`, `.png`, `.jpg`, `.txt`).
- **`relatorio_auditoria.xlsx`**: Planilha Excel gerada automaticamente com design institucional e total de horas aprovadas.
- **`relatorio_auditoria.json`**: Relatório em formato JSON com todos os dados estruturados.

---

## Regras de Classificação e Cômputo Implementadas

| Categoria | Regra de Cômputo |
| :--- | :--- |
| **Seminários/Simpósios (Outras instituições)** | Computar 1h |
| **Seminários/Simpósios (Fatesg)** | Computar 2h |
| **Cursos de acessibilidade e inclusão** | Computar 20h |
| **Monitoria Acadêmica** | Computar 30h |
| **Visita Técnica** | Computar 2h |
| **Visita em Feiras** | Computar 4h |
| **Ministrante de Curso** | Computar 20h |
| **Pesquisa ou Iniciação Científica** | Computar 30h |
| **Apresentação oral em eventos técnicos** | Computar 2h |
| **Participação e organização de eventos** | Computar 4h |
| **Congressos (Fatesg)** | Computar 4h |
| **Congressos (Outras instituições)** | Computar 2h |
| **Cursos/minicursos na área (Outras instituições)** | Computar 10% da carga horária declarada |
| **Cursos/minicursos (SENAI com certificado Fatesg)** | Computar 25% da carga horária declarada |
| **Curso de língua estrangeira** | Computar 10h *(Mínimo exigido: 40h declaradas)* |
| **Ouvinte em bancas (TCC/Projetos)** | Computar 2h |

---

## Como Usar

### 1. Modo Interativo (Menu no Terminal)
Basta executar:
```bash
python main.py
```
O menu permite escolher entre auditar a pasta de certificados, processar um arquivo específico ou colar o texto OCR diretamente.

### 2. Processar a pasta de certificados em lote
Coloque seus arquivos PDF ou imagens na pasta `certificados/` e execute:
```bash
python main.py --pasta certificados
```

### 3. Auditar texto diretamente via linha de comando
```bash
python main.py --texto "Certificamos que João Silva participou do evento Semana de Inteligência Artificial promovido pela Fatesg. Carga horária: 40 horas."
```

### 4. Executar os Testes Unitários
```bash
python -m unittest test_auditor.py
```
