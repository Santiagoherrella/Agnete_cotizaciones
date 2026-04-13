from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosAccesorios
from src.schemas.state import BotState

PROMPT_AGENTE_ACCESORIOS = """
Eres un Especialista en Componentes y Accesorios en Magnetron S.A.S.
Analiza el Pliego de Condiciones y extrae ÚNICAMENTE los ACCESORIOS, PROTECCIONES y DOCUMENTACIÓN para este equipo:

EQUIPO: {item_id} | {potencia} | {tipo_transformador}

INSTRUCCIONES:
- Concéntrate en fusibles (Bayonet), aisladores (Bushings), insertos, válvulas y placas.
- Presta especial atención a la cantidad de perforaciones en las paletas (spades) de Baja Tensión.
- Extrae qué información piden en la placa de características y planos.
- Si no está especificado, el sistema pondrá "No especificado". NUNCA inventes datos.

TEXTO DEL PLIEGO:
{texto_pliego}
"""

def nodo_agente_accesorios(state: BotState):
    print(f"🧰 [Agente Accesorios] Buscando válvulas, aisladores y placas para: {state['item_actual_id']}")
    texto_crudo = state.get("texto_extraido", "")
    trafo_actual = next((t for t in state.get("inventario_global", []) if t["item_id"] == state["item_actual_id"]), None)
    
    if not trafo_actual or not texto_crudo: return {"datos_accesorios": {}}

    llm_con_molde = get_llm("agente_accesorios").with_structured_output(DatosAccesorios)
    resultado = (ChatPromptTemplate.from_template(PROMPT_AGENTE_ACCESORIOS) | llm_con_molde).invoke({
        "item_id": trafo_actual["item_id"], "potencia": trafo_actual["potencia"],
        "tipo_transformador": trafo_actual["tipo_transformador"], "texto_pliego": texto_crudo
    })
    return {"datos_accesorios": resultado.dict()}
