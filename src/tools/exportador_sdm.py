import json
import os
import re
from src.schemas.state import BotState
from src.utils.logger import get_logger
logger = get_logger("ExportadorSdm")


def extraer_valor_limpio(campo_data):
    """Extrae el valor sin importar si viene como diccionario o texto plano."""
    if isinstance(campo_data, dict):
        return campo_data.get("valor", "No especificado")
    return str(campo_data) if campo_data else "No especificado"

def extraer_numero_limpio(campo_data):
    """Extrae el primer valor numérico encontrado en el string."""
    valor = extraer_valor_limpio(campo_data)
    if valor == "No especificado" or not valor:
        return None
    # Eliminar comas usadas como separador de miles si las hay
    texto_limpio = str(valor).replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", texto_limpio)
    if match:
        num_str = match.group()
        if num_str == ".": return None
        return float(num_str)
    return None

def buscar_variante(variantes, potencia_str):
    """Busca los parámetros específicos para una potencia solicitada."""
    if not variantes or not isinstance(variantes, list):
        return {}
    # Intentar match por número extraído
    num_pot = extraer_numero_limpio(potencia_str)
    if num_pot is not None:
        for v in variantes:
            if extraer_numero_limpio(v.get("potencia_kva", "")) == num_pot:
                return v
    return {}

def auditar_certificaciones(certificaciones_extraidas, tipo_trafo, fases_num, kva, material):
    """Evalúa las certificaciones requeridas contra las reglas de negocio."""
    cert_lower = str(certificaciones_extraidas).lower()
    tipo_lower = str(tipo_trafo).lower()
    material_lower = str(material).lower()
    
    resultado = {
        "texto_extraido": certificaciones_extraidas,
        "alertas_criticas": [],
        "notas_informativas": [],
        "ul_aplica": False,
        "ul_detalle": "No aplica"
    }
    
    if cert_lower == "no especificado" or not cert_lower:
        return resultado
        
    # 1. Alerta Crítica FM
    if "fm" in cert_lower:
        resultado["alertas_criticas"].append("ALERTA CRÍTICA: Este pedido exige certificación FM y NO ESTÁ APROBADA para compra.")
        
    # 2. NTC, ENEL
    if "ntc" in cert_lower or "enel" in cert_lower:
        resultado["notas_informativas"].append("Certificaciones NTC/ENEL: Ver certificados en intranet (\\\\intranet.pdc.magnetron.com\\certificacion de producto\\CERTIFICADOS DE PRODUCTO VIGENTES)")
        
    # 3. DOE 2016 y Corrugados
    if "doe" in cert_lower and "amorf" in cert_lower:
        resultado["notas_informativas"].append("DOE 2016 AMORFOS: En desarrollo/proceso.")
    if "corrugad" in cert_lower:
        resultado["notas_informativas"].append("Paneladora 'Paneles Corrugados': En desarrollo/proceso.")
        
    # 4. Lógica UL
    pide_ul = "ul" in cert_lower
    
    if "convencional" in tipo_lower:
        if fases_num == 1 or "1f" in tipo_lower or "mono" in tipo_lower:
            resultado["ul_aplica"] = False
            resultado["ul_detalle"] = "No aplica para Convencional 1F"
        else:
            resultado["ul_aplica"] = True
            resultado["ul_detalle"] = "Sí aplica para Convencional 3F"
    elif "potencia" in tipo_lower or "solar" in tipo_lower:
        if "cobre" in material_lower or "cu" in material_lower:
            resultado["ul_aplica"] = True
            resultado["ul_detalle"] = "Sí, material devanados CU-CU @ 12 MVA"
        else:
            resultado["ul_aplica"] = True
            resultado["ul_detalle"] = "Sí, material devanados AL-AL @ 5,5 MVA"
    elif "sumergible" in tipo_lower:
        resultado["ul_aplica"] = True
        resultado["ul_detalle"] = "Sí, con restricción uso de pintura"
    elif "desfasador" in tipo_lower:
        resultado["ul_aplica"] = True
        resultado["ul_detalle"] = "Sí aplica para Desfasador"
    elif "frecuencia variable" in tipo_lower or "elevador" in tipo_lower:
        resultado["ul_aplica"] = True
        resultado["ul_detalle"] = "Sí aplica para Elevador Frecuencia Variable"
    elif "pedestal" in tipo_lower or "padmount" in tipo_lower:
        resultado["ul_aplica"] = True
        resultado["ul_detalle"] = "Sí aplica para Pedestal"
    elif "seco" in tipo_lower:
        resultado["ul_aplica"] = False
        resultado["ul_detalle"] = "No aplica para transformadores Secos"
    else:
        if pide_ul:
            resultado["ul_aplica"] = True
            resultado["ul_detalle"] = "Sí, requerido por pliego (Tipo constructivo no mapeado específicamente en reglas)"

    return resultado

