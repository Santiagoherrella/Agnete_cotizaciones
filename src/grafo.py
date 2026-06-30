from langgraph.graph import StateGraph, END
from src.schemas.state import BotState

from src.agents.inventario import nodo_extraer_inventario
from src.tools.exportador import nodo_crear_excel_inventario, nodo_crear_excel_ctg
from src.agents.resumen_general import nodo_generar_resumen_tipo 

from src.agents.escuadron_electrico import nodo_extractor_electrico, nodo_revisor_electrico, decidir_ruta_electrico
from src.agents.escuadron_mecanico import nodo_extractor_mecanico, nodo_revisor_mecanico, decidir_ruta_mecanico
from src.agents.escuadron_accesorios import nodo_extractor_accesorios, nodo_revisor_accesorios, decidir_ruta_accesorios
from src.agents.escuadron_logistico import nodo_extractor_logistico, nodo_revisor_logistico

from src.agents.auditor_sdm import nodo_auditor_sdm
from src.tools.exportador_sdm import nodo_generar_json_sdm

from src.agents.agente_comercial import nodo_analista_comercial, nodo_tabulador_comercial
from src.tools.exportador_comercial import nodo_word_comercial, nodo_excel_comercial

from src.agents.configuraciones import validador_inicial, router_ingenieria, router_comercial, router_sdm, router_post_sdm, router_post_word
from src.agents.supervisor import nodo_supervisor_familias
from src.agents.alineador_normativo import nodo_alineador_normativo

# =============================================================================
# CONSTRUCCIÓN DEL FLUJO 
# =============================================================================
flujo = StateGraph(BotState)

# --- DEFINICIÓN DE NODOS ---
flujo.add_node("extractor_inventario", nodo_extraer_inventario) 
flujo.add_node("creador_excel_global", nodo_crear_excel_inventario) 
flujo.add_node("supervisor", nodo_supervisor_familias) 

flujo.add_node("extractor_electrico", nodo_extractor_electrico)
flujo.add_node("revisor_electrico", nodo_revisor_electrico)

flujo.add_node("extractor_mecanico", nodo_extractor_mecanico)
flujo.add_node("revisor_mecanico", nodo_revisor_mecanico)

flujo.add_node("extractor_accesorios", nodo_extractor_accesorios)
flujo.add_node("revisor_accesorios", nodo_revisor_accesorios)

flujo.add_node("extractor_logistico", nodo_extractor_logistico)
flujo.add_node("revisor_logistico", nodo_revisor_logistico)

flujo.add_node("ensamblador_word", nodo_generar_resumen_tipo) 
flujo.add_node("creador_ctg", nodo_crear_excel_ctg) 

flujo.add_node("analista_comercial", nodo_analista_comercial) 
flujo.add_node("tabulador_comercial", nodo_tabulador_comercial) 
flujo.add_node("ensamblador_comercial_word", nodo_word_comercial)  
flujo.add_node("exportador_comercial_excel", nodo_excel_comercial) 

flujo.add_node("alineador_normativo", nodo_alineador_normativo)
flujo.add_node("auditor_sdm", nodo_auditor_sdm) 
flujo.add_node("generador_sdm", nodo_generar_json_sdm) 

# --- DEFINICIÓN DE ARISTAS (EDGES) ---
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

flujo.add_edge("extractor_electrico", "revisor_electrico")
flujo.add_conditional_edges("revisor_electrico", decidir_ruta_electrico, {
    "reintentar_electrico": "extractor_electrico",
    "fin_electrico": "extractor_mecanico"
})

flujo.add_edge("extractor_mecanico", "revisor_mecanico")
flujo.add_conditional_edges("revisor_mecanico", decidir_ruta_mecanico, {
    "reintentar_mecanico": "extractor_mecanico",
    "fin_mecanico": "extractor_accesorios"
})

flujo.add_edge("extractor_accesorios", "revisor_accesorios")
flujo.add_conditional_edges("revisor_accesorios", decidir_ruta_accesorios, {
    "reintentar_accesorios": "extractor_accesorios",
    "fin_accesorios": "extractor_logistico"
})

flujo.add_edge("extractor_logistico", "revisor_logistico")
flujo.add_conditional_edges("revisor_logistico", router_comercial, {
    "reintentar": "extractor_logistico",
    "ir_a_comercial": "analista_comercial",
    "saltar_a_sdm": "alineador_normativo",
    "saltar_a_documentos_tecnicos": "ensamblador_word",
    "saltar_a_ctg": "creador_ctg",
    "terminar_familia": "supervisor"
})

flujo.add_edge("analista_comercial", "tabulador_comercial")
flujo.add_edge("tabulador_comercial", "ensamblador_comercial_word")
flujo.add_edge("ensamblador_comercial_word", "exportador_comercial_excel")

flujo.add_conditional_edges("exportador_comercial_excel", router_sdm, {
    "ir_a_sdm": "alineador_normativo",
    "saltar_a_documentos_tecnicos": "ensamblador_word", 
    "saltar_a_ctg": "creador_ctg",
    "terminar_familia": "supervisor" 
})

# ===============================================
# NUEVO FLUJO SDM (SIN HUMAN IN THE LOOP)
# ===============================================
flujo.add_edge("alineador_normativo", "auditor_sdm")
flujo.add_edge("auditor_sdm", "generador_sdm")  # Pasa directo a exportar el JSON

flujo.add_conditional_edges("generador_sdm", router_post_sdm, {
    "ir_a_word": "ensamblador_word",
    "ir_a_ctg": "creador_ctg",
    "terminar_familia": "supervisor"
})

flujo.add_conditional_edges("ensamblador_word", router_post_word, {
    "ir_a_ctg": "creador_ctg",
    "terminar_familia": "supervisor"
})

flujo.add_edge("creador_ctg", "supervisor")

maquina_magnetron = flujo.compile()