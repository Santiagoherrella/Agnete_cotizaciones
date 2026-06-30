import os
import uuid
from datetime import datetime
from typing import Any

from src.agents.alineador_normativo import nodo_alineador_normativo
from src.agents.auditor_sdm import nodo_auditor_sdm
from src.grafo import maquina_magnetron
from src.schemas.state import BotState
from src.tools.exportador_sdm import nodo_generar_json_sdm
from src.tools.extractor import extraer_texto_universal


def _merge_state(state: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into state while preserving list accumulators."""
    merged = dict(state)
    for key, value in updates.items():
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = merged[key] + value
        else:
            merged[key] = value
    return merged


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_uploaded_files(uploaded_files: list[Any], run_id: str | None = None) -> tuple[str, list[str]]:
    """Persist uploaded files in a run-specific folder and return its path."""
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    target_dir = os.path.join("data", "uploads", run_id)
    _ensure_dir(target_dir)

    saved_paths: list[str] = []
    for uploaded_file in uploaded_files:
        try:
            content = uploaded_file.getbuffer()
        except Exception as e:
            raise ValueError(f"No se pudo leer el archivo cargado: {uploaded_file.name}. {e}") from e

        if len(content) == 0:
            raise ValueError(f"El archivo '{uploaded_file.name}' esta vacio o corrupto.")

        safe_name = os.path.basename(uploaded_file.name)
        destination = os.path.join(target_dir, safe_name)
        with open(destination, "wb") as output_file:
            output_file.write(content)
        saved_paths.append(destination)

    return run_id, saved_paths


def build_combined_text(file_paths: list[str]) -> str:
    """Read all uploaded files and consolidate them into a single text payload."""
    chunks: list[str] = []
    for file_path in file_paths:
        chunks.append(f"\n\n--- DOCUMENTO: {os.path.basename(file_path)} ---\n")
        chunks.append(extraer_texto_universal(file_path))
    combined = "".join(chunks).strip()
    if not combined:
        raise ValueError(
            "No se pudo extraer texto de los archivos cargados. "
            "Verifica que no esten protegidos, escaneados sin OCR o dañados."
        )
    return combined


def build_initial_state(
    file_paths: list[str],
    combined_text: str,
    requested_config: dict[str, bool],
    run_id: str,
) -> BotState:
    """Create the initial graph state used by the orchestration pipeline."""
    ejecutar_sdm = requested_config.get("ejecutar_sdm", False)
    ejecutar_ingenieria = requested_config.get("ejecutar_ingenieria", True)
    ejecutar_comercial = requested_config.get("ejecutar_comercial", True)

    # The main graph skips SDM for web runs; SDM is executed in a controlled post-step.
    config_for_graph = {
        "ejecutar_ingenieria": ejecutar_ingenieria,
        "ejecutar_comercial": ejecutar_comercial,
        "ejecutar_sdm": False,
        "ejecutar_documentos_tecnicos": requested_config.get("ejecutar_documentos_tecnicos", True),
        "ejecutar_ctg": requested_config.get("ejecutar_ctg", True),
        "solicitar_sdm_al_final": ejecutar_sdm,
    }

    return {
        "run_id": run_id,
        "modo_interaccion": "web",
        "respuestas_humanas": {},
        "archivos_entrada": file_paths,
        "configuracion": config_for_graph,
        "ruta_documento": run_id,
        "texto_extraido": combined_text,
        "inventario_global": [],
        "ruta_excel_inventario": "",
        "cliente_identificado": "",
        "item_actual_id": "",
        "datos_electricos": {},
        "datos_mecanicos": {},
        "datos_accesorios": {},
        "datos_logisticos": {},
        "intentos_electrico": 0,
        "intentos_mecanico": 0,
        "intentos_accesorios": 0,
        "intentos_logistico": 0,
        "feedback_electrico": "",
        "feedback_mecanico": "",
        "feedback_accesorios": "",
        "feedback_logistico": "",
        "errores_extraccion": [],
        "alertas_diseno": [],
        "auditoria_sdm_ok": False,
        "campos_faltantes_sdm": [],
        "datos_normalizados_sdm": {},
        "resumen_comercial_ejecutivo": "",
        "tabla_comercial_checklist": "",
        "resumenes_completados": [],
        "fichas_tecnicas_finales": [],
        "rutas_fichas_word": [],
        "rutas_tablas_ctg": [],
        "rutas_sdm_json": [],
    }


def run_main_graph(initial_state: BotState) -> dict[str, Any]:
    """Execute the existing LangGraph flow for engineering/commercial stages."""
    return maquina_magnetron.invoke(initial_state)


def run_sdm_stage(state: dict[str, Any], human_answers: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Execute the SDM post-stage outside the main graph.
    """
    current_state = dict(state)

    current_state = _merge_state(current_state, nodo_alineador_normativo(current_state))
    current_state = _merge_state(current_state, nodo_auditor_sdm(current_state))
    current_state = _merge_state(current_state, nodo_generar_json_sdm(current_state))

    return {
        "status": "completed",
        "state": current_state,
        "missing_fields": [],
    }


def classify_artifacts(state: dict[str, Any]) -> dict[str, list[str] | str]:
    """Split generated artifacts into UI-friendly buckets."""
    def unique_paths(paths: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for path in paths:
            if path and path not in seen:
                seen.add(path)
                ordered.append(path)
        return ordered

    artifacts = {
        "inventario_excel": state.get("ruta_excel_inventario", ""),
        "word_tecnico": [],
        "word_comercial": [],
        "excel_ctg": [],
        "excel_comercial": [],
        "json_sdm": state.get("rutas_sdm_json", []),
    }

    for path in state.get("rutas_fichas_word", []):
        name = os.path.basename(path).lower()
        if "resumen_comercial" in name:
            artifacts["word_comercial"].append(path)
        else:
            artifacts["word_tecnico"].append(path)

    for path in state.get("rutas_tablas_ctg", []):
        name = os.path.basename(path).lower()
        if "checklist_comercial" in name:
            artifacts["excel_comercial"].append(path)
        else:
            artifacts["excel_ctg"].append(path)

    artifacts["word_tecnico"] = unique_paths(artifacts["word_tecnico"])
    artifacts["word_comercial"] = unique_paths(artifacts["word_comercial"])
    artifacts["excel_ctg"] = unique_paths(artifacts["excel_ctg"])
    artifacts["excel_comercial"] = unique_paths(artifacts["excel_comercial"])
    artifacts["json_sdm"] = unique_paths(artifacts["json_sdm"])

    return artifacts


def summarize_result(state: dict[str, Any], status: str) -> dict[str, Any]:
    """Create a compact summary for the Streamlit frontend."""
    inventory = state.get("inventario_global", [])
    return {
        "status": status,
        "run_id": state.get("run_id", ""),
        "cliente": state.get("cliente_identificado", ""),
        "familias_procesadas": state.get("resumenes_completados", []),
        "total_items_inventario": len(inventory),
        "alertas": state.get("alertas_diseno", []),
        "faltantes_sdm": state.get("campos_faltantes_sdm", []),
        "artifacts": classify_artifacts(state),
    }


def run_pipeline_from_uploads(uploaded_files: list[Any], requested_config: dict[str, bool]) -> dict[str, Any]:
    """Entry point for the Streamlit app."""
    if not uploaded_files:
        raise ValueError("Debes cargar al menos un archivo para ejecutar el flujo.")

    if requested_config.get("ejecutar_sdm") and not requested_config.get("ejecutar_ingenieria"):
        raise ValueError("La fase SDM requiere ejecutar primero la fase de ingenieria.")

    run_id, saved_paths = save_uploaded_files(uploaded_files)
    combined_text = build_combined_text(saved_paths)
    initial_state = build_initial_state(saved_paths, combined_text, requested_config, run_id)
    final_state = run_main_graph(initial_state)

    if requested_config.get("ejecutar_sdm"):
        sdm_result = run_sdm_stage(final_state)
        final_state = sdm_result["state"]
        status = sdm_result["status"]
        missing_fields = sdm_result["missing_fields"]
    else:
        status = "completed"
        missing_fields = []

    return {
        "status": status,
        "state": final_state,
        "summary": summarize_result(final_state, status),
        "missing_fields": missing_fields,
    }


def resume_sdm_from_human_input(state: dict[str, Any], human_answers: dict[str, str]) -> dict[str, Any]:
    """Resume the SDM stage after the user completes the missing technical fields."""
    if not human_answers:
        raise ValueError("Debes ingresar al menos un valor para reanudar la fase SDM.")

    sdm_result = run_sdm_stage(state, human_answers)
    final_state = sdm_result["state"]

    return {
        "status": sdm_result["status"],
        "state": final_state,
        "summary": summarize_result(final_state, sdm_result["status"]),
        "missing_fields": sdm_result["missing_fields"],
    }
