"""
extractor.py - Herramienta para lectura universal de documentos y correos.

Propósito general:
Sirve como el procesador central de entrada para el bot. Es capaz de leer archivos 
PDF, Word, Excel, texto plano y archivos de correo .eml, convirtiéndolos en una cadena de 
texto plano limpio que los agentes (LLMs) pueden consumir fácilmente.

Cuándo usarlo:
Esta herramienta debe invocarse antes de que inicie el grafo (`grafo.py`), o en la etapa de 
formateo de la entrada del usuario, para transformar el archivo cargado en `texto_extraido`.

Requisitos:
- Librerías: `fitz` (PyMuPDF), `docx`, `pandas`, `bs4`.
- Un LLM multimodal para la visión de imágenes incrustadas (e.g. `gpt-4o` o `gemini-1.5-pro`).
"""

import os
import fitz  # PyMuPDF para PDFs
import docx  # Para archivos Word
import pandas as pd # Para Excels
import email
from email import policy
from bs4 import BeautifulSoup
import base64
import re
from langchain_core.messages import HumanMessage
from src.corelogic import get_llm
from src.utils.logger import get_logger
logger = get_logger("Extractor")


def limpiar_basura_digital(texto: str) -> str:
    """
    Filtro de seguridad para destruir bloques Base64, Hexadecimales o texto CMAP corrupto.
    Esto previene que el LLM sufra sobrecarga de tokens y alucinaciones por inyecciones binarias.
    
    Parámetros:
    - texto (str): Texto crudo.
    
    Retorna:
    - str: Texto saneado.
    """
    if not texto:
        return ""
    # Elimina cualquier 'palabra' de más de 80 caracteres seguidos sin espacios (típico de Base64 oculto)
    texto_filtrado = re.sub(r'\S{80,}', '[BLOQUE BINARIO ELIMINADO]', texto)
    # Limpia saltos de línea masivos para ahorrar tokens
    texto_filtrado = re.sub(r'\n{4,}', '\n\n', texto_filtrado)
    return texto_filtrado

def procesar_imagen_vision(bytes_imagen: bytes, extension: str, llm_vision) -> str:
    """Procesa una imagen con el LLM de visión y devuelve el texto estructurado."""
    if not bytes_imagen or len(bytes_imagen) < 3000: # Ignorar iconos pequeños
        return ""
        
    img_b64 = base64.b64encode(bytes_imagen).decode("utf-8")
    content_type = f"image/{extension}" if extension else "image/png"
    
    mensaje = HumanMessage(
        content=[
            {
                "type": "text", 
                "text": "Extrae todo el texto, tablas y cantidades de esta imagen. Si es una tabla, usa formato Markdown. Si la imagen es un logo comercial, firma, o no tiene información técnica, responde exactamente: 'sin informacion'."
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:{content_type};base64,{img_b64}"},
            },
        ]
    )
    
    try:
        respuesta = llm_vision.invoke([mensaje])
        texto_vision = respuesta.content.strip()
        
        # Descartar ruido si el modelo obedeció
        if "sin informacion" not in texto_vision.lower().replace("ó", "o"):
            return f"\n[DATOS EXTRAÍDOS DE IMAGEN INCRUSTADA]\n{texto_vision}\n\n"
    except Exception as e:
        logger.info(f" [Visión] Error al procesar imagen: {e}")
        
    return ""


