from src.schemas.state import BotState

def nodo_human_in_the_loop(state: BotState):
    print("\n" + "🛑" * 30)
    print("👤 [HUMAN IN THE LOOP] INTERVENCIÓN REQUERIDA")
    print("El Auditor SDM ha detenido el proceso. Faltan datos críticos.")
    
    # Extraemos los diccionarios actuales
    datos_elec = state.get("datos_electricos", {})
    datos_mec = state.get("datos_mecanicos", {})
    faltantes = state.get("campos_faltantes_sdm", [])
    
    # Recorremos lo que falta y pedimos input en la terminal
    for campo in faltantes:
        valor_humano = input(f"👉 Por favor, ingrese el valor técnico para '{campo}': ")
        
        # Inyectamos el dato donde corresponde con una etiqueta de auditoría
        if "fluido" in campo or "aceite" in campo:
            datos_mec[campo] = {"valor": valor_humano, "origen": "HITL (Intervención Humana)"}
        else:
            # Asumimos que BIL, impedancia, voltajes son eléctricos
            datos_elec[campo] = {"valor": valor_humano, "origen": "HITL (Intervención Humana)"}
            
    print("✅ [HUMAN IN THE LOOP] Datos actualizados. Reanudando proceso hacia el SDM...")
    print("🛑" * 30 + "\n")
    
    return {
        "datos_electricos": datos_elec,
        "datos_mecanicos": datos_mec,
        "auditoria_sdm_ok": True, # Forzamos la aprobación porque el humano ya validó
        "campos_faltantes_sdm": [] # Vaciamos la lista
    }

def decidir_ruta_auditor(state: BotState):
    """ Enrutador: ¿Va directo al SDM o pide ayuda al humano? """
    if state.get("auditoria_sdm_ok", False):
        return "ir_a_sdm"
    return "pedir_ayuda_humana"