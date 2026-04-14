"""
escuadron_accesorios.py - Agentes encargados de extraer y validar accesorios.

Propósito general:
Este módulo contiene el extractor y el revisor correspondientes a la fase de accesorios 
y componentes (aisladores, válvulas, protecciones, etc.) del transformador. Forma parte 
del pipeline de escuadrones técnicos que procesa cada familia de transformadores.

Cuándo usarlo:
Este módulo es consumido por el flujo orquestador en `grafo.py`. El extractor usa un LLM 
para buscar los componentes en el pliego; el revisor actúa como un auditor basado en reglas 
duras que devuelve la tarea al extractor si falta información obligatoria.

Requisitos:
- El estado general (`BotState`) y la información del inventario.
- Acceso a `get_llm("agente_accesorios")`.
- Modelos tipados de `DatosAccesorios` para que el LLM devuelva la información estructurada.
"""

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
    """
    Busca e identifica los accesorios del transformador utilizando el LLM estructurado.
    Si el nodo revisor dejó feedback previo, este se inyecta como contexto adicional.
    
    Parámetros:
    - state (BotState): Estado global del grafo.
    
    Retorna:
    - Diccionario con la clave "datos_accesorios" mapeada al resultado extraído.
    """
    print(f"🧰 [Extractor Accesorios] Analizando {state.get('item_actual_id', '')} (Intento {state.get('intentos_accesorios', 0) + 1})")
    
    # 1. Preparar información basica del ítem desde el estado
    texto_crudo = state.get("texto_extraido", "")
    trafo_actual = next((t for t in state.get("inventario_global", []) if t["item_id"] == state.get("item_actual_id", "")), None)
    
    if not trafo_actual: 
        return {"datos_accesorios": {}}

    # 2. Inyección de feedback (Ciclo iterado del Revisor)
    feedback = state.get("feedback_accesorios", "")
    bloque_feedback = f"\n⚠️ ATENCIÓN - INSTRUCCIÓN DEL REVISOR:\n{feedback}\n" if feedback and "APROBADO" not in feedback else ""

    # 3. Solicitud al LLM pidiendo que empareje la salida con "DatosAccesorios"
    llm_estructurado = get_llm("agente_accesorios").with_structured_output(DatosAccesorios)
    prompt = ChatPromptTemplate.from_template(PROMPT_EXTRACTOR_ACCESORIOS)
    
    resultado = (prompt | llm_estructurado).invoke({
        "item_id": trafo_actual["item_id"],
        "potencia": trafo_actual["potencia"],
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "bloque_feedback": bloque_feedback,
        "texto_pliego": texto_crudo
    })
    
    # Manejar compatibilidad entre versiones de Pydantic
    return {"datos_accesorios": resultado.model_dump() if hasattr(resultado, 'model_dump') else resultado.dict()}

def nodo_revisor_accesorios(state: BotState):
    """
    Revisa la calidad de los datos extraídos por `nodo_extractor_accesorios`. 
    Verifica campos obligatorios (aisladores y fusibles) y genera feedback para reguiar.
    
    Parámetros:
    - state (BotState): Estado global del grafo.
    
    Retorna:
    - Actualización del estado (intentos consumidos, feedback y alertas en caso extremo).
    """
    datos = state.get("datos_accesorios", {})
    intentos = state.get("intentos_accesorios", 0)
    print(f"🕵️‍♂️ [Revisor Accesorios] Auditando datos...")
    
    # 1. Auditoría de información mínima
    faltan_datos = []
    if datos.get("aisladores_at", {}).get("valor") == "No especificado":
        faltan_datos.append("aisladores_at")
    if datos.get("fusibles", {}).get("valor") == "No especificado":
        faltan_datos.append("fusibles")

    # 2. Flujo Exitoso
    if not faltan_datos:
        print("✅ [Revisor Accesorios] Datos completos. Aprobado.")
        return {"feedback_accesorios": "APROBADO"}
    
    # 3. Flujo Reprocesamiento (Aún hay intentos)
    if intentos < 1:
        msg = f"No encontré: {', '.join(faltan_datos)}. Busca en las secciones de 'Bushings', 'Terminals', o 'Protection'."
        print(f"❌ [Revisor Accesorios] Faltan datos. Solicitando reintento... ({msg})")
        return {"intentos_accesorios": intentos + 1, "feedback_accesorios": msg}
    
    # 4. Flujo de Alerta/Fallback (Intentos agotados)
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
    """
    Función de enrutamiento (Conditional Edge) para el nodo del escuadrón.
    Dramatiza la lógica de sí volver atrás o avanzar al siguiente escuadron.
    """
    if "APROBADO" in state.get("feedback_accesorios", ""):
        return "fin_accesorios"
    return "reintentar_accesorios"

# ==========================================
# METADATA
# tools_used: [langchain_core]
# use_cases: [Revisión y Extracción de accesorios de trasformadores, Auditaje Automático]
# reusable_components: [nodo_extractor_accesorios, nodo_revisor_accesorios, decidir_ruta_accesorios]
# dependencies: [pip install langchain-core pydantic]
# ==========================================