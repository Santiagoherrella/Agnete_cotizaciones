from langgraph.graph import StateGraph, END
from src.schemas.state import BotState

from src.agents.inventario import nodo_extraer_inventario
from src.tools.exportador import nodo_crear_excel_inventario, nodo_crear_excel_ctg
from src.agents.resumen_general import nodo_generar_resumen_tipo # Importamos el Ensamblador

from src.agents.escuadron_electrico import nodo_extractor_electrico, nodo_revisor_electrico, decidir_ruta_electrico
from src.agents.escuadron_mecanico import nodo_extractor_mecanico, nodo_revisor_mecanico, decidir_ruta_mecanico
from src.agents.escuadron_accesorios import nodo_extractor_accesorios, nodo_revisor_accesorios, decidir_ruta_accesorios
from src.agents.escuadron_logistico import nodo_extractor_logistico, nodo_revisor_logistico, decidir_ruta_logistico

from src.agents.auditor_sdm import nodo_auditor_sdm
from src.tools.exportador_sdm import nodo_generar_json_sdm

from src.agents.intervencion_humana import nodo_human_in_the_loop, decidir_ruta_auditor

from src.agents.agente_comercial import nodo_analista_comercial, nodo_tabulador_comercial
from src.tools.exportador_comercial import nodo_word_comercial, nodo_excel_comercial

from src.agents.configuraciones import validador_inicial, router_ingenieria, router_comercial, router_sdm
from src.agents.supervisor import nodo_supervisor_familias

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

def decidir_salida_supervisor(state: BotState):
    """Decide si el supervisor tiene más trabajo o si ya terminamos todo."""
    if state.get("item_actual_id") == "FIN":
        return "finalizar"
    return "procesar_familia"

def decidir_bypass_comercial(state: BotState):
    """Consulta si debe ir a comercial o saltar directo a ingeniería."""
    config = state.get("configuracion", {})
    if config.get("modo") == "solo_ingenieria":
        return "saltar_a_ingenieria"
    return "ir_a_comercial"

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

# Generación de Entregables Técnicos por Familia
flujo.add_node("ensamblador_word", nodo_generar_resumen_tipo) # Crea el informe Word consolidado
flujo.add_node("creador_ctg", nodo_crear_excel_ctg) # Genera el Excel detallado para CTG

# Generación de Entregables Comerciales
flujo.add_node("analista_comercial", nodo_analista_comercial) # Agente de resumen ejecutivo
flujo.add_node("tabulador_comercial", nodo_tabulador_comercial) # Agente de checklist
flujo.add_node("ensamblador_comercial_word", nodo_word_comercial)  # Genera el informe Word comercial
flujo.add_node("exportador_comercial_excel", nodo_excel_comercial) # Genera el Excel comercial 

# Generación de JSON para el Software SDM
flujo.add_node("auditor_sdm", nodo_auditor_sdm) # Auditor de SDM
flujo.add_node("generador_sdm", nodo_generar_json_sdm) # Generador de  JSON SDM

# Agregamos el nodo humano
flujo.add_node("intervencion_humana", nodo_human_in_the_loop) # Intervención humana

flujo.add_node("validador_inicial", validador_inicial) # Validador inicial
flujo.add_node("router_ingenieria", router_ingenieria) # Router de ingeniería
flujo.add_node("router_comercial", router_comercial) # Router comercial
flujo.add_node("router_sdm", router_sdm) # Router SDM   

# --- DEFINICIÓN DE ARISTAS (EDGES) ---
# Aquí se define el "camino" que sigue la información.

# 1. Validación de seguridad ANTES de arrancar
flujo.set_conditional_entry_point(validador_inicial, {
    "abortar": END,
    "continuar": "extractor_inventario"
})

flujo.add_edge("extractor_inventario", "creador_excel_global")
flujo.add_edge("creador_excel_global", "supervisor")

flujo.add_conditional_edges("supervisor", router_ingenieria, {
        "finalizar": END,
        "ir_a_ingenieria": "extractor_electrico",
        "saltar_a_comercial": "analista_comercial"
    })
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

# Escuadrón Logístico/Comercial
flujo.add_edge("extractor_logistico", "revisor_logistico")


# 3. Salida de Logístico -> Comercial, SDM, o Documentos Finales
flujo.add_conditional_edges("revisor_logistico", router_comercial, {
    "reintentar": "extractor_logistico",
    "ir_a_comercial": "analista_comercial",
    "saltar_a_sdm": "auditor_sdm",
    "saltar_a_documentos_tecnicos": "ensamblador_word",
    "terminar_familia": "supervisor"
})

# Flujo Comercial Secuencial
flujo.add_edge("analista_comercial", "tabulador_comercial")
flujo.add_edge("tabulador_comercial", "ensamblador_comercial_word")
flujo.add_edge("ensamblador_comercial_word", "exportador_comercial_excel")

# Una vez generados los documentos comerciales, volvemos al flujo de ingeniería (SDM)
# 4. Salida de Comercial -> SDM, Documentos Finales, o Supervisor
flujo.add_conditional_edges("exportador_comercial_excel", router_sdm, {
    "ir_a_sdm": "auditor_sdm",
    "saltar_a_documentos_tecnicos": "ensamblador_word", 
    "terminar_familia": "supervisor" 
})


# 2. El Auditor decide si va al SDM o pide ayuda
flujo.add_conditional_edges("auditor_sdm", decidir_ruta_auditor, {
    "ir_a_sdm": "generador_sdm",
    "pedir_ayuda_humana": "intervencion_humana"
})

# 3. El humano reanuda hacia el SDM
flujo.add_edge("intervencion_humana", "generador_sdm")

# 4. Secuencia final estricta de documentos
flujo.add_edge("generador_sdm", "ensamblador_word")
flujo.add_edge("ensamblador_word", "creador_ctg")
flujo.add_edge("creador_ctg", "supervisor")


# --- COMPILACIÓN ---
maquina_magnetron = flujo.compile()

# ==========================================
# METADATA
# tools_used: [langgraph]
# use_cases: [Orquestación del flujo principal, Definición de nodos y aristas]
# reusable_components: [nodo_supervisor_familias, maquina_magnetron]
# dependencies: [pip install langgraph]
# ==========================================
