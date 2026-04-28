from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.state import BotState

# PROMPT 1: ANALISTA COMERCIAL (RESUMEN)
PROMPT_ANALISTA = """
Eres un analista comercial especializado en la elaboración de ofertas y licitaciones sobre transformadores para la empresa Magnetron USA LLC, la fabricación esta a cargo de nuestra filial MAGNETRON SAS que se encuentra en Colombia   

Tu misión es analizar el siguiente Pliego de Condiciones Comerciales y Técnicas y elaborar un Resumen Ejecutivo exhaustivo en ESPAÑOL que sirva como base de arranque para definir las condiciones comerciales de la oferta. 

INSTRUCCIONES DE SALIDA: 
- Sigue exactamente el índice de secciones (1-8) mostrado más abajo. 
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
 3. EXTRAE PARÁMETROS TECNICOS 
     3.1. Formula de evaluación de pérdidas y trae los valores  
     3.2. Tipo de núcleo y material
     3.3. Formato para diligenciamiento de Perdidas en vacío y a plena carga
     3.4. Solicitud de plano con la presentación de la oferta
     3.5. Solicitud de Marcas especificas
     3.6. Solicitud de proveedores aprobados
     3.7. Requerimiento de país de fabricación
     3.8. Dimensiones y peso límites
4. EXTRAER REVISION JURIDICA
    4.1. Anexos minuta de contrato o términos de contratación.
    4.2. Penalizaciones o multas
5. EXTRAER CERTIFICACIONES 
   5.1 Certificaciones exigidas
6. EXTRAER PRESENTACION DE LA DOCUMENTACIÓN DE LA OFERTA 
    6.1. Solicitud índice y paginado
    6.2. Solicitud Formato de los archivos
7. EXTRAER INFORMACION SOBRE ENTREGAS
    7.1. Lugar entrega – Zip code
    7.2. Incoterm.
    7.3. Condiciones de transporte Condicioness especiales sobre horarios de entrega 
8. EXTRAER ENTREGABLES DE LA OFERTA 
(Solo incluir datos disponibles):
    8.1. Planos requeridos
    8.2. Formularios exigidos
    8.3. Declaración de pérdidas 

Documento del Cliente: {context}
Resumen profesional (en ESPAÑOL):
"""

# PROMPT 2: GENERADOR DE TABLA
PROMPT_TABLA = """
Eres un analista comercial especializado en la elaboración de ofertas y licitaciones sobre transformadores para la empresa Magnetron.

Tu tarea es tomar el siguiente RESUMEN EJECUTIVO y generar EXACTAMENTE UNA TABLA en formato vertical (Markdown) que puedan copiarse directamente a Excel.

IMPORTANTE: 
- Genera SOLO la tabla, sin texto adicional antes o después.
- Usa el formato Markdown estricto: | Descripción  | Resultado |
- Si algún dato no está disponible en el resumen, coloca "N/A"
- NO inventes información que no esté en el resumen.

---
**Tabla #1 – Check list comercial **

| Descripción | Resultado |
|-------------|-----------|
| Fecha de presentación de la oferta | |
| Método de presentación de las ofertas | |
| Firma requerida | |
| Requerimientos especiales | |
| Fecha límite y método para consultas | |
| Aceptación de ofertas parciales | |
| Forma de Pago | |
| Validez de la oferta | |
| Moneda | |
| Duración del suministro | |
| Tiempo de entrega requerido | |
| Permite fórmula de reajuste de precios | |
| Evaluación de pérdidas | |
| Fórmula para evaluación económica | |
| Formato para diligenciamiento de pérdidas | |
| Solicitud de plano con la presentación de la oferta | |
| Solicitud de marcas específicas | |
| Solicitud de proveedores aprobados | |
| Requerimiento de país de fabricación | |
| Anexos minuta de contrato o términos de contratación | |
| Penalizaciones o multas | |
| Requiere estampilla | |
| Requiere fianza - pólizas - seguros | |
| Lugar de entrega | |
| Condiciones de transporte | |
| Condiciones especiales horarios | |
| Garantía de fabricación | |
| Entregables de la oferta (Documentos que se deben anexar) | |
| Otras condiciones | |

========================================
RESUMEN EJECUTIVO:
{resumen}
"""

def nodo_analista_comercial(state: BotState):
    print("💼 [Agente Comercial] Redactando Resumen Ejecutivo...")
    llm = get_llm("agente_resumen") 
    prompt = ChatPromptTemplate.from_template(PROMPT_ANALISTA)
    cadena = prompt | llm
    
    respuesta = cadena.invoke({"context": state["texto_extraido"]})
    return {"resumen_comercial_ejecutivo": respuesta.content}

def nodo_tabulador_comercial(state: BotState):
    print("📊 [Agente Comercial] Generando Tabla de Checklist...")
    llm = get_llm("agente_inventario") 
    prompt = ChatPromptTemplate.from_template(PROMPT_TABLA)
    cadena = prompt | llm
    
    # Aquí usamos la llave correcta que generó el nodo anterior
    respuesta = cadena.invoke({"resumen": state["resumen_comercial_ejecutivo"]})
    return {"tabla_comercial_checklist": respuesta.content}