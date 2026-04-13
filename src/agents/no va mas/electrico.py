from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosElectricos
from src.schemas.state import BotState

# ==========================================
# EL PROMPT (BASADO EN TU EXCELENTE DISEÑO)
# ==========================================
PROMPT_AGENTE_ELECTRICO = """
Eres un Ingeniero Electricista Senior especializado en el diseño de transformadores para Magnetron S.A.S.
Tu misión es analizar el Pliego de Condiciones Técnicas y extraer ÚNICAMENTE la información ELÉCTRICA correspondiente al siguiente equipo específico:

EQUIPO A ANALIZAR:
- Item/Identificador: {item_id}
- Potencia: {potencia}
- Voltajes: {voltaje_primario} / {voltaje_secundario}
- Tipo: {tipo_transformador}

INSTRUCCIONES DE SALIDA:
- Busca en el pliego los parámetros eléctricos que apliquen EXCLUSIVAMENTE a este equipo.
- NO inventes datos. Si un dato no está en el pliego, el sistema pondrá "No especificado" por defecto.
- Incluye valores numéricos concretos con sus unidades.
- Mantén un tono técnico, preciso y conciso.
- Si el pliego se contradice, indica la contradicción en el campo correspondiente.

TEXTO DEL PLIEGO:
{texto_pliego}
"""

def nodo_agente_electrico(state: BotState):
    """
    Toma el transformador actual en proceso y extrae sus datos eléctricos profundos.
    """
    print(f"\n⚡ [Agente Eléctrico] Analizando especificaciones para: {state['item_actual_id']}")
    
    texto_crudo = state.get("texto_extraido", "")
    inventario = state.get("inventario_global", [])
    item_id = state.get("item_actual_id", "")
    
    # Buscamos los datos básicos del trafo actual para darle contexto al LLM
    trafo_actual = next((t for t in inventario if t["item_id"] == item_id), None)
    
    if not trafo_actual or not texto_crudo:
        print("⚠️ [Agente Eléctrico] No hay datos suficientes para analizar.")
        return {"datos_electricos": {}}

    # Usamos nuestro mejor modelo, ya que el análisis técnico requiere alta precisión
    llm = get_llm("agente_electrico")
    
    # Le conectamos el molde Pydantic que acabamos de crear
    llm_con_molde = llm.with_structured_output(DatosElectricos)
    prompt = ChatPromptTemplate.from_template(PROMPT_AGENTE_ELECTRICO)
    
    cadena = prompt | llm_con_molde
    
    # Ejecutamos inyectando los datos específicos de ESTE transformador
    resultado = cadena.invoke({
        "item_id": trafo_actual["item_id"],
        "potencia": trafo_actual["potencia"],
        "voltaje_primario": trafo_actual["voltaje_primario"],
        "voltaje_secundario": trafo_actual["voltaje_secundario"],
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "texto_pliego": texto_crudo
    })
    
    print(f"✅ [Agente Eléctrico] Datos extraídos con éxito.")
    
    # Guardamos los datos eléctricos en la tarjeta viajera
    return {"datos_electricos": resultado.dict()}