def procesar_correo_eml(ruta_archivo: str) -> str:
    texto_consolidado = ""
    llm_vision = get_llm("vision")
    
    with open(ruta_archivo, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    asunto = msg.get('Subject', 'Sin Asunto')
    remitente = msg.get('From', 'Desconocido')
    fecha = msg.get('Date', 'Desconocida')
    
    texto_consolidado += f"--- METADATOS DEL CORREO ---\nASUNTO: {asunto}\nDE: {remitente}\nFECHA: {fecha}\n\n"

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = str(part.get("Content-Disposition"))

        if content_type.startswith("multipart/"):
            continue

        # Bloque para texto sin formato
        if content_type == "text/plain" and "attachment" not in disposition:
            payload = part.get_payload(decode=True)
            if payload:
                texto_limpio = payload.decode('utf-8', errors='ignore').strip()
                texto_limpio = limpiar_basura_digital(texto_limpio)
                if texto_limpio:
                    texto_consolidado += f"{texto_limpio}\n\n"
            
        # Bloque para texto HTML (muy común en Outlook corporativo)
        elif content_type == "text/html" and "attachment" not in disposition:
            payload = part.get_payload(decode=True)
            if payload:
                html_content = payload.decode('utf-8', errors='ignore')
                sopa = BeautifulSoup(html_content, "html.parser")
                texto_limpio = sopa.get_text(separator='\n', strip=True)
                texto_limpio = limpiar_basura_digital(texto_limpio)
                if texto_limpio:
                    texto_consolidado += f"{texto_limpio}\n\n"
            
        # Motor de Visión para imágenes incrustadas (firmas, fotos de placas, tablas pegadas)
        elif content_type.startswith("image/"):
            bytes_imagen = part.get_payload(decode=True)
            extension = content_type.split("/")[-1] if "/" in content_type else "png"
            texto_vision = procesar_imagen_vision(bytes_imagen, extension, llm_vision)
            if texto_vision:
                texto_consolidado += texto_vision

    return texto_consolidado

def extraer_tablas_hibrido(pdf_path: str) -> str:
    """
    Extractor de tablas inteligente para PDF usando pdfplumber.
    (Camelot se ha removido debido a problemas severos de rendimiento y dependencias)
    """
    tablas_unicas = []
    contenidos_vistos = set()
    tablas_str = ""
    
    def normalizar_tabla(t_str):
        return ' '.join(t_str.split()).lower()

    try:
        import pdfplumber
        logger.info(" [Lector] Intentando extraer tablas con pdfplumber...")
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        t_str = "\n".join(["\t".join([str(cell or "").replace("\n", " ") for cell in row]) for row in table])
                        norm = normalizar_tabla(t_str)
                        if norm not in contenidos_vistos:
                            contenidos_vistos.add(norm)
                            tablas_unicas.append(t_str)
                            tablas_str += t_str + "\n\n"
    except Exception as e:
        logger.info(f" [Lector] pdfplumber falló o no está instalado: {e}")

    return tablas_str

def extraer_texto_universal(ruta_archivo: str) -> str:
    """
    Lee un archivo en múltiples formatos soportados (PDF, DOCX, XLSX, TXT, EML) 
    y devuelve todo su contenido como texto crudo, aplicando limpieza de basura.
    
    Parámetros:
    - ruta_archivo (str): Ruta completa o relativa al documento a leer.
    
    Retorna:
    - str: El texto consolidado listo para inyectar en el `BotState`.
    """
    _, extension = os.path.splitext(ruta_archivo)
    extension = extension.lower()
    texto_completo = ""

    logger.info(f" [Lector] Procesando archivo: {os.path.basename(ruta_archivo)}")

    try:
        if extension == '.pdf':
            logger.info(" [Lector] Extrayendo PDF con método híbrido (fitz + tablas + visión)...")
            llm_vision = get_llm("vision")
            
            doc = fitz.open(ruta_archivo)
            for page_num in range(len(doc)):
                pagina = doc[page_num]
                # 1. Extraer Texto
                texto_completo += limpiar_basura_digital(pagina.get_text()) + "\n"
                
                # 2. Extraer Imágenes de la página
                image_list = pagina.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)
                        
                        # Filtrar imágenes miniatura
                        if len(image_bytes) >= 1000 and width >= 50 and height >= 50:
                            texto_vision = procesar_imagen_vision(image_bytes, image_ext, llm_vision)
                            if texto_vision:
                                texto_completo += f"\n[IMAGEN PÁGINA {page_num + 1}]\n" + texto_vision
                    except Exception as img_e:
                        logger.info(f" [Lector] Error procesando imagen en pag {page_num + 1}: {img_e}")
                        
            doc.close()
            
            # 3. Extraer Tablas
            tablas_extraidas = extraer_tablas_hibrido(ruta_archivo)
            if tablas_extraidas:
                texto_completo += "\n--- TABLAS EXTRAÍDAS DEL PDF ---\n" + limpiar_basura_digital(tablas_extraidas)
            
        elif extension in ['.docx', '.doc']:
            doc = docx.Document(ruta_archivo)
            for parrafo in doc.paragraphs:
                texto_completo += limpiar_basura_digital(parrafo.text) + "\n"
                
        elif extension in ['.xlsx', '.xls']:
            excel = pd.read_excel(ruta_archivo, sheet_name=None)
            for nombre_hoja, df in excel.items():
                texto_completo += f"--- HOJA: {nombre_hoja} ---\n"
                texto_completo += limpiar_basura_digital(df.to_string()) + "\n"
                
        elif extension == '.txt':
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                texto_completo = limpiar_basura_digital(f.read())
                
        elif extension == '.eml':
            texto_completo = procesar_correo_eml(ruta_archivo)
                
        else:
            logger.info(f" [Advertencia] Extensión no soportada: {extension}")

    except Exception as e:
        logger.info(f" [Error] Fallo al leer {ruta_archivo}: {str(e)}")

    # ESTE ES NUESTRO MONITOR DE SALUD:
    logger.info(f" [Debug] Caracteres extraídos de {os.path.basename(ruta_archivo)}: {len(texto_completo)}")
    
    # Limitar el tamaño para no sobrepasar los tokens del LLM (max ~300k caracteres por archivo)
    if len(texto_completo) > 300000:
        logger.info(f" [Advertencia] El documento excede el límite de tokens. Truncando de {len(texto_completo)} a 300000 caracteres.")
        mitad = 150000
        texto_completo = texto_completo[:mitad] + "\n\n...[TEXTO OMITIDO POR EXCEDER LÍMITE DE TOKENS]...\n\n" + texto_completo[-mitad:]
        
    return texto_completo

# ==========================================
# METADATA
# tools_used: [fitz, docx, pandas, email, bs4, base64, re, langchain_core]
# use_cases: [Parseo OCR y de texto de archivos del cliente, Extirpación de basura binaria, Visión en correos]
# reusable_components: [limpiar_basura_digital, extraer_texto_universal]
# dependencies: [pip install PyMuPDF python-docx pandas beautifulsoup4 langchain-core]
# ==========================================