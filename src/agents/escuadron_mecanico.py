"""
escuadron_mecanico.py - Agentes encargados de extraer parámetros mecánicos y constructivos.

Propósito general:
Este módulo contiene el extractor y el revisor correspondientes a la fase mecánica del 
diseño de transformadores. Su objetivo es identificar y validar variables constructivas 
(materiales del tanque, refrigeración, pintura, color, peso) en el pliego del cliente.

Cuándo usarlo:
Se ejecuta automáticamente en `grafo.py` después del escuadrón eléctrico. Extrae data, 
y en caso de no hallar color de pintura o fluido dieléctrico, el revisor intentará 
reguiar al extractor y finalmente emitirá una sugerencia ANSI.

Requisitos:
- El estado general (`BotState`) y la información del inventario.
- Acceso a `get_llm("agente_mecanico")`.
- Modelos tipados de `DatosMecanicos`.
"""

from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosMecanicos
from src.schemas.state import BotState

# ==========================================
# 1. EL PROMPT DEL EXTRACTOR
# ==========================================
PROMPT_EXTRACTOR_MECANICO = """
Eres un Ingeniero Mecánico Senior en Magnetron S.A.S.
Extrae ÚNICAMENTE la información MECÁNICA,

TIPO: {tipo_transformador}
INSTRUCCIONES CRÍTICAS:
- IDIOMA OBLIGATORIO: Todo el texto extraído y generado DEBE estar 100% en ESPAÑOL TÉCNICO. 
- TRADUCCIÓN: Si el pliego original está en inglés, traduce las frases y descripciones al español (Ej: de "Solidly Grounded" a "Sólidamente Aterrizado", de "Mild Steel" a "Acero Dulce").
- EXCEPCIONES: NO traduzcas las siglas universales de ingeniería (ONAN, ONAF, kVA, BIL, IEEE, UL, ANSI, EXW) ni los nombres propios.
- Extrae valores numéricos con sus unidades.
- Todo dato que encuentres en el texto debe tener como origen "Pliego".
- Si un dato no existe en el texto, debes poner obligatoriamente el valor "No especificado" y el origen "No especificado".
- NO inventes datos.
CARACTERÍSTICAS CONSTRUCTIVAS Y MECÁNICAS
(Discriminar por cliente si aplica; solo incluir datos disponibles):
   - Tipo de refrigeración (si es con aceite vegetal colocar KNAN)
   - Materiales de bobinados
   - Forma constructiva de la parte activa
   - Tipo de núcleo y material
   - Sistema de aislamiento
   - Aceite o fluido dieléctrico (marca si es FR3)
   - Características del tanque
   - Sistemas de sellado
   - Requisitos sísmicos
   - Dimensiones y peso límites
   - Radiadores y sistemas de enfriamiento

SISTEMA DE PINTURA Y TRATAMIENTO SUPERFICIAL
(Solo incluir datos disponibles):
   - Preparación superficial requerida
   - Tipo de pintura base y acabado
   - Espesor mínimo de película seca
   - Color RAL especificado
   - Requisitos de resistencia a corrosión
   - Tratamientos especiales
   
{bloque_feedback}

TEXTO DEL PLIEGO:
{texto_pliego}
"""

