import os
from dotenv import load_dotenv

# 1. Cargar configuración
load_dotenv()

from src.schemas.state import BotState
from src.tools.extractor import extraer_texto_universal
from src.grafo import maquina_magnetron

def ejecutar_prueba_maestra():
    carpeta_inputs = "data/inputs"
    
    # Validar archivos
    archivos = [f for f in os.listdir(carpeta_inputs) if os.path.isfile(os.path.join(carpeta_inputs, f))]
    if not archivos:
        print(" No hay archivos en data/inputs/")
        return

    print("\n" + "="*60)
    print(" INICIANDO PRUEBA 1: SISTEMA MULTI-AGENTE MAGNETRÓN")
    print(f"Archivos a procesar: {len(archivos)}")
    print("="*60)

    # 2. Consolidar todo el contexto (Engrapadora de documentos)
    texto_total = ""
    for arc in archivos:
        print(f"Leyendo: {arc}...")
        texto_total += f"\n\n--- DOCUMENTO: {arc} ---\n"
        texto_total += extraer_texto_universal(os.path.join(carpeta_inputs, arc))
    
    # 3. Preparar la Tarjeta Viajera
    estado_inicial: BotState = {
        "configuracion": { # Datos que vamos a extraer
            "ejecutar_ingenieria": True,
            "ejecutar_comercial": False,
            "ejecutar_sdm": True
        },
        "ruta_documento": "PROYECTO_PEA_RIVER_BATCH",
        "texto_extraido": texto_total,
        "inventario_global": [],
        "resumenes_completados": [],
        "item_actual_id": "", # Usaremos esto para controlar el flujo de tipos
        "datos_electricos": {},
        "datos_mecanicos": {},
        "errores_extraccion": [],
        "rutas_fichas_word": [],
        "rutas_tablas_ctg": []  # <--- AGREGAR ESTO
    }

# 4. Ejecutar la planta
    print("\n" + "="*60)
    resultado = maquina_magnetron.invoke(estado_inicial)

# --- NUEVO BLOQUE DE IMPRESIÓN ---
    import json
    print("\n" + "="*60)
    print("RESULTADO FINAL DE LOS 4 ESCUADRONES")
    print("="*60)
    
    print("\n DATOS ELÉCTRICOS:")
    print(json.dumps(resultado.get("datos_electricos", {}), indent=2, ensure_ascii=False))
    
    print("\n DATOS MECÁNICOS:")
    print(json.dumps(resultado.get("datos_mecanicos", {}), indent=2, ensure_ascii=False))
    
    print("\n DATOS ACCESORIOS:")
    print(json.dumps(resultado.get("datos_accesorios", {}), indent=2, ensure_ascii=False))
    
    print("\n DATOS LOGÍSTICOS:")
    print(json.dumps(resultado.get("datos_logisticos", {}), indent=2, ensure_ascii=False))
    
    print("\n ALERTAS DE DISEÑO (FALLBACKS):")
    for alerta in resultado.get("alertas_diseno", []):
        print(f"  - {alerta}")

if __name__ == "__main__":
    ejecutar_prueba_maestra()


