from src.tools.normalizador_sdm import MotorNormalizacionSDM
from src.schemas.state import BotState

# Instanciamos el motor globalmente (Usa la caché de RAM)
motor_sdm = MotorNormalizacionSDM()

def nodo_alineador_normativo(state: BotState):
    """
    Cruza los datos crudos extraídos por los escuadrones contra 
    las tablas SQL maestras de Magnetrón para obtener los IDs del SDM.
    """
    print("\n⚙️ [Alineador Normativo] Mapeando texto a IDs relacionales (Fase A)...")
    
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
    # 3. 🚀 CORRECCIÓN: Desempacar las 3 variables (ID, Texto_Limpio, Alerta)
    id_pais, txt_pais, alerta_pais = motor_sdm.normalizar_pais(pais_crudo)
    id_norma, txt_norma, alerta_norma = motor_sdm.normalizar_norma(norma_cruda, id_pais)
    id_kva, txt_kva, alerta_kva = motor_sdm.normalizar_potencia(potencia_cruda)
    id_vp, txt_vp, alerta_vp = motor_sdm.normalizar_voltaje_primario(vp_crudo)
    id_vs, txt_vs, alerta_vs = motor_sdm.normalizar_voltaje_secundario(vs_crudo)
    
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
        }
    }
    
    # Actualizar el estado global
    state["datos_normalizados_sdm"] = datos_sdm
    
    # Imprimir en consola para validación visual
    print("\n   --- IDs Internos ---")
    for k, v in datos_sdm["ids_internos"].items():
        if v: print(f"   ✅ {k.upper()}: {v}")
        
    print("\n   --- Textos Limpios ---")
    for k, v in datos_sdm["textos_limpios"].items():
        if v: print(f"   📄 {k.upper()}: {v}")
        
    for alerta in alertas_nuevas:
        print(f"   {alerta}")

    return {
        "alertas_diseno": alertas_actuales,
        "datos_normalizados_sdm": datos_sdm
    }