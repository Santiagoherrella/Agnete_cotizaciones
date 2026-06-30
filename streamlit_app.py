# streamlit run streamlit_app.py
import os

import pandas as pd
import streamlit as st

from src.services.pipeline_service import (
    resume_sdm_from_human_input,
    run_pipeline_from_uploads,
)
from src.utils.logger import current_user, SYSTEM_USER, get_logger

logger = get_logger("StreamlitApp")

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

    with st.expander("Ver Alertas y Familias detectadas", expanded=False):
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

    with st.expander("Ver detalles técnicos (Modo Desarrollador)", expanded=False):
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

def render_feedback_button():
    """Renderiza botón flotante que abre Forms para feedback"""
    
    # URL de tu Microsoft Forms
    FORMS_URL = "https://forms.office.com/r/yLAnpwJw1V"
    
    st.markdown("""
    <style>
    .feedback-float-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 999;
    }
    .feedback-float-btn {
        background: linear-gradient(135deg, #0f6db4 0%, #1a8fd9 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 14px 28px;
        font-weight: 600;
        font-size: 15px;
        box-shadow: 0 4px 15px rgba(15, 109, 180, 0.4);
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
    }
    .feedback-float-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(15, 109, 180, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="feedback-float-container">
        <a href="{FORMS_URL}" target="_blank" class="feedback-float-btn">
            💬 Déjanos tu Feedback
        </a>
    </div>
    """, unsafe_allow_html=True)

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


def _render_toc_capitalization_form() -> None:
    backend_state = st.session_state.get("backend_state")
    if not backend_state:
        return
    datos_sdm = backend_state.get("datos_normalizados_sdm", {})
    clasificacion = datos_sdm.get("clasificacion_ia", {})
    
    if not clasificacion.get("aplica_capitalizacion"):
        return

    st.subheader("Evaluación de Pérdidas (TOC)")
    st.info("El sistema detectó que este pliego incluye fórmulas de capitalización de pérdidas. Confirme o ajuste los factores monetarios.")
    
    with st.form("toc_capitalization_form"):
        col1, col2, col3, col4 = st.columns(4)
        k1 = col1.number_input("K1 (Pérdidas en Vacío)", value=0.0, step=0.1)
        k2 = col2.number_input("K2 (Pérdidas con Carga)", value=0.0, step=0.1)
        k3 = col3.number_input("K3", value=0.0, step=0.1)
        k4 = col4.number_input("K4", value=0.0, step=0.1)
        
        unidad = st.selectbox("Unidad original reportada", ["$/W", "$/kW"])
        submitted = st.form_submit_button("Aplicar factores y regenerar JSON")
        
        if submitted:
            factor = 0.001 if unidad == "$/kW" else 1.0
            
            backend_state["evaluacion_perdidas_economicas"] = {
                "k1_normalizado_usd_w": k1 * factor,
                "k2_normalizado_usd_w": k2 * factor,
                "k3_normalizado_usd_w": k3 * factor,
                "k4_normalizado_usd_w": k4 * factor
            }
            
            from src.tools.exportador_sdm import nodo_generar_json_sdm
            with st.spinner("Actualizando JSON SDM en caliente..."):
                rutas = nodo_generar_json_sdm(backend_state)
                # Actualizamos la visualización de los artefactos
                st.session_state.workflow_result["summary"]["artifacts"]["json_sdm"] = rutas.get("rutas_sdm_json", [])
            st.success("JSON SDM actualizado correctamente.")
            st.rerun()


def main() -> None:
    _init_session_state()

    st.title("Orquestador Multiagente de Cotizaciones")
    st.write(
        "Carga uno o varios documentos, configura las fases a ejecutar y revisa "
        "los entregables tecnicos, comerciales y SDM desde una sola interfaz."
    )
    
    render_feedback_button()

    with st.sidebar:
        st.header("Usuario Activo")
        web_user = st.text_input("Ingresa tu nombre para los registros", value=SYSTEM_USER)
        if web_user.strip():
            current_user.set(web_user.strip())

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
                logger.critical(f"=== INICIO DE PROCESAMIENTO === | Archivos cargados: {[f.name for f in uploaded_files]}")
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
    _render_toc_capitalization_form()
    _render_artifacts(summary.get("artifacts", {}))
    _render_state_views(state)


if __name__ == "__main__":
    main()
