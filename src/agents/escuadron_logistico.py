"""
escuadron_logistico.py - Agentes encargados de extraer condiciones comerciales y logísticas.

Propósito general:
Extrae y valida la información no técnica del pliego (fechas, garantías, incoterms, 
condiciones de entrega, penalizaciones y requerimientos de presentación de la oferta).

Cuándo usarlo:
Se invoca en la parte final del pipeline de los escuadrones técnicos, usualmente para 
compilar los datos que permitirán elaborar la sección comercial de la cotización final.

Requisitos:
- El estado general (`BotState`) y la información del inventario.
- Acceso a `get_llm("agente_logistico")`.
- Modelos tipados de `DatosLogisticos`.
"""

from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosLogisticos
from src.schemas.state import BotState
from src.utils.logger import get_logger
logger = get_logger("EscuadronLogistico")


# ==========================================
# 1. EL PROMPT DEL EXTRACTOR (Basado en prompt comercial.txt)
# ==========================================
PROMPT_EXTRACTOR_LOGISTICO = """
<DOCUMENTO_DEL_CLIENTE>
{texto_pliego}
</DOCUMENTO_DEL_CLIENTE>

=========================================
INSTRUCCIONES DE EXTRACCIÓN:
=========================================

Eres un Analista Comercial Senior elaborando licitaciones para Magnetron USA LLC (fabricación en MAGNETRON S.A.S. Colombia).
Extrae ÚNICAMENTE la información COMERCIAL, LOGÍSTICA y JURÍDICA que aplica para este tipo de transformador:

EQUIPO: {tipo_transformador}

🚨 REGLA DE AISLAMIENTO ESTRICTO 🚨
El documento adjunto contiene información para MÚLTIPLES tipos de transformadores y familias. 
TÚ SOLO DEBES EXTRAER LA INFORMACIÓN PARA LA FAMILIA: {tipo_transformador}.
IGNORA POR COMPLETO cualquier párrafo, tabla o especificación que pertenezca explícitamente a otras familias presentes en el documento, tales como: {otras_familias}.
Si una especificación (ej. lugar de entrega, embalaje) menciona que es para otra familia, NO LA EXTRAIGAS, táchala mentalmente.

INSTRUCCIONES CRÍTICAS:
- IDIOMA OBLIGATORIO: Todo el texto extraído y generado DEBE estar 100% en ESPAÑOL TÉCNICO. 
- TRADUCCIÓN: Si el pliego original está en inglés, traduce las frases y descripciones al español (Ej: de "Solidly Grounded" a "Sólidamente Aterrizado", de "Mild Steel" a "Acero Dulce").
- EXCEPCIONES: NO traduzcas las siglas universales de ingeniería (ONAN, ONAF, kVA, BIL, IEEE, UL, ANSI, EXW) ni los nombres propios.
- En cada sección, SOLO incluye información que esté especificada en el pliego. 
- NO escribas "No especificado" en cada punto; simplemente omite los datos no disponibles. 
- Incluye valores numéricos concretos con sus unidades. 
- Si existen varios clientes o variantes, diferéncialos claramente. 
- Mantén un tono comercial, preciso y conciso; no inventes datos. 
- Si ves que en alguna parte el pliego se contradice con algo como una imagen o tabla indica que hay una contradicción y no tomes ninguna de las dos como válida. 
- Si el pliego tiene imágenes, descríbelas e indica que hay en ellas. 
- NO generes tablas en este resumen. Las tablas se crearán automáticamente por separado.  

NORMATIVA Y CERTIFICACIONES
(Listar SOLO las normas mencionadas explícitamente):
   - Estándares aplicables con número y título completo
   - Pruebas y ensayos requeridos
   - Certificaciones exigidas
   - Requisitos sísmicos específicos
   - Normativa para materiales específicos

IDENTIFICACIÓN, ROTULADO Y DOCUMENTACIÓN
(Solo incluir datos disponibles):
   - Requisitos de placas de características. (cantidad y cuando estas son abligatorias)
   - Etiquetado y marcación especial
   - Documentación técnica requerida
   - Planos y manuales solicitados
   - Idioma para documentación

EMBALAJE Y TRANSPORTE
(Solo incluir datos disponibles):
   - Tipo de embalaje requerido
   - Materiales específicos
   - Requisitos de preservación
   - Condiciones de transporte
   - Preparación para manejo

ENTREGABLES DE LA OFERTA
(Solo incluir datos disponibles):
   - Planos requeridos
   - Pruebas específicas
   - Declaración de pérdidas
{bloque_feedback}


"""

