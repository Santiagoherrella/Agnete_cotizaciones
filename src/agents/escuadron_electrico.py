"""
escuadron_electrico.py - Agentes encargados de extraer y validar parámetros eléctricos.

Propósito general:
Este módulo contiene el extractor y el revisor correspondientes a la fase inicial del 
diseño de transformadores (eléctrica). Su objetivo es identificar y validar voltajes, 
frecuencias, impedancias, pérdidas y normativas explícitas en el pliego del cliente.

Cuándo usarlo:
Se ejecuta automáticamente como el primer paso técnico en `grafo.py` después de agrupar 
por familia. El LLM extrae la data y el revisor la audita. Si falta la impedancia o el 
BIL secundario (datos críticos), pide reintento.

Requisitos:
- El estado general (`BotState`) y la información del inventario.
- Acceso a `get_llm("agente_electrico")`.
- Modelos tipados de `DatosElectricos`.
"""

from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosElectricos
from src.schemas.state import BotState

# ==========================================
# 1. EL PROMPT DEL EXTRACTOR (Con Lupa de Feedback)
# ==========================================
PROMPT_EXTRACTOR_ELECTRICO = """
Eres un Ingeniero Electricista Senior especializado en el diseño de transformadores para Magnetron S.A.S.
Por lo cual debes de realizar la siguiente tarea en español.
Tu misión es extraer ÚNICAMENTE la información ELÉCTRICA correspondiente a este tipo de transformador:

TIPO: {tipo_transformador}

INSTRUCCIONES CRÍTICAS:
- Extrae valores numéricos con sus unidades.
- Todo dato que encuentres en el texto debe tener como origen "Pliego".
- Si un dato no existe en el texto, debes poner obligatoriamente el valor "No especificado" y el origen "No especificado".
- NO inventes datos.

PARÁMETROS ELÉCTRICOS
(Solo incluir los datos disponibles sobre):
   - Voltajes nominales (primario/secundario) y configuración
   - Frecuencia de operación
   - Grupo de conexión
   - Impedancia de cortocircuito (%)
   - Regulación de tensión (taps)
   - Nivel de pérdidas máximas permitidas. (si es doble voltaje cual de los voltages debe de cumplir estas)
   - BIL (Nivel Básico de Aislamiento)
NORMATIVA Y CERTIFICACIONES
(Listar SOLO las normas mencionadas explícitamente):
   - Estándares aplicables con número y título completo
   - Tipo de norma (diseño, fabricación, ensayo, producto)
   - Pruebas y ensayos requeridos
   - Certificaciones exigidas
   - Requisitos sísmicos específicos
   - Normativa para materiales específicos
   
{bloque_feedback}

TEXTO DEL PLIEGO:
{texto_pliego}
"""

# ==========================================
# 2. EL NODO EXTRACTOR (El LLM)
# ==========================================
def nodo_extractor_electrico(state: BotState):
    """
    Busca e identifica los parámetros eléctricos primarios utilizando el LLM estructurado.
    Si el nodo revisor dejó feedback previo, se inyecta como contexto adicional para forzar
    al modelo a buscar minuciosamente.
    
    Parámetros:
    - state (BotState): Estado global del grafo.
    
    Retorna:
    - Diccionario con la clave "datos_electricos" mapeada al resultado (diccionario).
    """
    print(f"⚡ [Extractor Eléctrico] Analizando {state['item_actual_id']} (Intento {state.get('intentos_electrico', 0) + 1})")
    
    texto_crudo = state.get("texto_extraido", "")
    inventario = state.get("inventario_global", [])
    item_id = state.get("item_actual_id", "")
    trafo_actual = next((t for t in inventario if t["item_id"] == item_id), None)
    
    if not trafo_actual: 
        return {"datos_electricos": {}}

    # Si el revisor dejó feedback en un intento anterior, lo inyectamos como "lupa"
    feedback = state.get("feedback_electrico", "")
    bloque_feedback = f"\n⚠️ ATENCIÓN - INSTRUCCIÓN DEL REVISOR:\n{feedback}\n" if feedback and "APROBADO" not in feedback else ""

    llm = get_llm("agente_electrico") # Usa el modelo configurado en config.json
    llm_estructurado = llm.with_structured_output(DatosElectricos)
    prompt = ChatPromptTemplate.from_template(PROMPT_EXTRACTOR_ELECTRICO)
    
    cadena = prompt | llm_estructurado
    resultado = cadena.invoke({
        "item_id": trafo_actual["item_id"],
        "potencia": trafo_actual["potencia"],
        "voltaje_primario": trafo_actual["voltaje_primario"],
        "voltaje_secundario": trafo_actual["voltaje_secundario"],
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "bloque_feedback": bloque_feedback,
        "texto_pliego": texto_crudo
    })
    
    # Convertimos el objeto Pydantic a diccionario para guardarlo en el State
    return {"datos_electricos": resultado.model_dump() if hasattr(resultado, 'model_dump') else resultado.dict()}

