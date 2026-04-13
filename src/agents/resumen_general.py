import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from src.schemas.state import BotState

def limpiar_texto_xml(texto):
    """Elimina caracteres de control invisibles que rompen la librería de Word."""
    if not isinstance(texto, str):
        return str(texto)
    # Solo permite tabulaciones, saltos de línea y caracteres de texto normales (ASCII/Unicode >= 32)
    return "".join(c for c in texto if ord(c) in (9, 10, 13) or ord(c) >= 32)

def formatear_diccionario(doc: Document, titulo: str, datos: dict):
    """Escribe una sección en el Word extrayendo el valor y el origen."""
    if not datos: return
    
    doc.add_heading(titulo, level=2)
    for clave, info in datos.items():
        if not isinstance(info, dict) or "valor" not in info: continue
        
        nombre_campo = clave.replace("_", " ").title()
        
        # 🛡️ FILTRAMOS EL TEXTO ANTES DE INYECTARLO AL WORD
        valor = limpiar_texto_xml(info.get("valor", "No especificado"))
        origen = limpiar_texto_xml(info.get("origen", "No especificado"))
        
        p = doc.add_paragraph()
        p.add_run(f"• {nombre_campo}: ").bold = True
        p.add_run(f"{valor}")
        
        # Si el dato fue inyectado por una norma, lo marcamos en gris y cursiva
        if origen not in ["Pliego", "No especificado"]:
            run_origen = p.add_run(f" (Dato asumido por: {origen})")
            run_origen.italic = True
            run_origen.font.color.rgb = RGBColor(128, 128, 128)

def nodo_generar_resumen_tipo(state: BotState):
    """Toma los JSON de los 4 escuadrones y ensambla el Word final para la familia."""
    
    # 1. Identificar la Familia actual
    inventario = state.get("inventario_global", [])
    item_id = state.get("item_actual_id", "")
    trafo_actual = next((t for t in inventario if t["item_id"] == item_id), None)
    
    if not trafo_actual: return {}
    familia = trafo_actual.get("tipo_transformador", "General")
    
    print(f"📝 [Ensamblador Word] Redactando Documento Técnico para la familia: {familia}...")
    
    # 2. Crear el Documento Word
    doc = Document()
    doc.add_heading(f"RESUMEN TÉCNICO Y COMERCIAL - {familia.upper()}", 0)
    
    p_intro = doc.add_paragraph("Documento generado automáticamente a partir de los pliegos del cliente. ")
    p_intro.add_run("Uso exclusivo para Ingeniería de Detalle y Cotización - Magnetron S.A.S.").bold = True
    
    # 3. Inyectar las 4 secciones
    formatear_diccionario(doc, "1. Parámetros Eléctricos", state.get("datos_electricos", {}))
    formatear_diccionario(doc, "2. Datos Mecánicos y Fluidos", state.get("datos_mecanicos", {}))
    formatear_diccionario(doc, "3. Accesorios y Protecciones", state.get("datos_accesorios", {}))
    formatear_diccionario(doc, "4. Logística y Condiciones Comerciales", state.get("datos_logisticos", {}))
    
    # 4. Inyectar las Alertas de Diseño (Banderas Rojas)
    alertas = state.get("alertas_diseno", [])
    if alertas:
        doc.add_heading("🚨 ALERTAS Y RECOMENDACIONES NORMATIVAS", level=2)
        for alerta in alertas:
            p = doc.add_paragraph()
            run = p.add_run(f"⚠️ {alerta}")
            run.font.color.rgb = RGBColor(255, 0, 0) # Rojo para alertas
    
    # 5. Guardar Archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    nombre_limpio = "".join([c for c in familia if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    ruta_docx = f"data/outputs/Resumen_{nombre_limpio.replace(' ', '_')}_{timestamp}.docx"
    
    os.makedirs("data/outputs", exist_ok=True)
    doc.save(ruta_docx)
    print(f"✅ [Ensamblador Word] Documento guardado en: {ruta_docx}")
    
    completados_actuales = state.get("resumenes_completados", [])
    rutas_actuales = state.get("rutas_fichas_word", [])
    
    return {
        "resumenes_completados": completados_actuales + [familia],
        "rutas_fichas_word": rutas_actuales + [ruta_docx]
    }