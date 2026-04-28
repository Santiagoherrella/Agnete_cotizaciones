import json
import os
from src.schemas.state import BotState

def extraer_valor_limpio(campo_data):
    """Extrae el valor sin importar si viene como diccionario o texto plano."""
    if isinstance(campo_data, dict):
        return campo_data.get("valor", "No especificado")
    return str(campo_data) if campo_data else "No especificado"

def nodo_generar_json_sdm(state: BotState):
    if not state.get("auditoria_sdm_ok", False):
        print("⚠️ [Exportador SDM] Saltando generación por falta de datos críticos.")
        return {}
    
    # 1. Traemos la memoria de los escuadrones (Datos MACRO / Generales)
    elec = state.get("datos_electricos", {})
    mec = state.get("datos_mecanicos", {})
    logi = state.get("datos_logisticos", {})
    
    # 2. Traemos el inventario (Datos MICRO / Específicos por trafo)
    inventario = state.get("inventario_global", [])
    familia_actual = state.get("item_actual_id", "")
    
    carpeta_sdm = "data/outputs/SDM_Files"
    os.makedirs(carpeta_sdm, exist_ok=True)
    rutas_generadas = []
    
    # 3. Filtramos el inventario para no mezclar familias distintas
    equipos_familia = []
    for equipo in inventario:
        tipo_inv = equipo.get("tipo_transformador", "")
        if tipo_inv in familia_actual or familia_actual in tipo_inv:
            equipos_familia.append(equipo)
            
    # Fallback de seguridad: si no logra cruzar los nombres, procesa todo el inventario
    if not equipos_familia:
        equipos_familia = inventario

    # 4. 🚀 BUCLE MÁGICO: Crear un JSON por CADA transformador
    for idx, equipo in enumerate(equipos_familia):
        
        # Tomamos la potencia y voltajes EXACTOS de este ítem del inventario
        potencia_especifica = equipo.get("potencia", extraer_valor_limpio(elec.get("capacidad_nominal")))
        voltaje_pri_especifico = equipo.get("voltaje_primario", extraer_valor_limpio(elec.get("voltajes_nominales")))
        voltaje_sec_especifico = equipo.get("voltaje_secundario", extraer_valor_limpio(elec.get("voltaje_secundario")))
        
        datos = {
            "software": "SDM - Magnetron",
            "identificador_pliego": equipo.get("item_id", f"Trafo_{idx+1}"),
            "cantidad_solicitada": equipo.get("cantidad", 1),
            "parametros_diseno": {
                # --- DATOS ESPECÍFICOS DEL TRANSFORMADOR ---
                "potencia_kva": str(potencia_especifica),
                "voltaje_primario": str(voltaje_pri_especifico),
                "voltaje_secundario": str(voltaje_sec_especifico),
                
                # --- DATOS GENERALES DE LA FAMILIA ---
                "bil_primario": extraer_valor_limpio(elec.get("bil_primario", {}).get("valor", "")),
                "bil_secundario": extraer_valor_limpio(elec.get("bil_secundario", {}).get("valor", "")),
                "impedancia_porcentaje": extraer_valor_limpio(elec.get("impedancia_cortocircuito", {}).get("valor", "")),
                "tipo_aceite": extraer_valor_limpio(mec.get("fluido_dielectrico", {}).get("valor", "")),
                "perdidas_no_carga": extraer_valor_limpio(elec.get("perdidas_no_carga", {}).get("valor", "")),
                "perdidas_carga": extraer_valor_limpio(elec.get("perdidas_carga", {}).get("valor", "")),
                "perdidas_totales": extraer_valor_limpio(elec.get("perdidas_totales", {}).get("valor", "")),
                "eficiencia": extraer_valor_limpio(elec.get("eficiencia", {}).get("valor", "")),
                "conmutable":extraer_valor_limpio(elec.get("regulacion_taps", {}).get("valor", "")),
                "Alto_especifico":extraer_valor_limpio(mec.get("alto_especifico", {}).get("valor", "")),
                "Ancho_especifico":extraer_valor_limpio(mec.get("ancho_especifico", {}).get("valor", "")),
                "Largo_especifico":extraer_valor_limpio(mec.get("largo_especifico", {}).get("valor", "")),
                "Peso_especifico":extraer_valor_limpio(mec.get("dimensiones_peso_limites", {}).get("valor", "")),
                "certificación_ul":extraer_valor_limpio(logi.get("certificacion_ul", {}).get("valor", ""))
            }
        }
        
        # 5. Creamos un nombre de archivo único para que no se sobreescriban
        # Ej: SDM_ENTRY_75kVA_Item1.json
        potencia_limpia = str(potencia_especifica).replace(" ", "").replace("/", "-")
        nombre_archivo = f"SDM_ENTRY_{potencia_limpia}_{equipo.get('item_id', f'Item{idx+1}')}.json"
        
        # Quitamos caracteres especiales que Windows/Mac no permiten en archivos
        nombre_archivo = "".join([c for c in nombre_archivo if c.isalnum() or c in ['_', '.', '-']])
        
        ruta = os.path.join(carpeta_sdm, nombre_archivo)
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            
        rutas_generadas.append(ruta)
        print(f"🚀 [SDM] Archivo generado para trafo de {potencia_especifica}: {ruta}")
        
    return {"rutas_sdm_json": rutas_generadas}