def nodo_generar_json_sdm(state: BotState):
    
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

    # 4. BUCLE MÁGICO: Crear un JSON por CADA transformador
    datos_norm = state.get("datos_normalizados_sdm", {})
    textos = datos_norm.get("textos_limpios", {})

    for idx, equipo in enumerate(equipos_familia):
        
        # OBTENEMOS DATOS MICRO DIRECTOS DEL INVENTARIO (Excel)
        potencia_real = equipo.get("potencia", "No estandarizado")
        vp_real = equipo.get("voltaje_primario", "No estandarizado")
        vs_real = equipo.get("voltaje_secundario", "No estandarizado")

        clasificacion = datos_norm.get("clasificacion_ia", {})
        ids_orcl = datos_norm.get("ids_internos", {})
        duales = datos_norm.get("voltajes_duales", {})
        
        # Buscar variante específica para este KVA
        variante = buscar_variante(elec.get("variantes_por_potencia", []), potencia_real)

        # Lógica para Fases (Viene del inventario, con soporte extendido y fallback al tipo de trafo)
        fases_str = str(equipo.get("fases", "")).lower()
        if any(palabra in fases_str for palabra in ["mono", "1", "one", "single", "una"]):
            fases_num = 1
        elif any(palabra in fases_str for palabra in ["tri", "3", "three", "tres"]):
            fases_num = 3
        else:
            # Fallback: Revisar si la frase de tipo de transformador tiene la pista de la fase
            tipo_transformador = str(elec.get("tipo_transformador", {})).lower()
            if any(palabra in tipo_transformador for palabra in ["mono", "1", "one", "single", "una"]):
                fases_num = 1
            else:
                fases_num = 3

        # Lógica para Taps
        taps_str = extraer_valor_limpio(elec.get("regulacion_taps", {})).lower()
        tiene_taps = False if taps_str in ["no especificado", "sin taps", "no aplica", "no tiene"] or "sin" in taps_str else True
        if elec.get("cantidad_taps") == 0:
            tiene_taps = False

        datos = {
            "software": "SDM - Magnetron",
            "identificador_pliego": str(equipo.get("item_id", f"Item_{idx+1}")),
            "cantidad_solicitada": equipo.get("cantidad", 1),
            "ids_mapeo_oracle": {
                "id_pais": ids_orcl.get("id_pais"),
                "id_norma": ids_orcl.get("id_norma"),
                "id_kva": ids_orcl.get("id_kva"),
                "id_vp": ids_orcl.get("id_vp"),
                "id_vs": ids_orcl.get("id_vs")
            },
            "parametros_diseno": {
                "potencia_kva": extraer_numero_limpio(potencia_real),
                
                "voltaje_primario_texto": extraer_valor_limpio(textos.get("voltaje_primario") or vp_real),
                "voltaje_secundario_texto": extraer_valor_limpio(textos.get("voltaje_secundario") or vs_real),
                
                "pais_instalacion": textos.get("pais") or extraer_valor_limpio(logi.get("pais_entrega", {})),
                "norma_diseno": textos.get("norma", "No estandarizado"),
                "tipo_transformador": str(equipo.get("tipo_transformador", "")),
                
                "fases": fases_num,
                
                "bil_primario_kv": extraer_numero_limpio(variante.get("bil_primario") or elec.get("bil_primario", {})),
                "bil_secundario_kv": extraer_numero_limpio(elec.get("bil_secundario", {})),
                
                "conmutacion": {
                    "es_conmutable": tiene_taps,
                    "taps_rango_porcentaje": extraer_valor_limpio(elec.get("regulacion_taps", {})),
                    "cantidad_taps": elec.get("cantidad_taps"),
                    "paso_porcentaje": elec.get("paso_porcentaje_taps")
                },
                
                "impedancia_porcentaje": extraer_numero_limpio(variante.get("impedancia_cortocircuito") or elec.get("impedancia_cortocircuito", {})),
                "impedancia_estandar_tccf": None,
                
                "tipo_aceite": extraer_valor_limpio(mec.get("fluido_dielectrico", {})),
                
                "perdidas_no_carga_w": extraer_numero_limpio(variante.get("perdidas_no_carga") or elec.get("perdidas_no_carga", {})),
                "perdidas_no_carga_estandar_w": None,
                
                "perdidas_carga_w": extraer_numero_limpio(variante.get("perdidas_carga") or elec.get("perdidas_carga", {})),
                "perdidas_carga_estandar_w": None,

                "eficiencia_pliego_texto": extraer_valor_limpio(elec.get("eficiencia", {})),
                "eficiencia_porcentaje": extraer_numero_limpio(elec.get("eficiencia", {})),
                "eficiencia_estandar_clasificada": clasificacion.get("norma_eficiencia_clasificada"),
                "eficiencia_estandar_porcentaje": None,
                "eficiencia_estandar_carga_porcentaje": None,
                "eficiencia_estandar_temperatura_c": None,

                "evaluacion_perdidas_economicas": {
                    "aplica_capitalizacion": clasificacion.get("aplica_capitalizacion"),
                    "formula_capitalizacion_texto_crudo": extraer_valor_limpio(elec.get("evaluacion_perdidas", {})),
                    "k1_normalizado_usd_w": elec.get("k1_usd_w"),
                    "k2_normalizado_usd_w": elec.get("k2_usd_w"),
                    "k3_normalizado_usd_w": None,
                    "k4_normalizado_usd_w": None
                },
                
                "dimensiones_limites": {
                    "alto_mm": extraer_numero_limpio(mec.get("alto_especifico", {})),
                    "ancho_mm": extraer_numero_limpio(mec.get("ancho_especifico", {})),
                    "largo_mm": extraer_numero_limpio(mec.get("largo_especifico", {})),
                    "peso_total_kg": extraer_numero_limpio(mec.get("dimensiones_peso_limites", {}))
                },
                "certificaciones_auditoria": auditar_certificaciones(
                    extraer_valor_limpio(logi.get("certificaciones_solicitadas", logi.get("certificacion_ul", {}))),
                    equipo.get("tipo_transformador", ""),
                    fases_num,
                    extraer_numero_limpio(potencia_real),
                    extraer_valor_limpio(mec.get("material_bobinados", ""))
                )
            }
        }
        
        # 5. Creamos un nombre de archivo único
        potencia_limpia = str(potencia_real).replace(" ", "").replace("/", "-")
        nombre_archivo = f"SDM_ENTRY_{potencia_limpia}_{equipo.get('item_id', f'Item{idx+1}')}.json"
        
        # Quitamos caracteres especiales que Windows/Mac no permiten en archivos
        nombre_archivo = "".join([c for c in nombre_archivo if c.isalnum() or c in ['_', '.', '-']])
        
        ruta = os.path.join(carpeta_sdm, nombre_archivo)
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            
        rutas_generadas.append(ruta)
        logger.info(f" [SDM] Archivo generado para trafo de {potencia_real}: {ruta}")
        
    return {"rutas_sdm_json": rutas_generadas}