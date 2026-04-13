from langgraph.graph import StateGraph, END
from src.schemas.state import BotState

from src.agents.inventario import nodo_extraer_inventario
from src.tools.exportador import nodo_crear_excel_inventario, nodo_crear_excel_ctg
from src.agents.resumen_general import nodo_generar_resumen_tipo # Importamos el Ensamblador

from src.agents.escuadron_electrico import nodo_extractor_electrico, nodo_revisor_electrico, decidir_ruta_electrico
from src.agents.escuadron_mecanico import nodo_extractor_mecanico, nodo_revisor_mecanico, decidir_ruta_mecanico
from src.agents.escuadron_accesorios import nodo_extractor_accesorios, nodo_revisor_accesorios, decidir_ruta_accesorios
from src.agents.escuadron_logistico import nodo_extractor_logistico, nodo_revisor_logistico, decidir_ruta_logistico

# ==========================================
# EL SUPERVISOR (Controlador por Familias)
# ==========================================
def nodo_supervisor_familias(state: BotState):
    inventario = state.get("inventario_global", [])
    completados = state.get("resumenes_completados", [])
    
    # 1. Obtener familias únicas del inventario
    familias_unicas = list(set([t["tipo_transformador"] for t in inventario if t.get("tipo_transformador") != "No especificado"]))
    
    # 2. Buscar si hay alguna familia que aún no tenga resumen
    familia_pendiente = None
    item_representativo = None
    
    for familia in familias_unicas:
        if familia not in completados:
            familia_pendiente = familia
            # Tomamos el primer trafo de esta familia como el "Lector" del pliego
            item_representativo = next(t["item_id"] for t in inventario if t["tipo_transformador"] == familia)
            break
            
    # 3. Si no hay familias pendientes, terminamos
    if not familia_pendiente:
        print(f"\n👨‍💼 [Supervisor] ¡Todas las familias procesadas! Terminando flujo.")
        return {"item_actual_id": "FIN"}
        
    print(f"\n👨‍💼 [Supervisor] Iniciando análisis para la Familia: {familia_pendiente} (Usando ref: {item_representativo})")
    
    # Reiniciamos la memoria para que los agentes trabajen limpios en esta nueva familia
    return {
        "item_actual_id": item_representativo, 
        "intentos_electrico": 0, "intentos_mecanico": 0, "intentos_accesorios": 0, "intentos_logistico": 0,
        "feedback_electrico": "", "feedback_mecanico": "", "feedback_accesorios": "", "feedback_logistico": "",
        "alertas_diseno": [],
        "datos_electricos": {}, "datos_mecanicos": {}, "datos_accesorios": {}, "datos_logisticos": {}
    }

def enrutar_supervisor(state: BotState):
    if state.get("item_actual_id") == "FIN":
        return END 
    return "extractor_electrico"

# ==========================================
# CONSTRUCCIÓN DEL FLUJO (La Pista de Carreras)
# ==========================================
flujo = StateGraph(BotState)

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

# NUEVO NODO: El ensamblador del Word
''
flujo.add_node("ensamblador_word", nodo_generar_resumen_tipo)
flujo.add_node("creador_ctg", nodo_crear_excel_ctg)

# Conexiones
flujo.set_entry_point("extractor_inventario")
flujo.add_edge("extractor_inventario", "creador_excel_global")
flujo.add_edge("creador_excel_global", "supervisor")
flujo.add_conditional_edges("supervisor", enrutar_supervisor)

flujo.add_edge("extractor_electrico", "revisor_electrico")
flujo.add_conditional_edges("revisor_electrico", decidir_ruta_electrico, {"reintentar_electrico": "extractor_electrico", "fin_electrico": "extractor_mecanico"})

flujo.add_edge("extractor_mecanico", "revisor_mecanico")
flujo.add_conditional_edges("revisor_mecanico", decidir_ruta_mecanico, {"reintentar_mecanico": "extractor_mecanico", "fin_mecanico": "extractor_accesorios"})

flujo.add_edge("extractor_accesorios", "revisor_accesorios")
flujo.add_conditional_edges("revisor_accesorios", decidir_ruta_accesorios, {"reintentar_accesorios": "extractor_accesorios", "fin_accesorios": "extractor_logistico"})

# CAMBIO CRUCIAL AQUÍ: El logístico ahora pasa la batuta al Ensamblador de Word
flujo.add_edge("extractor_logistico", "revisor_logistico")
flujo.add_conditional_edges("revisor_logistico", decidir_ruta_logistico, {
    "reintentar_logistico": "extractor_logistico",
    "fin_logistico": "ensamblador_word" # Pasa al creador del docx
})

# Word pasa a CTG
flujo.add_edge("ensamblador_word", "creador_ctg")

# CTG avisa al Supervisor que terminamos con esta familia
flujo.add_edge("creador_ctg", "supervisor")

maquina_magnetron = flujo.compile()
