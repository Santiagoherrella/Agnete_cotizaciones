from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosMecanicos
from src.schemas.state import BotState

PROMPT_AGENTE_MECANICO = """
Eres un Ingeniero Mecánico Senior en Magnetron S.A.S.
Analiza el Pliego de Condiciones y extrae ÚNICAMENTE la información MECÁNICA, CONSTRUCTIVA y de FLUIDOS para este equipo:

EQUIPO: {item_id} | {potencia} | {tipo_transformador}

INSTRUCCIONES:
- Concéntrate en el tanque, pintura, aceite, bobinas y embalaje.
- Si es aceite vegetal, pon "KNAN".
- Incluye el color RAL o norma de pintura si se menciona.
- Si no está especificado, el sistema pondrá "No especificado". NUNCA inventes datos.

TEXTO DEL PLIEGO:
{texto_pliego}
"""

def nodo_agente_mecanico(state: BotState):
    print(f"⚙️ [Agente Mecánico] Analizando tanque, pintura y fluidos para: {state['item_actual_id']}")
    texto_crudo = state.get("texto_extraido", "")
    trafo_actual = next((t for t in state.get("inventario_global", []) if t["item_id"] == state["item_actual_id"]), None)
    
    if not trafo_actual or not texto_crudo: return {"datos_mecanicos": {}}

    llm_con_molde = get_llm("agente_mecanico").with_structured_output(DatosMecanicos)
    resultado = (ChatPromptTemplate.from_template(PROMPT_AGENTE_MECANICO) | llm_con_molde).invoke({
        "item_id": trafo_actual["item_id"], "potencia": trafo_actual["potencia"],
        "tipo_transformador": trafo_actual["tipo_transformador"], "texto_pliego": texto_crudo
    })
    return {"datos_mecanicos": resultado.dict()}