# ==========================================
# 2. EL NODO EXTRACTOR
# ==========================================
def nodo_extractor_mecanico(state: BotState):
    """
    Busca e identifica los parámetros constructivos utilizando el LLM estructurado.
    
    Parámetros:
    - state (BotState): Estado global.
    
    Retorna:
    - Diccionario con la clave "datos_mecanicos" con los campos requeridos mapeados.
    """
    print(f"🔩 [Extractor Mecánico] Analizando {state['item_actual_id']} (Intento {state.get('intentos_mecanico', 0) + 1})")
    
    texto_crudo = state.get("texto_extraido", "")
    trafo_actual = next((t for t in state.get("inventario_global", []) if t["item_id"] == state.get("item_actual_id", "")), None)
    
    if not trafo_actual: 
        return {"datos_mecanicos": {}}

    feedback = state.get("feedback_mecanico", "")
    bloque_feedback = f"\n⚠️ ATENCIÓN - INSTRUCCIÓN DEL REVISOR:\n{feedback}\n" if feedback and "APROBADO" not in feedback else ""

    llm_estructurado = get_llm("agente_mecanico").with_structured_output(DatosMecanicos)
    prompt = ChatPromptTemplate.from_template(PROMPT_EXTRACTOR_MECANICO)
    
    resultado = (prompt | llm_estructurado).invoke({
        "item_id": trafo_actual["item_id"],
        "potencia": trafo_actual["potencia"],
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "bloque_feedback": bloque_feedback,
        "texto_pliego": texto_crudo
    })
    
    return {"datos_mecanicos": resultado.model_dump() if hasattr(resultado, 'model_dump') else resultado.dict()}

# ==========================================
# 3. EL NODO REVISOR (Con Alertas de Diseño)
# ==========================================
def nodo_revisor_mecanico(state: BotState):
    """
    Auditor de las variables mecánicas. Detecta si falta color de pintura o el 
    fluido dieléctrico, y solicita iterar si hay intentos o emite alertas de diseño.
    
    Parámetros:
    - state (BotState): Estado actual.
    
    Retorna:
    - Actualización del estado (intento consumidos, y alertas).
    """
    datos = state.get("datos_mecanicos", {})
    intentos = state.get("intentos_mecanico", 0)
    print(f"🕵️‍♂️ [Revisor Mecánico] Auditando datos...")
    
    faltan_datos = []
    if datos.get("color_pintura", {}).get("valor") == "No especificado":
        faltan_datos.append("color_pintura")
    if datos.get("fluido_dielectrico", {}).get("valor") == "No especificado":
        faltan_datos.append("fluido_dielectrico")

    if not faltan_datos:
        print("✅ [Revisor Mecánico] Datos completos. Aprobado.")
        return {"feedback_mecanico": "APROBADO"}
    
    if intentos < 1:
        msg = f"No encontré: {', '.join(faltan_datos)}. Busca en secciones de 'Tank', 'Finish', 'Paint' o 'Fluid'."
        print(f"❌ [Revisor Mecánico] Faltan datos. Solicitando reintento... ({msg})")
        return {"intentos_mecanico": intentos + 1, "feedback_mecanico": msg}
    
    print(f"⚠️ [Revisor Mecánico] Intentos agotados. Generando alerta para: {', '.join(faltan_datos)}")
    nuevas_alertas = []
    if "color_pintura" in faltan_datos:
        nuevas_alertas.append("🔩 Mecánico: Color de pintura no especificado. Sugerencia: Usar Verde RAL 6014 (Estándar Pedestal) o Gris ANSI 70 (Estándar Poste).")
    if "fluido_dielectrico" in faltan_datos:
        nuevas_alertas.append("🔩 Mecánico: Fluido dieléctrico no especificado. Sugerencia: Asumir Aceite Mineral Tipo II.")
        
    return {
        "datos_mecanicos": datos, 
        "feedback_mecanico": "APROBADO_CON_ALERTAS",
        "alertas_diseno": nuevas_alertas
    }

# ==========================================
# 4. EL ENRUTADOR
# ==========================================
def decidir_ruta_mecanico(state: BotState):
    """ Enrutador hacia la siguiente fase de accesorios. """
    if "APROBADO" in state.get("feedback_mecanico", ""):
        return "fin_mecanico"
    return "reintentar_mecanico"

# ==========================================
# METADATA
# tools_used: [langchain_core]
# use_cases: [Extracción parámetros mecánicos y constructivos, Auto-Revisión LLM]
# reusable_components: [nodo_extractor_mecanico, nodo_revisor_mecanico]
# dependencies: [pip install langchain-core pydantic]
# ==========================================