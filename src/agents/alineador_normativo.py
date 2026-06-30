from src.tools.normalizador_sdm import MotorNormalizacionSDM
from src.schemas.state import BotState
from src.utils.logger import get_logger

logger = get_logger("AlineadorNormativo")

# Instanciamos el motor globalmente (Usa la caché de RAM)
motor_sdm = MotorNormalizacionSDM()

def nodo_alineador_normativo(state: BotState):
    """
    Cruza los datos crudos extraídos por los escuadrones contra 
    Cruza los datos crudos extraídos por los escuadrones contra 
    las tablas SQL maestras de Magnetrón para obtener los IDs del SDM.
    """
    logger.info("\n[Alineador Normativo] Mapeando texto a IDs relacionales (Fase A)...")
    
    # 1. Recuperar los datos crudos de la memoria
    elec = state.get("datos_electricos", {})
    logi = state.get("datos_logisticos", {})
    
# 2. Extraer las variables objetivo
    # Le pasamos el lugar de entrega (Ej: "Ozark, Al 36361") para que el motor deduzca el país
    lugar_entrega = logi.get("lugar_entrega_incoterm", {}).get("valor", "No especificado")
    pais_crudo = lugar_entrega 
    
    norma_cruda = logi.get("normas_aplicables", {}).get("valor", "No especificado")
    potencia_cruda = elec.get("capacidad_nominal", {}).get("valor", "No especificado")
    vp_crudo = elec.get("voltaje_primario", {}).get("valor", "No especificado")
    vs_crudo = elec.get("voltaje_secundario", {}).get("valor", "No especificado")
    
    texto_eficiencia = elec.get("eficiencia", {}).get("valor", "No especificado")
    texto_perdidas = elec.get("evaluacion_perdidas", {}).get("valor", "No especificado")

    # 3. CORRECCIÓN: Desempacar las variables
    id_pais, txt_pais, alerta_pais = motor_sdm.normalizar_pais(pais_crudo)
    id_norma, txt_norma, alerta_norma = motor_sdm.normalizar_norma(norma_cruda, id_pais)
    id_kva, txt_kva, alerta_kva = motor_sdm.normalizar_potencia(potencia_cruda)
    id_vp, txt_vp, e1, e11, alerta_vp = motor_sdm.normalizar_voltaje_primario(vp_crudo)
    id_vs, txt_vs, e2, e21, alerta_vs = motor_sdm.normalizar_voltaje_secundario(vs_crudo)
    
    # Clasificador con LLM
    clasificacion_llm = motor_sdm.clasificar_eficiencia_y_toc(texto_eficiencia, texto_perdidas)
    
    # 4. Inyectar alertas si los datos del pliego son inventados o no estandarizados
    alertas_nuevas = [a for a in [alerta_pais, alerta_norma, alerta_kva, alerta_vp, alerta_vs] if a]
    alertas_actuales = state.get("alertas_diseno", []) + alertas_nuevas
    
    # 5. Guardar Separado: Frontend (Textos para el Detalle) vs Backend (IDs para el SDM/Cálculos)
    datos_sdm = {
        "textos_limpios": {
            "pais": txt_pais,
            "norma": txt_norma,
            "potencia_kva": txt_kva,
            "voltaje_primario": txt_vp,
            "voltaje_secundario": txt_vs
        },
        "ids_internos": {
            "id_pais": id_pais,
            "id_norma": id_norma,
            "id_kva": id_kva,
            "id_vp": id_vp,
            "id_vs": id_vs
        },
        "voltajes_duales": {
            "e1": e1,
            "e11": e11,
            "e2": e2,
            "e21": e21
        },
        "clasificacion_ia": clasificacion_llm
    }
    
    # Actualizar el estado global
    state["datos_normalizados_sdm"] = datos_sdm
    
    # Imprimir en consola para validación visual
    logger.info("\n   --- IDs Internos ---")
    for k, v in datos_sdm["ids_internos"].items():
        if v: logger.info(f"    {k.upper()}: {v}")
        
    logger.info("\n   --- Textos Limpios ---")
    for k, v in datos_sdm["textos_limpios"].items():
        if v: logger.info(f"    {k.upper()}: {v}")
        
    logger.info(f"\n   --- Clasificación IA ---")
    logger.info(f"    TOC Aplica: {clasificacion_llm.get('aplica_capitalizacion')}")
    logger.info(f"    Norma Eficiencia: {clasificacion_llm.get('norma_eficiencia_clasificada')}")

    for alerta in alertas_nuevas:
        logger.info(f"   {alerta}")

    return {
        "alertas_diseno": alertas_actuales,
        "datos_normalizados_sdm": datos_sdm
    }