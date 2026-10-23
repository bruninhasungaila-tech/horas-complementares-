"""
Testes automatizados para o Auditor de Certificados da Faculdade SENAI Fatesg.
Valida regras de extração, cálculo e conformidade com o regulamento.
"""

import unittest
from auditor import AuditorCertificados


class TestAuditorCertificados(unittest.TestCase):

    def setUp(self):
        self.auditor = AuditorCertificados()

    def test_exemplo_semana_ia_fatesg(self):
        texto = (
            "Certificamos que João Silva participou do evento Semana de Inteligência Artificial "
            "promovido pela Fatesg.\n"
            "Carga horária: 40 horas.\n"
            "Goiânia, 15 de novembro de 2025."
        )
        res = self.auditor.analisar_texto(texto)
        self.assertEqual(res["nome_aluno"], "João Silva")
        self.assertEqual(res["nome_evento"], "Semana de Inteligência Artificial")
        self.assertEqual(res["entidade_emissora"], "Fatesg")
        self.assertEqual(res["carga_horaria_declarada"], 40)
        self.assertEqual(res["categoria_identificada"], "Participação e organização de eventos")
        self.assertEqual(res["carga_horaria_computada"], 4.0)
        self.assertEqual(res["status_leitura"], "SUCESSO")

    def test_curso_lingua_estrangeira_sucesso(self):
        texto = (
            "Certificamos que João Silva concluiu o Curso de Inglês Básico "
            "na Escola de Idiomas XYZ, com carga horária de 50 horas."
        )
        res = self.auditor.analisar_texto(texto)
        self.assertEqual(res["nome_aluno"], "João Silva")
        self.assertEqual(res["carga_horaria_declarada"], 50)
        self.assertEqual(res["categoria_identificada"], "Curso de língua estrangeira")
        self.assertEqual(res["carga_horaria_computada"], 10.0)
        self.assertEqual(res["status_leitura"], "SUCESSO")

    def test_curso_lingua_estrangeira_rejeitado(self):
        texto = (
            "Certificamos que Maria Santos concluiu o Curso de Espanhol Instrumental "
            "na Instituição ABC com carga horária de 20 horas."
        )
        res = self.auditor.analisar_texto(texto)
        self.assertEqual(res["nome_aluno"], "Maria Santos")
        self.assertEqual(res["carga_horaria_declarada"], 20)
        self.assertEqual(res["categoria_identificada"], "Curso de língua estrangeira")
        self.assertEqual(res["carga_horaria_computada"], 0.0)
        self.assertEqual(res["status_leitura"], "REJEITADO_REGULAMENTO")

    def test_curso_senai_fatesg_25_porcento(self):
        texto = (
            "Certificamos que Carlos Eduardo concluiu o minicurso de Programação Python "
            "promovido pelo SENAI Goiás. Carga horária total de 40 horas."
        )
        res = self.auditor.analisar_texto(texto)
        self.assertEqual(res["nome_aluno"], "Carlos Eduardo")
        self.assertEqual(res["entidade_emissora"], "SENAI")
        self.assertEqual(res["carga_horaria_declarada"], 40)
        self.assertEqual(res["categoria_identificada"], "Cursos/minicursos (SENAI com certificado Fatesg)")
        self.assertEqual(res["carga_horaria_computada"], 10.0)  # 25% de 40 = 10
        self.assertEqual(res["status_leitura"], "SUCESSO")

    def test_curso_outras_instituicoes_10_porcento(self):
        texto = (
            "Certificamos que Ana Clara concluiu o curso de Machine Learning "
            "na plataforma Coursera com carga horária de 100 horas."
        )
        res = self.auditor.analisar_texto(texto)
        self.assertEqual(res["nome_aluno"], "Ana Clara")
        self.assertEqual(res["entidade_emissora"], "Outras instituições")
        self.assertEqual(res["carga_horaria_declarada"], 100)
        self.assertEqual(res["categoria_identificada"], "Cursos/minicursos na área (Outras instituições)")
        self.assertEqual(res["carga_horaria_computada"], 10.0)  # 10% de 100 = 10
        self.assertEqual(res["status_leitura"], "SUCESSO")

    def test_dados_faltantes_placeholder(self):
        res = self.auditor.analisar_texto("{texto_ocr}")
        self.assertEqual(res["status_leitura"], "DADOS_FALTANTES")
        self.assertIsNone(res["nome_aluno"])
        self.assertEqual(res["carga_horaria_computada"], 0)

    def test_ouvinte_em_bancas(self):
        texto = (
            "Atestamos que Lucas Pereira participou como ouvinte em banca examinadora de TCC "
            "com carga horária de 4 horas."
        )
        res = self.auditor.analisar_texto(texto)
        self.assertEqual(res["nome_aluno"], "Lucas Pereira")
        self.assertEqual(res["categoria_identificada"], "Ouvinte em bancas (TCC/Projetos)")
        self.assertEqual(res["carga_horaria_computada"], 2.0)
        self.assertEqual(res["status_leitura"], "SUCESSO")


if __name__ == "__main__":
    unittest.main()
