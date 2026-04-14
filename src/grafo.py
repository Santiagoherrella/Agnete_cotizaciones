from langgraph.graph import StateGraph, END
from src.schemas.state import BotState

from src.agents.inventario import nodo_extraer_inventario
from src.tools.exportador import nodo_crear_excel_inventario, nodo_crear_excel_ctg
from src.agents.resumen_general import nodo_generar_resumen_tipo # Importamos el Ensamblador

from src.agents.escuadron_electrico import nodo_extractor_electrico, nodo_revisor_electrico, decidir_ruta_electrico
from src.agents.escuadron_mecanico import nodo_extractor_mecanico, nodo_revisor_mecanico, decidir_ruta_mecanico
from src.agents.escuadron_accesorios import nodo_extractor_accesorios, nodo_revisor_accesorios, decidir_ruta_accesorios
from src.agents.escuadron_logistico import nodo_extractor_logistico, nodo_revisor_logistico, decidir_ruta_logistico

"""
ESTRUCTURA DEL GRAFO (WORKFLOW)
===============================
Este archivo define la orquesta de agentes que procesan los pliegos de condiciones.
El flujo sigue una lógica de "Pipeline" con ciclos de revisión y una gestión por "Familias".

PASOS PRINCIPALES:
1. Extracción de Inventario: Identifica qué se va a cotizar.
2. Supervisión: Agrupa los ítems por familias de transformadores y gestiona el turno de cada una.
3. Escuadrones Técnicos: Procesamiento secuencial (Eléctrico -> Mecánico -> Accesorios -> Logístico).
   - Cada escuadrón tiene un EXTRACTOR (busca datos) y un REVISOR (valida y pide correcciones).
4. Ensamblado y Cierre: Genera reportes (Word/Excel) y vuelve al Supervisor para la siguiente familia.
"""

# =============================================================================
# EL SUPERVISOR (Controlador de Iteraciones por Familias)
# =============================================================================
def nodo_supervisor_familias(state: BotState):
    """
    Actúa como el cerebro del flujo. Decide qué familia de transformadores procesar a continuación.
    Si ya no quedan familias pendientes, marca el fin del proceso.
    """
    inventario = state.get("inventario_global", [])
    completados = state.get("resumenes_completados", [])
    
    # 1. Identificar qué tipos de transformadores (familias) existen en el documento
    familias_unicas = list(set([t["tipo_transformador"] for t in inventario if t.get("tipo_transformador") != "No especificado"]))
    
    # 2. Buscar si hay alguna familia que aún no haya sido procesada
    familia_pendiente = None
    item_representativo = None
    
    for familia in familias_unicas:
        if familia not in completados:
            familia_pendiente = familia
            # Seleccionamos un ítem de esta familia para que sirva de guía en la búsqueda de datos
            item_representativo = next(t["item_id"] for t in inventario if t["tipo_transformador"] == familia)
            break
            
    # 3. Si no hay familias pendientes, terminamos el flujo global
    if not familia_pendiente:
        print(f"\n👨‍💼 [Supervisor] ¡Todas las familias procesadas! Terminando flujo.")
        return {"item_actual_id": "FIN"}
        
    print(f"\n👨‍💼 [Supervisor] Iniciando análisis para la Familia: {familia_pendiente} (Usando ref: {item_representativo})")
    
    # Reiniciamos las variables de control para que los agentes empiecen "limpios" con la nueva familia
    return {
        "item_actual_id": item_representativo, 
        "intentos_electrico": 0, "intentos_mecanico": 0, "intentos_accesorios": 0, "intentos_logistico": 0,
        "feedback_electrico": "", "feedback_mecanico": "", "feedback_accesorios": "", "feedback_logistico": "",
        "alertas_diseno": [],
        "datos_electricos": {}, "datos_mecanicos": {}, "datos_accesorios": {}, "datos_logisticos": {}
    }

def enrutar_supervisor(state: BotState):
    """ Función lógica que decide si ir al primer escuadrón o terminar. """
    if state.get("item_actual_id") == "FIN":
        return END 
    return "extractor_electrico"

# =============================================================================
# CONSTRUCCIÓN DEL FLUJO (Definición de Nodos y Conexiones)
# =============================================================================
flujo = StateGraph(BotState)

