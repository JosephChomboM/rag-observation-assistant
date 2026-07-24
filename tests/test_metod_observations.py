import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from openpyxl import Workbook

from metod_observations.config import load_config
from metod_observations.excel_loader import load_pruebas_from_excel
from metod_observations.knowledge_builder import build_knowledge_from_pruebas
from metod_observations.observation_generator import validate_observation_payload
from metod_observations.pipeline import run_observation_pipeline

TEMP_ROOT = Path(os.getenv("SOFTIA_TEST_TMP", r"C:\tmp"))
TEMP_ROOT.mkdir(parents=True, exist_ok=True)

class FakeModelClient:
    embedding_deployment = "fake-embedding"

    def embed_text(self, text):
        lower = text.lower()
        return [
            float(lower.count("universo")),
            float(lower.count("duplic")),
            float(lower.count("script")),
            float(len(text) % 97),
        ]

    def chat_json(self, prompt, image_data_urls=None, max_tokens=1800, temperature=0.1):
        return json.dumps(
            {
                "hay_observacion": True,
                "criticidad": "Moderado",
                "observacion": "Se identifica un hallazgo consolidado de prueba.",
                "sustento": "La evidencia recuperada sustenta el hallazgo.",
                "controles_evaluados": ["BBDD1_P01_C01", "BBDD1_P01_C02"],
                "controles_que_originan_observacion": ["BBDD1_P01_C02"],
                "evidencias_usadas": [
                    {"archivo": "evidencia_universo.txt", "chunk_id": "BBDD1_E0001_C001", "score": 0.9}
                ],
                "informacion_faltante": [],
            }
        )


def build_sample_excel(path: Path):
    workbook = Workbook()
    ws = workbook.active
    ws.title = "BBDD 1"
    ws.append(["Detalle_prueba", "Detalle", "Prompt", "Limites", "Criticidad", "Excepciones"])
    ws.append(
        [
            "Replica del proceso de extraccion del universo",
            "Se puede ejecutar sin errores el script",
            "Revisar continuidad del script",
            "0 errores",
            ">0 errores criticidad Moderado",
            "Sin excepciones",
        ]
    )
    ws.append(
        [
            "",
            "No existen duplicados en bases intermedias",
            "Revisar reportes de duplicados",
            "0.01% duplicados",
            ">0.01% criticidad Moderado",
            "Sin excepciones",
        ]
    )
    ws.append(
        [
            "Reconstruccion del proceso de extraccion del universo",
            "El universo reconstruido coincide al 99%",
            "Revisar coincidencia",
            "No menor a 99%",
            "<99% criticidad Moderado",
            "Sin excepciones",
        ]
    )
    workbook.save(path)


class MetodObservationTests(unittest.TestCase):
    def test_excel_loader_forward_fills_prueba_and_builds_control_ids(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            excel_path = Path(temp_dir) / "admin.xlsx"
            build_sample_excel(excel_path)

            pruebas_by_metod = load_pruebas_from_excel(excel_path)
            pruebas = pruebas_by_metod["BBDD1"]

            self.assertEqual(len(pruebas), 2)
            self.assertEqual(pruebas[0].prueba_id, "BBDD1_P01")
            self.assertEqual(len(pruebas[0].controls), 2)
            self.assertEqual(pruebas[0].controls[1].control_id, "BBDD1_P01_C02")

    def test_knowledge_builder_generates_one_markdown_per_prueba(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            excel_path = Path(temp_dir) / "admin.xlsx"
            build_sample_excel(excel_path)
            pruebas = load_pruebas_from_excel(excel_path)["BBDD1"]

            manifest = build_knowledge_from_pruebas(pruebas, temp_dir)

            self.assertEqual(manifest["pruebas_count"], 2)
            self.assertEqual(manifest["controls_count"], 3)
            markdowns = list((Path(temp_dir) / "BBDD1" / "pruebas").glob("*.md"))
            self.assertEqual(len(markdowns), 2)
            self.assertIn("## Control BBDD1_P01_C01", markdowns[0].read_text(encoding="utf-8"))

    def test_invalid_criticality_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            excel_path = Path(temp_dir) / "admin.xlsx"
            build_sample_excel(excel_path)
            prueba = load_pruebas_from_excel(excel_path)["BBDD1"][0]

            with self.assertRaises(ValueError):
                validate_observation_payload(
                    {
                        "hay_observacion": True,
                        "criticidad": "Media",
                        "observacion": "x",
                    },
                    prueba,
                )

    def test_pipeline_runs_per_prueba_with_fake_model(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            base = Path(temp_dir)
            excel_path = base / "admin.xlsx"
            knowledge_dir = base / "knowledge"
            workspace_dir = base / "workspace"
            build_sample_excel(excel_path)
            pruebas = load_pruebas_from_excel(excel_path)["BBDD1"]
            build_knowledge_from_pruebas(pruebas, knowledge_dir)

            shared = knowledge_dir / "_shared"
            shared.mkdir(parents=True)
            (shared / "glossary_data.json").write_text(
                json.dumps(
                    [
                        {
                            "term": "Universo",
                            "definition": "Poblacion objetivo del proceso.",
                            "aliases": ["poblacion objetivo"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            input_dir = workspace_dir / "inputs" / "BBDD1"
            input_dir.mkdir(parents=True)
            (input_dir / "evidencia_universo.txt").write_text(
                "El script del universo no presenta errores y el reporte no muestra duplicados.",
                encoding="utf-8",
            )

            config = replace(
                load_config(),
                knowledge_base_dir=str(knowledge_dir),
                inputs_base_dir=str(workspace_dir / "inputs"),
                indexes_base_dir=str(workspace_dir / "indexes"),
                outputs_base_dir=str(workspace_dir / "outputs" / "generated_observations"),
                embedding_deployment="fake-embedding",
            )

            result = run_observation_pipeline(
                "BBDD1",
                config=config,
                rebuild_evidence_index=True,
                model_client=FakeModelClient(),
            )

            self.assertEqual(result["usage_summary"]["llm_generation_requests"], 2)
            self.assertEqual(len(result["observations"]), 2)
            self.assertTrue(Path(result["output_paths"]["json"]).exists())
            self.assertTrue(Path(result["output_paths"]["markdown"]).exists())


if __name__ == "__main__":
    unittest.main()

