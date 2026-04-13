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

def limpiar_basura_digital(texto: str) -> str:
    """Filtro de seguridad para destruir bloques Base64, Hexadecimales o texto CMAP corrupto."""
    if not texto:
        return ""
    # Elimina cualquier 'palabra' de más de 80 caracteres seguidos sin espacios (típico de Base64 oculto)
    texto_filtrado = re.sub(r'\S{80,}', '[BLOQUE BINARIO ELIMINADO]', texto)
    # Limpia saltos de línea masivos para ahorrar tokens
    texto_filtrado = re.sub(r'\n{4,}', '\n\n', texto_filtrado)
    return texto_filtrado

def procesar_correo_eml(ruta_archivo: str) -> str:
    """Procesa un archivo .eml extrayendo texto nativo y aplicando visión a imágenes incrustadas."""
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

        if content_type == "text/plain" and "attachment" not in disposition:
            payload = part.get_payload(decode=True)
            if payload:
                texto_limpio = payload.decode('utf-8', errors='ignore').strip()
                texto_limpio = limpiar_basura_digital(texto_limpio)
                if texto_limpio:
                    texto_consolidado += f"{texto_limpio}\n\n"
            
        elif content_type == "text/html" and "attachment" not in disposition:
            payload = part.get_payload(decode=True)
            if payload:
                html_content = payload.decode('utf-8', errors='ignore')
                sopa = BeautifulSoup(html_content, "html.parser")
                texto_limpio = sopa.get_text(separator='\n', strip=True)
                texto_limpio = limpiar_basura_digital(texto_limpio)
                if texto_limpio:
                    texto_consolidado += f"{texto_limpio}\n\n"
            
        elif content_type.startswith("image/"):
            bytes_imagen = part.get_payload(decode=True)
            if not bytes_imagen or len(bytes_imagen) < 3000:
                continue 
                
            img_b64 = base64.b64encode(bytes_imagen).decode("utf-8")
            
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
                
                if "sin informacion" not in texto_vision.lower().replace("ó", "o"):
                    texto_consolidado += f"\n[DATOS EXTRAÍDOS DE IMAGEN INCRUSTADA]\n{texto_vision}\n\n"
            except Exception as e:
                print(f"⚠️ [Visión] Error al procesar imagen: {e}")

    return texto_consolidado

def extraer_texto_universal(ruta_archivo: str) -> str:
    """
    Lee un archivo (PDF, DOCX, XLSX, TXT, EML) y devuelve todo su contenido como texto plano.
    """
    _, extension = os.path.splitext(ruta_archivo)
    extension = extension.lower()
    texto_completo = ""

    print(f"📄 [Lector] Procesando archivo: {os.path.basename(ruta_archivo)}")

    try:
        if extension == '.pdf':
            doc = fitz.open(ruta_archivo)
            for pagina in doc:
                texto_completo += limpiar_basura_digital(pagina.get_text())
            
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
            print(f"⚠️ [Advertencia] Extensión no soportada: {extension}")

    except Exception as e:
        print(f"❌ [Error] Fallo al leer {ruta_archivo}: {str(e)}")

    # ESTE ES NUESTRO MONITOR DE SALUD:
    print(f"📏 [Debug] Caracteres extraídos de {os.path.basename(ruta_archivo)}: {len(texto_completo)}")
    return texto_completo