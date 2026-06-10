# streamlit run streamlit_app.py
import os

import pandas as pd
import streamlit as st

from src.services.pipeline_service import (
    resume_sdm_from_human_input,
    run_pipeline_from_uploads,
)


st.set_page_config(
    page_title="Magnetron Orquestador de Cotizaciones",
    page_icon=":material/account_tree:",
    layout="wide",
)


def _init_session_state() -> None:
    defaults = {
        "workflow_result": None,
        "backend_state": None,
        "pending_fields": [],
        "uploader_key": 0,
        "cfg_ingenieria": True,
        "cfg_comercial": True,
        "cfg_sdm": False,
        "cfg_documentos_tecnicos": True,
        "cfg_ctg": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _enforce_sdm_dependency() -> None:
    if st.session_state.get("cfg_sdm"):
        st.session_state["cfg_ingenieria"] = True


def _reset_quote_ui() -> None:
    st.session_state["workflow_result"] = None
    st.session_state["backend_state"] = None
    st.session_state["pending_fields"] = []
    st.session_state["uploader_key"] = int(st.session_state.get("uploader_key", 0)) + 1


def _read_binary_file(file_path: str) -> bytes:
    with open(file_path, "rb") as file_handle:
        return file_handle.read()


def _render_download_button(file_path: str, label: str, widget_key: str) -> None:
    if not file_path or not os.path.exists(file_path):
        return

    st.download_button(
        label=label,
        data=_read_binary_file(file_path),
        file_name=os.path.basename(file_path),
        mime="application/octet-stream",
        key=widget_key,
    )


def _render_artifacts(artifacts: dict) -> None:
    st.subheader("Entregables")

    inventario_excel = artifacts.get("inventario_excel")
    if inventario_excel:
        _render_download_button(
            inventario_excel,
            "Descargar inventario Excel",
            "download_inventario_excel",
        )

    for idx, path in enumerate(artifacts.get("word_tecnico", [])):
        _render_download_button(
            path,
            f"Descargar Word tecnico: {os.path.basename(path)}",
            f"download_word_tecnico_{idx}",
        )

    for idx, path in enumerate(artifacts.get("word_comercial", [])):
        _render_download_button(
            path,
            f"Descargar Word comercial: {os.path.basename(path)}",
            f"download_word_comercial_{idx}",
        )

    for idx, path in enumerate(artifacts.get("excel_ctg", [])):
        _render_download_button(
            path,
            f"Descargar CTG: {os.path.basename(path)}",
            f"download_excel_ctg_{idx}",
        )

    for idx, path in enumerate(artifacts.get("excel_comercial", [])):
        _render_download_button(
            path,
            f"Descargar checklist comercial: {os.path.basename(path)}",
            f"download_excel_comercial_{idx}",
        )

    for idx, path in enumerate(artifacts.get("json_sdm", [])):
        _render_download_button(
            path,
            f"Descargar JSON SDM: {os.path.basename(path)}",
            f"download_json_sdm_{idx}",
        )


def _render_summary(summary: dict) -> None:
    st.subheader("Resumen de corrida")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Estado", summary.get("status", "sin estado"))
    col2.metric("Run ID", summary.get("run_id", ""))
    col3.metric("Items detectados", summary.get("total_items_inventario", 0))
    col4.metric("Familias procesadas", len(summary.get("familias_procesadas", [])))

    cliente = summary.get("cliente") or "No identificado"
    st.caption(f"Cliente detectado: {cliente}")

    familias = summary.get("familias_procesadas", [])
    if familias:
        st.write("Familias procesadas:", ", ".join(familias))

    alertas = summary.get("alertas", [])
    if alertas:
        st.warning("\n".join(str(alerta) for alerta in alertas))


def _render_state_views(state: dict) -> None:
    inventario = state.get("inventario_global", [])
    if inventario:
        st.subheader("Inventario detectado")
        st.dataframe(pd.DataFrame(inventario), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Datos tecnicos")
        st.caption("Electricos")
        st.json(state.get("datos_electricos", {}))
        st.caption("Mecanicos")
        st.json(state.get("datos_mecanicos", {}))
        st.caption("Accesorios")
        st.json(state.get("datos_accesorios", {}))

    with col2:
        st.subheader("Datos complementarios")
        st.caption("Logisticos")
        st.json(state.get("datos_logisticos", {}))

        if state.get("resumen_comercial_ejecutivo"):
            st.caption("Resumen comercial ejecutivo")
            st.text_area(
                "Resumen comercial",
                state.get("resumen_comercial_ejecutivo", ""),
                height=240,
                disabled=True,
                label_visibility="collapsed",
            )

        if state.get("datos_normalizados_sdm"):
            st.caption("Datos normalizados SDM")
            st.json(state.get("datos_normalizados_sdm", {}))


def _render_human_intervention_form() -> None:
    pending_fields = st.session_state.get("pending_fields", [])
    backend_state = st.session_state.get("backend_state")

    if not pending_fields or not backend_state:
        return

    st.subheader("Intervencion humana requerida")
    st.info(
        "El auditor SDM detecto campos faltantes. Completa los valores tecnicos para generar los JSON SDM."
    )

    with st.form("human_input_form"):
        for field in pending_fields:
            st.text_input(f"Valor para {field}", key=f"human_{field}")

        submitted = st.form_submit_button("Reanudar fase SDM")

        if submitted:
            answers = {
                field: st.session_state.get(f"human_{field}", "").strip()
                for field in pending_fields
            }
            empty_fields = [field for field, value in answers.items() if not value]
            if empty_fields:
                st.error(f"Completa todos los campos antes de reanudar: {', '.join(empty_fields)}")
                return

            with st.spinner("Reanudando fase SDM con datos humanos..."):
                result = resume_sdm_from_human_input(backend_state, answers)

            st.session_state.workflow_result = result
            st.session_state.backend_state = result["state"]
            st.session_state.pending_fields = result.get("missing_fields", [])
            st.rerun()


def main() -> None:
    _init_session_state()

    st.title("Orquestador Multiagente de Cotizaciones")
    st.write(
        "Carga uno o varios documentos, configura las fases a ejecutar y revisa "
        "los entregables tecnicos, comerciales y SDM desde una sola interfaz."
    )

    with st.sidebar:
        st.header("Configuracion")
        if st.button("Nueva cotizacion / Limpiar", type="secondary"):
            _reset_quote_ui()
            st.rerun()

        if st.session_state.get("cfg_sdm") and not st.session_state.get("cfg_ingenieria"):
            st.session_state["cfg_ingenieria"] = True

        st.checkbox(
            "Ejecutar ingenieria",
            key="cfg_ingenieria",
            disabled=st.session_state.get("cfg_sdm", False),
            help="Puede ejecutarse sola o junto con Comercial. Si activas SDM, queda obligatoria.",
        )
        st.checkbox(
            "Ejecutar comercial",
            key="cfg_comercial",
            help="Puede ejecutarse sola o junto con Ingenieria.",
        )
        st.checkbox(
            "Ejecutar SDM",
            key="cfg_sdm",
            on_change=_enforce_sdm_dependency,
            help="Requiere Ingenieria activa.",
        )
        st.checkbox("Generar Word tecnico", key="cfg_documentos_tecnicos")
        st.checkbox("Generar CTG", key="cfg_ctg")
        if st.session_state.get("cfg_sdm"):
            st.info("SDM requiere Ingenieria, por eso queda activada automaticamente.")

        ejecutar_ingenieria = st.session_state["cfg_ingenieria"]
        ejecutar_comercial = st.session_state["cfg_comercial"]
        ejecutar_sdm = st.session_state["cfg_sdm"]
        ejecutar_documentos_tecnicos = st.session_state["cfg_documentos_tecnicos"]
        ejecutar_ctg = st.session_state["cfg_ctg"]
        invalid_config = False

    uploaded_files = st.file_uploader(
        "Documentos del proceso",
        type=["pdf", "docx", "doc", "xlsx", "xls", "txt", "eml"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.get('uploader_key', 0)}",
    )

    if uploaded_files:
        st.caption(f"Archivos cargados: {len(uploaded_files)}")
        st.dataframe(
            pd.DataFrame({"archivo": [file.name for file in uploaded_files]}),
            use_container_width=True,
            hide_index=True,
        )

    if st.button("Iniciar procesamiento", type="primary", disabled=invalid_config):
        if not uploaded_files:
            st.error("Debes cargar al menos un archivo antes de ejecutar.")
        else:
            empty_files = [f.name for f in uploaded_files if len(f.getbuffer()) == 0]
            if empty_files:
                st.error(
                    "Hay archivos vacios o dañados: "
                    + ", ".join(empty_files)
                    + ". Vuelve a cargarlos o exportalos nuevamente."
                )
                return

            st.session_state["workflow_result"] = None
            st.session_state["backend_state"] = None
            st.session_state["pending_fields"] = []

            request_config = {
                "ejecutar_ingenieria": ejecutar_ingenieria,
                "ejecutar_comercial": ejecutar_comercial,
                "ejecutar_sdm": ejecutar_sdm,
                "ejecutar_documentos_tecnicos": ejecutar_documentos_tecnicos,
                "ejecutar_ctg": ejecutar_ctg,
            }

            with st.spinner("Procesando documentos y ejecutando orquestacion..."):
                try:
                    result = run_pipeline_from_uploads(uploaded_files, request_config)
                except ValueError as e:
                    st.error(str(e))
                    return
                except Exception:
                    st.error(
                        "Ocurrio un error procesando los archivos. "
                        "Revisa que el formato sea correcto y que el archivo no este protegido o corrupto."
                    )
                    return

            st.session_state.workflow_result = result
            st.session_state.backend_state = result["state"]
            st.session_state.pending_fields = result.get("missing_fields", [])

    workflow_result = st.session_state.get("workflow_result")
    if not workflow_result:
        return

    summary = workflow_result.get("summary", {})
    state = workflow_result.get("state", {})

    _render_summary(summary)
    _render_human_intervention_form()
    _render_artifacts(summary.get("artifacts", {}))
    _render_state_views(state)


if __name__ == "__main__":
    main()
