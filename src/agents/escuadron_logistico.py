from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import DatosLogisticos
from src.schemas.state import BotState

# ==========================================
# 1. EL PROMPT DEL EXTRACTOR (Basado en prpmpt comercial.txt)
# ==========================================
PROMPT_EXTRACTOR_LOGISTICO = """
Eres un Analista Comercial Senior elaborando licitaciones para Magnetron USA LLC (fabricación en MAGNETRON S.A.S. Colombia).
Extrae ÚNICAMENTE la información COMERCIAL, LOGÍSTICA y JURÍDICA que apñlica para este tipo de transformador:

EQUIPO: {tipo_transformador}

INSTRUCCIONES CRÍTICAS:
- En cada sección, SOLO incluye información que esté especificada en el pliego. 
- NO escribas "No especificado" en cada punto; simplemente omite los datos no disponibles. 
- Incluye valores numéricos concretos con sus unidades. 
- Si existen varios clientes o variantes, diferéncialos claramente. 
- Mantén un tono comercial, preciso y conciso; no inventes datos. 
- Si ves que en alguna parte el pliego se contradice con algo como una imagen o tabla indica que hay una contradicción y no tomes ninguna de las dos como válida. 
- Si el pliego tiene imágenes, descríbelas e indica que hay en ellas. 
- NO generes tablas en este resumen. Las tablas se crearán automáticamente por separado.  

1. CONDICIONES GENERALES  
   (Solo incluir los datos disponibles sobre): 
    1.1. Fecha de presentación de la oferta 
    1.2. Indica la hora Colombia de presentación, realiza conversión a UTC -5  
    1.3. Identifica en el pliego el método de presentación de la oferta Ejemplo: Correo electrónico, Portal, Correspondencia física.  
        1.3.1. Si es correo electrónico 
            1.3.1.1 Identifica la dirección de correo electrónico para envío de la oferta   
        1.3.2. Si es portal.
            1.3.2.1. Identifica el link de cargue de la documentación de la oferta  
        1.3.3. Si es por Correspondencia física: 
            1.3.3.1. Identifica si requieren Firma en tinta, puño y letra 
            1.3.3.2.Identifica si tiene requerimiento especial.  
            1.3.3.3. Identifica si requieren Firma escaneada o certificada 
            1.3.3.4. Identifica si se debe notarizar documentos firmados 
    1.4. Fecha límite de consultas  
    1.5. Método de envío de consultas 
        1.5.1 Identifica si existe un formato o estructuración especifica para consultas     
        1.5.2. Identifica si el cliente tiene consultas comerciales y/o técnicas y enuméralas en orden de prioridad.   
    1.6. Identifica si aceptan presentación de oferta parcial  
    1.7. Identifica si permiten desviaciones o excepciones técnicas  
    1.8. Identifica si permiten desviaciones o excepciones comerciales 

 2. EXTRAER CONDICIONES COMERCIALES  
     2.1. Forma de Pago.
     2.2. Validez de la oferta
     2.3. Moneda
     2.4. Duración del suministro
     2.5. Tiempo de entrega requerido
     2.6. Permite formula de reajuste de precio
     2.7. Identifica si se debe anexar fianza de seriedad de la oferta
     2.8. Detalla requerimiento sobre pólizas y seguros aplicables
     2.9.Identifica si hay requisito de estampillas e impuestos 		 
3. EXTRAER REVISION JURIDICA
    3.1. Anexos minuta de contrato o términos de contratación.
    3.2. Penalizaciones o multas
4. EXTRAER CERTIFICACIONES 
   4.1 Certificaciones exigidas
5. EXTRAER PRESENTACION DE LA DOCUMENTACIÓN DE LA OFERTA 
    5.1. Solicitud índice y paginado
    5.2. Solicitud Formato de los archivos
6. EXTRAER INFORMACION SOBRE ENTREGAS
    6.1.Lugar entrega – Zip code
    6.2.Incoterm .
    6.3. Condiciones de transporteCondiciones especiales sobre horarios de entrega 
7. EXTRAER ENTREGABLES DE LA OFERTA 
(Solo incluir datos disponibles):
    7.1. Planos requeridos
    7.2. Formularios exigidos
    7.3. Declaración de pérdidas 
{bloque_feedback}

TEXTO DEL PLIEGO:
{texto_pliego}
"""

def nodo_extractor_logistico(state: BotState):
    print(f"🚚 [Extractor Logístico] Analizando reglas comerciales para: {state.get('item_actual_id', '')} (Intento {state.get('intentos_logistico', 0) + 1})")
    
    texto_crudo = state.get("texto_extraido", "")
    trafo_actual = next((t for t in state.get("inventario_global", []) if t["item_id"] == state.get("item_actual_id", "")), None)
    if not trafo_actual: return {"datos_logisticos": {}}

    feedback = state.get("feedback_logistico", "")
    bloque_feedback = f"\n⚠️ ATENCIÓN - INSTRUCCIÓN DEL REVISOR:\n{feedback}\n" if feedback and "APROBADO" not in feedback else ""

    llm_estructurado = get_llm("agente_logistico").with_structured_output(DatosLogisticos)
    prompt = ChatPromptTemplate.from_template(PROMPT_EXTRACTOR_LOGISTICO)
    
    resultado = (prompt | llm_estructurado).invoke({
        "item_id": trafo_actual["item_id"],
        "tipo_transformador": trafo_actual["tipo_transformador"],
        "bloque_feedback": bloque_feedback,
        "texto_pliego": texto_crudo
    })
    
    return {"datos_logisticos": resultado.model_dump() if hasattr(resultado, 'model_dump') else resultado.dict()}

def nodo_revisor_logistico(state: BotState):
    datos = state.get("datos_logisticos", {})
    intentos = state.get("intentos_logistico", 0)
    print(f"🕵️‍♂️ [Revisor Comercial] Auditando riesgos del pliego...")
    
    faltan_datos = []
    if datos.get("lugar_entrega", {}).get("valor") == "No especificado":
        faltan_datos.append("lugar_entrega")
    if datos.get("garantias", {}).get("valor") == "No especificado":
        faltan_datos.append("garantias")

    if not faltan_datos:
        print("✅ [Revisor Comercial] Datos completos. Aprobado.")
        return {"feedback_logistico": "APROBADO"}
    
    if intentos < 1:
        msg = f"No encontré: {', '.join(faltan_datos)}. Busca en secciones de 'Delivery', 'Warranty', 'Shipment' o 'Terms'."
        print(f"❌ [Revisor Comercial] Faltan datos. Solicitando reintento... ({msg})")
        return {"intentos_logistico": intentos + 1, "feedback_logistico": msg}
    
    print(f"⚠️ [Revisor Comercial] Intentos agotados. Generando alerta comercial para: {', '.join(faltan_datos)}")
    nuevas_alertas = []
    if "lugar_entrega" in faltan_datos:
        nuevas_alertas.append("🚚 Comercial: Lugar de entrega no especificado en el pliego técnico. Sugerencia: Verificar correos anexos o asumir entrega EXW Fábrica Colombia.")
    if "garantias" in faltan_datos:
        nuevas_alertas.append("🚚 Comercial: Periodo de garantía no especificado. Sugerencia: Cotizar con la garantía estándar de 18 meses a partir de la entrega.")
        
    return {
        "datos_logisticos": datos, 
        "feedback_logistico": "APROBADO_CON_ALERTAS",
        "alertas_diseno": nuevas_alertas
    }

def decidir_ruta_logistico(state: BotState):
    if "APROBADO" in state.get("feedback_logistico", ""):
        return "fin_logistico"
    return "reintentar_logistico"