def nodo_extractor_logistico(state: BotState):
    """
    Localiza en el pliego todas las condiciones logísticas, comerciales y legales usando el LLM.
    
    Parámetros:
    - state (BotState): Estado del grafo con acceso a `texto_extraido`.
    
    Retorna:
    - `{"datos_logisticos": {...}}` con el mapa de la data según la interfaz `DatosLogisticos`.
    """
    logger.info(f" [Extractor Logístico] Analizando reglas comerciales para: {state.get('item_actual_id', '')} (Intento {state.get('intentos_logistico', 0) + 1})")
    
    texto_crudo = state.get("texto_extraido", "")
    inventario = state.get("inventario_global", [])
    trafo_actual = next((t for t in inventario if t["item_id"] == state.get("item_actual_id", "")), None)
    
    if not trafo_actual: 
        return {"datos_logisticos": {}}

    # Identificar otras familias para la Regla de Aislamiento
    familia_str = trafo_actual.get("tipo_transformador", "")
    todas_familias = list(set([t.get("tipo_transformador", "") for t in inventario if t.get("tipo_transformador") and t.get("tipo_transformador") != "No especificado"]))
    otras_familias = [f for f in todas_familias if f != familia_str]
    otras_familias_str = ", ".join(otras_familias) if otras_familias else "Ninguna otra familia identificada"

    # Si el revisor dejó feedback en un intento anterior, lo inyectamos como "lupa"
    feedback = state.get("feedback_logistico", "")
    bloque_feedback = f"\n ATENCIÓN - INSTRUCCIÓN DEL REVISOR:\n{feedback}\n" if feedback and "APROBADO" not in feedback else ""

    llm_estructurado = get_llm("agente_logistico").with_structured_output(DatosLogisticos)
    prompt = ChatPromptTemplate.from_template(PROMPT_EXTRACTOR_LOGISTICO)
    
    cadena = prompt | llm_estructurado
    resultado = cadena.invoke({
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "otras_familias": otras_familias_str,
        "texto_pliego": texto_crudo,
        "bloque_feedback": bloque_feedback
    })
    
    return {"datos_logisticos": resultado.model_dump() if hasattr(resultado, 'model_dump') else resultado.dict()}

def nodo_revisor_logistico(state: BotState):
    """
    Auditor logístico/comercial. Confirma que variables crudas como lugar de entrega 
    e información de garantías no falten.
    
    Parámetros:
    - state (BotState): Estado actual.
    
    Retorna:
    - Actualización del estado (intentos consumidos, alertas de fallback).
    """
    datos = state.get("datos_logisticos", {})
    intentos = state.get("intentos_logistico", 0)
    logger.info(f" [Revisor Comercial] Auditando riesgos del pliego...")
    
    faltan_datos = []
    if datos.get("lugar_entrega", {}).get("valor") == "No especificado":
        faltan_datos.append("lugar_entrega")
    if datos.get("garantias", {}).get("valor") == "No especificado":
        faltan_datos.append("garantias")

    if not faltan_datos:
        logger.info(" [Revisor Comercial] Datos completos. Aprobado.")
        return {"feedback_logistico": "APROBADO"}
    
    logger.info(f" [Revisor Comercial] Datos faltantes. Generando alerta comercial para: {', '.join(faltan_datos)}")
    nuevas_alertas = []
    if "lugar_entrega" in faltan_datos:
        nuevas_alertas.append(" Comercial: Lugar de entrega no especificado en el pliego técnico. Sugerencia: Verificar correos anexos o asumir entrega EXW Fábrica Colombia.")
    if "garantias" in faltan_datos:
        nuevas_alertas.append(" Comercial: Periodo de garantía no especificado. Sugerencia: Cotizar con la garantía estándar de 18 meses a partir de la entrega.")
        
    return {
        "datos_logisticos": datos, 
        "feedback_logistico": "APROBADO_CON_ALERTAS",
        "alertas_diseno": nuevas_alertas
    }

def decidir_ruta_logistico(state: BotState):
    """ Enrutador condicional. Si aprueba, pasa a la construcción del word (siguiente paso en grafo.py) """
    if "APROBADO" in state.get("feedback_logistico", ""):
        return "fin_logistico"
    return "reintentar_logistico"

# ==========================================
# METADATA
# tools_used: [langchain_core]
# use_cases: [Extracción parámetros logísticos y legales, Auditoría de términos comerciales]
# reusable_components: [nodo_extractor_logistico, nodo_revisor_logistico]
# dependencies: [pip install langchain-core pydantic]
# ==========================================