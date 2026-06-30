from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import ReporteAuditoriaSDM
from src.schemas.state import BotState

PROMPT_AUDITOR_SDM = """
Eres el Auditor de Integridad de Datos para el SDM (Software de Diseño Magnetron).
Tu única misión es asegurar que los datos recolectados por los escuadrones permitan realizar un diseño de ingeniería válido.

DATOS ACTUALES:
- Eléctricos: {datos_electricos}
- Mecánicos: {datos_mecanicos}

REQUISITOS SDM:
Para que el SDM funcione, es OBLIGATORIO tener: Potencia, Voltajes (Pri/Sec), BIL, Impedancia y Tipo de Aceite.
Si falta alguno, responde 'aprobado_para_sdm': false.
"""

def nodo_auditor_sdm(state: BotState):
    llm = get_llm("agente_resumen") # Usamos un modelo potente para la auditoría
    llm_con_formato = llm.with_structured_output(ReporteAuditoriaSDM)
    
    prompt = ChatPromptTemplate.from_template(PROMPT_AUDITOR_SDM)
    cadena = prompt | llm_con_formato
    
    reporte = cadena.invoke({
        "datos_electricos": state.get("datos_electricos", {}),
        "datos_mecanicos": state.get("datos_mecanicos", {})
    })
    
    # Si no pasa la auditoría, añadimos una alerta roja al estado
    alertas = state.get("alertas_diseno", [])
    if not reporte.aprobado_para_sdm:
        alertas.append(f" ERROR SDM: Datos insuficientes ({', '.join(reporte.campos_faltantes)}). {reporte.observaciones}")
    
    return {
        "alertas_diseno": alertas,
        "auditoria_sdm_ok": reporte.aprobado_para_sdm,
        "campos_faltantes_sdm": reporte.campos_faltantes # Pasamos la batuta al humano # Nueva llave en el estado
    }