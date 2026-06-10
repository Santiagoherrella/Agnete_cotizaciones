from src.schemas.state import BotState

def _inyectar_respuesta(campo: str, valor_humano: str, datos_elec: dict, datos_mec: dict) -> None:
    """Clasifica el campo y guarda la respuesta humana con trazabilidad."""
    if "fluido" in campo or "aceite" in campo:
        datos_mec[campo] = {"valor": valor_humano, "origen": "HITL (Intervencion Humana)"}
    else:
        datos_elec[campo] = {"valor": valor_humano, "origen": "HITL (Intervencion Humana)"}

def nodo_human_in_the_loop(state: BotState):
    print("\n" + "🛑" * 30)
    print("👤 [HUMAN IN THE LOOP] INTERVENCIÓN REQUERIDA")
    print("El Auditor SDM ha detenido el proceso. Faltan datos críticos.")
    
    # Extraemos los diccionarios actuales
    datos_elec = state.get("datos_electricos", {})
    datos_mec = state.get("datos_mecanicos", {})
    faltantes = state.get("campos_faltantes_sdm", [])
    respuestas_humanas = state.get("respuestas_humanas", {})
    modo_interaccion = state.get("modo_interaccion", "cli")

    if respuestas_humanas:
        for campo in faltantes:
            valor_humano = str(respuestas_humanas.get(campo, "")).strip()
            if not valor_humano:
                raise ValueError(f"Falta la respuesta humana para el campo '{campo}'.")
            _inyectar_respuesta(campo, valor_humano, datos_elec, datos_mec)
    else:
        if modo_interaccion == "web":
            raise ValueError("Se requiere 'respuestas_humanas' para continuar la intervencion en modo web.")

        # Recorremos lo que falta y pedimos input en la terminal
        for campo in faltantes:
            valor_humano = input(f"👉 Por favor, ingrese el valor técnico para '{campo}': ")
            _inyectar_respuesta(campo, valor_humano, datos_elec, datos_mec)
            
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