# ==========================================
# 3. EL NODO REVISOR (Código Python Puro = $0 Costo)
# ==========================================
def nodo_revisor_electrico(state: BotState):
    """
    Audita el trabajo del Extractor Eléctrico y genera Alertas si es necesario.
    Verifica que la `impedancia` y el `bil_primario` se hayan extraído.
    
    Parámetros:
    - state (BotState): Estado global del grafo.
    
    Retorna:
    - Actualización del estado (intentos consumidos, feedback y alertas en caso de fallback).
    """
    datos = state.get("datos_electricos", {})
    intentos = state.get("intentos_electrico", 0)
    
    print(f"🕵️‍♂️ [Revisor Eléctrico] Auditando datos...")
    
    faltan_datos = []
    if datos.get("impedancia", {}).get("valor") == "No especificado":
        faltan_datos.append("impedancia")
    if datos.get("bil_primario", {}).get("valor") == "No especificado":
        faltan_datos.append("bil_primario")

    if not faltan_datos:
        print("✅ [Revisor Eléctrico] Datos completos. Aprobado.")
        return {"feedback_electrico": "APROBADO"}
    
    if intentos < 1:
        msg = f"No encontré: {', '.join(faltan_datos)}. Por favor, busca con más cuidado en las secciones de 'Ratings' o 'Impedance'."
        print(f"❌ [Revisor Eléctrico] Faltan datos. Solicitando reintento... ({msg})")
        return {"intentos_electrico": intentos + 1, "feedback_electrico": msg}
    
    # ESCENARIO C: Fallback (Alertas de Diseño generadas sin LLM)
    print(f"⚠️ [Revisor Eléctrico] Intentos agotados. Generando alerta para: {', '.join(faltan_datos)}")
    nuevas_alertas = []
    if "impedancia" in faltan_datos:
        nuevas_alertas.append("⚡ Eléctrico: Impedancia no especificada. Sugerencia: Usar estándar ANSI C57.12.34 (Ej: 1.5% a 2.5%).")
    if "bil_primario" in faltan_datos:
        nuevas_alertas.append("⚡ Eléctrico: BIL Primario no especificado. Sugerencia: Validar estándar Magnetrón según voltaje.")
        
    return {
        "datos_electricos": datos, # El dato se queda como "No especificado"
        "feedback_electrico": "APROBADO_CON_ALERTAS",
        "alertas_diseno": nuevas_alertas # Enviamos las alertas al State
    }

# ==========================================
# 4. EL ENRUTADOR (Conditional Edge para LangGraph)
# ==========================================
def decidir_ruta_electrico(state: BotState):
    """
    Le dice a LangGraph a dónde ir después de la revisión (avanzar a mecánico o iterar).
    """
    estado_revision = state.get("feedback_electrico", "")
    
    if "APROBADO" in estado_revision:
        return "fin_electrico"  # Ya sea puro o con fallback, terminó exitosamente.
    else:
        return "reintentar_electrico" # Vuelve al nodo extractor

# ==========================================
# METADATA
# tools_used: [langchain_core]
# use_cases: [Extracción parámetros eléctricos, Regulación/Auditoría en Grafo, Prompt con lupa de feedback]
# reusable_components: [nodo_extractor_electrico, nodo_revisor_electrico]
# dependencies: [pip install langchain-core pydantic]
# ==========================================