# --- DEFINICIÓN DE NODOS ---
# Cada nodo representa una pieza de código (agente o herramienta) que realiza una tarea específica.

# Fase Inicial: Preparación
flujo.add_node("extractor_inventario", nodo_extraer_inventario) # Saca la lista de trafos
flujo.add_node("creador_excel_global", nodo_crear_excel_inventario) # Genera resumen inicial en Excel
flujo.add_node("supervisor", nodo_supervisor_familias) # El jefe que decide qué familia sigue

# Fase de Análisis: Escuadrones Técnicos (Extractor + Revisor)
flujo.add_node("extractor_electrico", nodo_extractor_electrico)
flujo.add_node("revisor_electrico", nodo_revisor_electrico)

flujo.add_node("extractor_mecanico", nodo_extractor_mecanico)
flujo.add_node("revisor_mecanico", nodo_revisor_mecanico)

flujo.add_node("extractor_accesorios", nodo_extractor_accesorios)
flujo.add_node("revisor_accesorios", nodo_revisor_accesorios)

flujo.add_node("extractor_logistico", nodo_extractor_logistico)
flujo.add_node("revisor_logistico", nodo_revisor_logistico)

# Fase de Cierre: Generación de Entregables por Familia
flujo.add_node("ensamblador_word", nodo_generar_resumen_tipo) # Crea el informe Word consolidado
flujo.add_node("creador_ctg", nodo_crear_excel_ctg) # Genera el Excel detallado para CTG

# --- DEFINICIÓN DE ARISTAS (EDGES) ---
# Aquí se define el "camino" que sigue la información.

# 1. Punto de entrada y flujo inicial
flujo.set_entry_point("extractor_inventario")
flujo.add_edge("extractor_inventario", "creador_excel_global")
flujo.add_edge("creador_excel_global", "supervisor")

# 2. El Supervisor decide si empezar con los escuadrones o terminar
flujo.add_conditional_edges("supervisor", enrutar_supervisor)

# 3. SECUENCIA DE ESCUADRONES (Lógica: Extraer -> Revisar -> (Loop si hay error) -> Siguiente Escuadrón)

# Escuadrón Eléctrico: Luego de revisar, o reintenta o pasa al Mecánico
flujo.add_edge("extractor_electrico", "revisor_electrico")
flujo.add_conditional_edges("revisor_electrico", decidir_ruta_electrico, {
    "reintentar_electrico": "extractor_electrico", # Si el revisor no está satisfecho
    "fin_electrico": "extractor_mecanico"         # Si todo está OK
})

# Escuadrón Mecánico: Luego de revisar, o reintenta o pasa a Accesorios
flujo.add_edge("extractor_mecanico", "revisor_mecanico")
flujo.add_conditional_edges("revisor_mecanico", decidir_ruta_mecanico, {
    "reintentar_mecanico": "extractor_mecanico",
    "fin_mecanico": "extractor_accesorios"
})

# Escuadrón de Accesorios: Luego de revisar, o reintenta o pasa a Logístico
flujo.add_edge("extractor_accesorios", "revisor_accesorios")
flujo.add_conditional_edges("revisor_accesorios", decidir_ruta_accesorios, {
    "reintentar_accesorios": "extractor_accesorios",
    "fin_accesorios": "extractor_logistico"
})

# Escuadrón Logístico/Comercial: Al terminar, pasa al Ensamblador de Word
flujo.add_edge("extractor_logistico", "revisor_logistico")
flujo.add_conditional_edges("revisor_logistico", decidir_ruta_logistico, {
    "reintentar_logistico": "extractor_logistico",
    "fin_logistico": "ensamblador_word"
})

# 4. Generación de informes y retorno al Supervisor para la siguiente familia
flujo.add_edge("ensamblador_word", "creador_ctg") # Word generado -> Excel CTG generado
flujo.add_edge("creador_ctg", "supervisor")       # Familia terminada -> Volver al jefe para ver si hay más

# --- COMPILACIÓN ---
maquina_magnetron = flujo.compile()

# ==========================================
# METADATA
# tools_used: [langgraph]
# use_cases: [Orquestación del flujo principal, Definición de nodos y aristas]
# reusable_components: [nodo_supervisor_familias, maquina_magnetron]
# dependencies: [pip install langgraph]
# ==========================================
