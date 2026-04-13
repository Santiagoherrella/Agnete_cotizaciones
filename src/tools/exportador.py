import pandas as pd
import os
import re
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.state import BotState
from src.schemas.modelos import TablaCTGFamilia

def nodo_crear_excel_inventario(state: BotState):
    """Fase 2: Empaca el Excel global"""
    print("📊 [Herramienta Excel] Empacando el inventario global en formato .xlsx...")
    inventario = state.get("inventario_global", [])
    if not inventario:
        return {"ruta_excel_inventario": ""}

    df = pd.DataFrame(inventario)
    df.columns = [col.replace("_", " ").title() for col in df.columns]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    ruta_salida = f"data/outputs/Inventario_RFQ_{timestamp}.xlsx"
    
    os.makedirs("data/outputs", exist_ok=True)
    df.to_excel(ruta_salida, index=False)
    print(f"✅ Archivo Excel de Inventario generado: {ruta_salida}")
    return {"ruta_excel_inventario": ruta_salida}

# ==========================================
# CEREBRO INDEPENDIENTE PARA EL CTG (Micro-Extracción)
# ==========================================
PROMPT_CTG_INDEPENDIENTE = """
Eres un Ingeniero Eléctrico Senior en Magnetron S.A.S.
Tu misión es construir la matriz de Características Técnicas Garantizadas (CTG) para esta familia de transformadores: {familia}.

El cliente solicitó EXACTAMENTE los siguientes equipos en el inventario:
{lista_inventario}

INSTRUCCIONES CRÍTICAS:
1. Tu respuesta debe contener EXACTAMENTE {num_equipos} variantes (una por cada equipo de la lista, en el mismo orden).
2. Para cada equipo, busca en el pliego sus datos técnicos específicos (Phase, BIL, Efficiency, No-load losses, Load losses) según su Potencia (kVA) y Voltaje.
3. Si la tabla de pérdidas o algún dato no está en el pliego, pon "No especificado".
4. El fabricante siempre es "MAGNETRON S.A.S.".

TEXTO DEL PLIEGO:
{texto_pliego}
"""

def nodo_crear_excel_ctg(state: BotState):
    inventario = state.get("inventario_global", [])
    item_id = state.get("item_actual_id", "")
    
    trafo_actual = next((t for t in inventario if t["item_id"] == item_id), None)
    if not trafo_actual: return {}
        
    familia = trafo_actual.get("tipo_transformador", "General")
    trafos_familia = [t for t in inventario if t.get("tipo_transformador") == familia]
    
    print(f"📊 [Generador CTG] Extrayendo matriz técnica (1 a 1) para {len(trafos_familia)} equipos de la familia: {familia}...")
    
    # 1. Preparar la lista exacta para el LLM
    lista_str = ""
    for i, t in enumerate(trafos_familia):
        lista_str += f"{i+1}. {t.get('cantidad', 1)} unds | {t.get('potencia', '')} | Pri: {t.get('voltaje_primario', '')} | Sec: {t.get('voltaje_secundario', '')}\n"

    # 2. Llamar al modelo pesado para la extracción
    prompt = ChatPromptTemplate.from_template(PROMPT_CTG_INDEPENDIENTE)
    llm = get_llm("agente_electrico") # Asegúrate de que en config.json este sea gpt-4o
    cadena = prompt | llm.with_structured_output(TablaCTGFamilia)
    
    try:
        resultado_llm = cadena.invoke({
            "familia": familia,
            "lista_inventario": lista_str,
            "num_equipos": len(trafos_familia),
            "texto_pliego": state.get("texto_extraido", "")
        })
    except Exception as e:
        print(f"❌ [Error CTG] Falló la extracción para {familia}: {e}")
        return {}

    # 3. Cruzar Inventario con LLM para asegurar 100% de precisión 1 a 1
    estructura_filas = [
        ("Manufacturer", ""), ("Type", ""), ("Manufacturing standards", ""), 
        ("kVA Rating", ""), ("Phase", ""), ("Primary Voltage", "V"), ("Primary BIL", "kV"), 
        ("Taps", ""), ("Secondary Voltage", "V"), ("Secondary BIL", "kV"), 
        ("Connection group", ""), ("Frequency", "Hz"), ("DOE 2016 Efficiency", "%"), 
        ("No-load losses @20°C", "W"), ("Load losses @ 85°C - 100% loaded", "W")
    ]
    
    datos_excel = {"DESCRIPTION": [i[0] for i in estructura_filas], "UNIT": [i[1] for i in estructura_filas]}
    
    variantes_llm = resultado_llm.variantes if hasattr(resultado_llm, 'variantes') else []

    for i, trafo_inv in enumerate(trafos_familia):
        # Si el LLM se saltó alguno, usamos un dict vacío para no romper el Excel
        var_llm = variantes_llm[i].model_dump() if i < len(variantes_llm) and hasattr(variantes_llm[i], 'model_dump') else (variantes_llm[i].dict() if i < len(variantes_llm) else {})
        
        # Mezclamos la verdad absoluta del inventario con la investigación del LLM
        col_data = [
            "MAGNETRON S.A.S.",
            trafo_inv.get("tipo_transformador", "No especificado"),
            var_llm.get("normas", "No especificado"),
            trafo_inv.get("potencia", "No especificado"), # Del Inventario
            var_llm.get("fases", "No especificado"),      # Del LLM
            trafo_inv.get("voltaje_primario", "No especificado"), # Del Inventario
            var_llm.get("bil_primario", "No especificado"),       # Del LLM
            var_llm.get("taps", "No especificado"),
            trafo_inv.get("voltaje_secundario", "No especificado"), # Del Inventario
            var_llm.get("bil_secundario", "No especificado"),
            var_llm.get("grupo_conexion", "No especificado"),
            var_llm.get("frecuencia", "No especificado"),
            var_llm.get("eficiencia", "No especificado"),
            var_llm.get("perdidas_vacio", "No especificado"),     # Del LLM
            var_llm.get("perdidas_carga", "No especificado")      # Del LLM
        ]
        datos_excel[f"GUARANTEED_{i}"] = col_data

    # 4. Generar el Excel
    df = pd.DataFrame(datos_excel)
    df.columns = ["DESCRIPTION", ""] + ["GUARANTEED"] * len(trafos_familia)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    tipo_limpio = "".join([c for c in familia if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    ruta_salida = f"data/outputs/CTG_{tipo_limpio.replace(' ', '_')}_{timestamp}.xlsx"
    
    os.makedirs("data/outputs", exist_ok=True)
    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Technical Characteristics")
        worksheet = writer.sheets["Technical Characteristics"]
        worksheet.column_dimensions['A'].width = 40
        worksheet.column_dimensions['B'].width = 8
        for col_i in range(3, 3 + len(trafos_familia)):
            worksheet.column_dimensions[chr(64 + col_i)].width = 20

    print(f"✅ [Ensamblador CTG] Archivo guardado (1 a 1 con inventario): {ruta_salida}")
    return {"rutas_tablas_ctg": [ruta_salida]}