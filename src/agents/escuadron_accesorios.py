from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosAccesorios
from src.schemas.state import BotState

# ==========================================
# 1. EL PROMPT DEL EXTRACTOR
# ==========================================
PROMPT_EXTRACTOR_ACCESORIOS = """
Eres un Especialista en Componentes y Accesorios en Magnetron S.A.S.
Por lo cual debes de realizar la siguiente tarea en español.
Extrae ÚNICAMENTE los ACCESORIOS, PROTECCIONES y DOCUMENTACIÓN para este tipo de transformador:

TIPO: {tipo_transformador}

INSTRUCCIONES CRÍTICAS:
- Extrae valores numéricos con sus unidades.
- Todo dato que encuentres en el texto debe tener como origen "Pliego".
- Si un dato no existe en el texto, debes poner obligatoriamente el valor "No especificado" y el origen "No especificado".
- NO inventes datos.
ACCESORIOS Y COMPONENTES
(Mencionar marcas específicas o restricciones; solo incluir datos disponibles):
   - Equipamiento de protección
   - Cambiadores de tensión o conmutadores
   - Aisladores de alta tensión (Dependiendiendo del amperaje)
   - Aisladres de baja tensión (cantidad de perforaciones en los aisladores de baja tension por potencia)
   - Sistemas de monitoreo
   - Gabinetes/cajas de conexión
   - Accesorios especiales
   - Válvulas y dispositivos de alivio
   - Sistemas de puesta a tierra
{bloque_feedback}

TEXTO DEL PLIEGO:
{texto_pliego}
"""

def nodo_extractor_accesorios(state: BotState):
    print(f"🧰 [Extractor Accesorios] Analizando {state.get('item_actual_id', '')} (Intento {state.get('intentos_accesorios', 0) + 1})")
    
    texto_crudo = state.get("texto_extraido", "")
    trafo_actual = next((t for t in state.get("inventario_global", []) if t["item_id"] == state.get("item_actual_id", "")), None)
    if not trafo_actual: return {"datos_accesorios": {}}

    feedback = state.get("feedback_accesorios", "")
    bloque_feedback = f"\n⚠️ ATENCIÓN - INSTRUCCIÓN DEL REVISOR:\n{feedback}\n" if feedback and "APROBADO" not in feedback else ""

    llm_estructurado = get_llm("agente_accesorios").with_structured_output(DatosAccesorios)
    prompt = ChatPromptTemplate.from_template(PROMPT_EXTRACTOR_ACCESORIOS)
    
    resultado = (prompt | llm_estructurado).invoke({
        "item_id": trafo_actual["item_id"],
        "potencia": trafo_actual["potencia"],
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "bloque_feedback": bloque_feedback,
        "texto_pliego": texto_crudo
    })
    
    return {"datos_accesorios": resultado.model_dump() if hasattr(resultado, 'model_dump') else resultado.dict()}

def nodo_revisor_accesorios(state: BotState):
    datos = state.get("datos_accesorios", {})
    intentos = state.get("intentos_accesorios", 0)
    print(f"🕵️‍♂️ [Revisor Accesorios] Auditando datos...")
    
    faltan_datos = []
    if datos.get("aisladores_at", {}).get("valor") == "No especificado":
        faltan_datos.append("aisladores_at")
    if datos.get("fusibles", {}).get("valor") == "No especificado":
        faltan_datos.append("fusibles")

    if not faltan_datos:
        print("✅ [Revisor Accesorios] Datos completos. Aprobado.")
        return {"feedback_accesorios": "APROBADO"}
    
    if intentos < 1:
        msg = f"No encontré: {', '.join(faltan_datos)}. Busca en las secciones de 'Bushings', 'Terminals', o 'Protection'."
        print(f"❌ [Revisor Accesorios] Faltan datos. Solicitando reintento... ({msg})")
        return {"intentos_accesorios": intentos + 1, "feedback_accesorios": msg}
    
    print(f"⚠️ [Revisor Accesorios] Intentos agotados. Generando alerta para: {', '.join(faltan_datos)}")
    nuevas_alertas = []
    if "aisladores_at" in faltan_datos:
        nuevas_alertas.append("🧰 Accesorios: Aisladores AT no especificados. Sugerencia: Para Padmount usar Insertos 200A. Para Polemount usar Bushings de Porcelana.")
    if "fusibles" in faltan_datos:
        nuevas_alertas.append("🧰 Accesorios: Protección no especificada. Sugerencia: Para Padmount incluir fusibles Bayonet.")
        
    return {
        "datos_accesorios": datos, 
        "feedback_accesorios": "APROBADO_CON_ALERTAS",
        "alertas_diseno": nuevas_alertas
    }

def decidir_ruta_accesorios(state: BotState):
    if "APROBADO" in state.get("feedback_accesorios", ""):
        return "fin_accesorios"
    return "reintentar_accesorios"