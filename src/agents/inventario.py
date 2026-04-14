"""
inventario.py - Agente enrutador y clasificador del inventario inicial.

Propósito general:
Identifica la naturaleza del documento analizado (correo informal vs. pliego técnico)
y extrae la lista de transformadores que se deben cotizar (Cantidades, Potencias, Voltajes). 
Sirve como el "Gatekeeper" de todo el sistema.

Cuándo usarlo:
Es el nodo de entrada absoluto (`extractor_inventario`) en `grafo.py`. Siempre se 
ejecuta de primero, ya que sin un inventario de equipos el resto de nodos no tiene con qué operar.

Requisitos:
- El estado `BotState` con el campo `texto_extraido` lleno.
- Modelos LLM configurados para `enrutador` y `agente_inventario`.
- Output parser de langchain Pydantic (InventarioPedido).
"""

from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import InventarioPedido, ClasificacionDocumento
from src.schemas.state import BotState
import os

# ==========================================
# PROMPT 0: EL CLASIFICADOR (CON EJEMPLO PARA MODELOS NANO)
# ==========================================
PROMPT_CLASIFICADOR = """
Eres un clasificador de documentos. Tu única tarea es decidir si el texto es un "CORREO" o un "PLIEGO".

REGLAS:
- CORREO: Si el texto parece impreso desde Outlook, tiene encabezados como "Desde", "Para", "Fecha", "Asunto", o es una cadena de mensajes informales.
- PLIEGO: Si es una especificación técnica, licitación formal o tiene tablas de cantidades comerciales.

--- EJEMPLO DE CORREO ---
Texto:
"Outlook
RV: COTIZAR TRAFO
Desde Juan Perez <juanperez@magnetron.com.co>
Fecha Lun 02/02/2026 16:09
Para Cotizaciones Magnetron SAS"

Respuesta correcta: CORREO
-------------------------

TEXTO A ANALIZAR:
{texto}
"""

# ==========================================
# PROMPT 1: ESPECIALISTA EN PLIEGOS (Rígido y estricto)
# ==========================================
PROMPT_PLIEGO = """
Eres un Ingeniero Evaluador de Licitaciones.
Extrae el Listado de Materiales (BOM) a cotizar.

REGLAS PARA PLIEGOS:
1. Busca tablas de cantidades ("Bid Schedule", "Qty").
2. IGNORA tablas técnicas (fusibles, pérdidas, impedancias). Si tiene kVA pero no dice cantidad a comprar, ES BASURA, ignórala.
3. Extrae: cantidad, potencia, voltaje primario, secundario, tipo constructivo y fases. NUNCA inventes datos.
4. Si las cantidades son contradictorias (ej. "One (2)"), prioriza siempre el número en texto ("One" = 1).
TEXTO DEL PLIEGO:
{texto}
"""

# ==========================================
# PROMPT 2: ESPECIALISTA EN CORREOS (Flexible e inferencial)
# ==========================================
PROMPT_CORREO = """
Eres un Asesor Comercial Técnico de Magnetrón. 
Tu trabajo es leer correos desordenados de los clientes y extraer qué transformadores quieren cotizar.

REGLAS PARA CORREOS:
1. Lee todo el hilo del correo. A veces en un correo dicen "100kVA" y en el de abajo aclaran que es "Pedestal". Junta toda la información para el mismo equipo.
2. Si piden cotizar un equipo pero no dicen la cantidad, asume que es Cantidad: 1.
3. Extrae: cantidad, potencia, voltaje primario, secundario, tipo constructivo y fases. 
4. Si un dato no está, escribe "No especificado". NUNCA dejes la lista vacía si hay una solicitud de cotización.

--- EJEMPLO ---
Texto: "Buen dia. Por favor su ayuda con el tramite. Pedestal Radial. Transformador 100 KVA 13,200/22,860 Voltios Primarios 120/240 Voltios Secundarios en Mild Steel"
Extracción: cantidad: 1, potencia: "100 KVA", tipo_transformador: "Pedestal Radial", voltaje_primario: "13,200/22,860 V", voltaje_secundario: "120/240 V", fases: "No especificado".
---------------

TEXTO DEL CORREO:
{texto}
"""

# ==========================================
# LA FUNCIÓN DEL NODO (EL ENRUTADOR)
# ==========================================
def nodo_extraer_inventario(state: BotState):
    """
    Toma el texto extraído del documento, evalúa de manera heurística/semántica 
    qué tipo de documento es (Correo o Pliego formal) y utiliza el prompt correspondiente
    para extraer la lista inicial de objetos a cotizar.
    
    Parámetros:
    - state (BotState): Estado que contiene `texto_extraido`.
    
    Retorna:
    - Estado de inventario: `{"inventario_global": [lista_de_equipos_pydantic]}`
    """
    texto_crudo = state.get("texto_extraido", "")
    if not texto_crudo:
         return {"inventario_global": []}

    print("\n🕵️‍♂️ [Enrutador] Analizando el tipo de documento...")
    
    # --- PASO A: CLASIFICAR ---
    llm_base = get_llm("enrutador")
    prompt_clasif = ChatPromptTemplate.from_template(PROMPT_CLASIFICADOR)
    
    # Unimos el prompt al modelo y al Pydantic
    cadena_clasificadora = prompt_clasif | llm_base.with_structured_output(ClasificacionDocumento)
    
    # Le pasamos solo los primeros 1500 caracteres (el encabezado) para evitar que se confunda
    decision = cadena_clasificadora.invoke({"texto": texto_crudo[:1500]})
    
    tipo_doc = decision.tipo.upper() # Aseguramos que esté en mayúsculas
    print(f"🔀 [Enrutador] Decisión: El documento es un {tipo_doc}. Asignando especialista...")
    
    # --- PASO B: ENRUTAR Y EXTRAER ---
    # La escogencia del tipo documental define el comportamiento y tono del LLM.
    if tipo_doc == "CORREO":
        # Usamos un LLM con un poco más de temperatura para inferir mejor el lenguaje natural
        llm_extractor = get_llm("agente_inventario")
        prompt = ChatPromptTemplate.from_template(PROMPT_CORREO)
    else:
        # Usamos un LLM totalmente rígido (Temp 0.0) para las tablas y pliegos
        llm_extractor = get_llm("agente_inventario")
        prompt = ChatPromptTemplate.from_template(PROMPT_PLIEGO)

    # Conectamos el molde de inventario
    llm_con_molde = llm_extractor.with_structured_output(InventarioPedido)
    cadena = prompt | llm_con_molde
    
    # Ejecutamos la extracción con el prompt y temperatura elegidos
    print(f"⚙️ [Agente {tipo_doc}] Extrayendo información...")
    resultado = cadena.invoke({"texto": texto_crudo})
    
    lista_inventario = [item.model_dump() if hasattr(item, 'model_dump') else item.dict() for item in resultado.equipos]
    print(f"✅ [Agente {tipo_doc}] ¡Éxito! Se encontraron {len(lista_inventario)} equipos.")
    
    return {"inventario_global": lista_inventario}

# ==========================================
# METADATA
# tools_used: [langchain_core, os]
# use_cases: [Clasificación de Documentos, Extracción Listado de Materiales (BOM)]
# reusable_components: [nodo_extraer_inventario]
# dependencies: [pip install langchain-core pydantic]
# ==========================================