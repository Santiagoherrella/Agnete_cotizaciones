"""
corelogic.py - Gestión de selección e inicialización de modelos de lenguaje.

Propósito general:
Este módulo centraliza la instanciación de los Modelos de Lenguaje Grande (LLMs)
utilizados en los diferentes agentes del bot de resúmenes. Evita la duplicación 
de código y permite cambiar o configurar fácilmente el proveedor (Gemini, OpenAI, etc.) 
para cada nodo del grafo a través del archivo `config.json`.

Cuándo usarlo:
Debe importarse y usarse en cualquier nodo o agente que requiera hacer una llamada 
a un LLM (ej. nodo extractor, ensamblador o chat general).

Requisitos:
- Archivo `.env` con las claves de API configuradas (`OPENAI_API_KEY`, `GOOGLE_API_KEY`).
- Archivo `config.json` en la raíz del proyecto para leer la configuración por agente.
"""

import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Cargar variables de entorno estáticas desde el .env al inicio del proceso
load_dotenv()

# Intentar ubicar config.json (se prefiere la raíz del proyecto)
ruta_config = os.path.join(os.path.dirname(__file__), "..", "config.json") 
if not os.path.exists(ruta_config):
    ruta_config = "config.json" # Asume que la raíz activa es donde se corre

# Lectura global de la configuración para no hacerlo en cada llamada a la función
with open(ruta_config, "r", encoding="utf-8") as f:
    config = json.load(f)

def get_llm(id_agente: str):
    """
    Instancia y devuelve el modelo de lenguaje configurado para un agente específico.

    Parámetros:
    - id_agente (str): La clave identificadora del agente en `config.json`
                       (e.g., 'agente_inventario', 'agente_electrico').

    Retorna:
    - Objeto de Langchain del tipo `BaseChatModel` configurado con los 
      parámetros solicitados (ej. `ChatOpenAI` o `ChatGoogleGenerativeAI`).

    Levanta:
    - ValueError: Si el ID no existe en config.json, si el proveedor no está 
      soportado, o si faltan las variables de entorno para las APIs.

    Ejemplo de uso:
        llm = get_llm("agente_electrico")
        resultado = llm.invoke("Hola")
    """
    # Verificar si el agente está registrado
    if id_agente not in config:
        raise ValueError(f"❌ [CoreLogic] El agente '{id_agente}' no está definido en config.json")

    parametros = config[id_agente]
    provider = parametros.get("llm_provider", "").lower()
    model_name = parametros.get("llm_model")
    temperature = parametros.get("temperature", 0.0)

    # Lógica de instanciación según proveedor
    if provider == "openai":
        if 'OPENAI_API_KEY' not in os.environ:
            raise ValueError("La variable OPENAI_API_KEY no está configurada en el .env")
        
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    elif provider == "gemini":
        if 'GOOGLE_API_KEY' not in os.environ:
            raise ValueError("La variable GOOGLE_API_KEY no está configurada en el .env")
        
        return ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
    else:
        raise ValueError(f"Proveedor LLM no soportado: {provider}")

# ==========================================
# METADATA
# tools_used: [os, json, dotenv, langchain_google_genai, langchain_openai]
# use_cases: [Instanciación de agentes LLM, Gestión de config por ID de agente]
# reusable_components: [get_llm]
# dependencies: [pip install python-dotenv langchain-google-genai langchain-openai]
# ==========================================