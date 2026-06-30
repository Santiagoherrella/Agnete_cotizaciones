from src.schemas.state import BotState
from langgraph.graph import StateGraph, END
from src.utils.logger import get_logger
logger = get_logger("Supervisor")


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
            # Seleccionamos un ítem de esta familia para que sirva de guía
            item_representativo = next(t["item_id"] for t in inventario if t["tipo_transformador"] == familia)
            break
            
    # 3. Si no hay familias pendientes, terminamos el flujo global
    if not familia_pendiente:
        logger.info(f"\n [Supervisor] ¡Todas las familias procesadas! Terminando flujo.")
        return {"item_actual_id": "FIN"}
        
    logger.info(f"\n [Supervisor] Iniciando análisis para la Familia: {familia_pendiente} (Usando ref: {item_representativo})")
    
    # ==========================================
    # 🔗 LA SOLUCIÓN AL BUCLE INFINITO
    # ==========================================
    # Agregamos la familia a la lista de completados INMEDIATAMENTE
    nuevos_completados = completados + [familia_pendiente]
    
    # Reiniciamos las variables de control para que los agentes empiecen "limpios"
    return {
        "item_actual_id": item_representativo, 
        "resumenes_completados": nuevos_completados,  # <--- ESTO ROMPE EL BUCLE
        "intentos_electrico": 0, "intentos_mecanico": 0, "intentos_accesorios": 0, "intentos_logistico": 0,
        "feedback_electrico": "", "feedback_mecanico": "", "feedback_accesorios": "", "feedback_logistico": "",
        "alertas_diseno": [],
        "datos_electricos": {}, "datos_mecanicos": {}, "datos_accesorios": {}, "datos_logisticos": {}
    }
def enrutar_supervisor(state: BotState):
    """ Función lógica que decide si ir al primer escuadrón o terminar. """
    if state.get("item_actual_id") == "FIN":
        return END 
    return "decidir_ruta_produccion"
