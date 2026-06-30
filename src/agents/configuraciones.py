from src.schemas.state import BotState
from src.agents.escuadron_logistico import decidir_ruta_logistico # <--- Faltaba esto
from src.utils.logger import get_logger
logger = get_logger("Configuraciones")


def validador_inicial(state: BotState):
    """Evita que el bot arranque si no hay nada que hacer."""
    conf = state.get("configuracion", {})
    # Si todos los interruptores están en False, cancelamos
    if not any([conf.get("ejecutar_ingenieria"), conf.get("ejecutar_comercial"), conf.get("ejecutar_sdm")]):
        logger.info(" [ERROR] No se seleccionó ninguna tarea. Abortando para ahorrar tokens.")
        return "abortar"
    return "continuar"

def router_ingenieria(state: BotState):
    """Decide hacia qué gran bloque saltar desde el supervisor."""
    # Si el supervisor ya no encuentra familias, termina todo.
    if state.get("item_actual_id") == "FIN": 
        return "finalizar"
    
    conf = state.get("configuracion", {})
    
    # Evalúa en orden de prioridad:
    if conf.get("ejecutar_ingenieria"): 
        return "ir_a_ingenieria"
        
    if conf.get("ejecutar_comercial"): 
        return "saltar_a_comercial"

    return "finalizar"

def router_comercial(state: BotState):
    """Revisa primero si hubo error técnico, si no, decide el salto comercial."""
    conf = state.get("configuracion", {})

    # 1. ¿El escuadrón logístico falló y necesita repetir? (ESTO FALTABA)
    if decidir_ruta_logistico(state) == "reintentar_logistico":
        return "reintentar"
        
    # 2. Si terminó bien, miramos los interruptores
    if conf.get("ejecutar_comercial"):
        return "ir_a_comercial"
        
    # 3. Si comercial está apagado, pero SDM está encendido
    if conf.get("ejecutar_sdm"):
        return "saltar_a_sdm"

    # 4. Si comercial y SDM están apagados, pero Ingeniería está encendido (Vamos directo a armar el Word)
    if conf.get("ejecutar_ingenieria"):
        return "saltar_a_documentos_tecnicos"
        
    # 5. Si no hay nada más que hacer
    return "terminar_familia"    

def router_sdm(state: BotState):
    conf = state.get("configuracion", {})
    """Decide si genera el JSON para el software de diseño."""
    if conf.get("ejecutar_sdm") and conf.get("ejecutar_ingenieria"):
        return "ir_a_sdm"
    
    # 2. Si el SDM está apagado, pero Ingeniería está encendido, debe armar el Word Técnico
    if conf.get("ejecutar_ingenieria"):
        return "saltar_a_documentos_tecnicos"
    
    return "terminar_familia"

def router_post_sdm(state: BotState):
    """Decide hacia dónde ir después de generar el JSON del SDM."""
    config = state.get("configuracion", {})
    if config.get("ejecutar_documentos_tecnicos", True):
        return "ir_a_word"
    elif config.get("ejecutar_ctg", True):
        return "ir_a_ctg"
    return "terminar_familia"

def router_post_word(state: BotState):
    """Decide hacia dónde ir después de ensamblar el Word."""
    config = state.get("configuracion", {})
    if config.get("ejecutar_ctg", True):
        return "ir_a_ctg"
    return "terminar_familia"