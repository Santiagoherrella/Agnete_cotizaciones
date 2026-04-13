"""corelogic.py - Gestión de selección e inicialización de modelos de lenguaje."""
import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Cargar variables de entorno (.env)
load_dotenv()

# Leer configuración desde config.json
ruta_config = os.path.join(os.path.dirname(__file__), "..", "config.json") # Ajuste la ruta si su corelogic está en src/
if not os.path.exists("config.json"):
    ruta_config = "config.json" # Asume raíz si se corre desde ahí

with open(ruta_config, "r", encoding="utf-8") as f:
    config = json.load(f)

def get_llm(id_agente: str):
    """
    Lee el config.json y devuelve el modelo instanciado para el agente específico.
    Ejemplo de uso: llm = get_llm("agente_inventario")
    """
    if id_agente not in config:
        raise ValueError(f"❌ [CoreLogic] El agente '{id_agente}' no está definido en config.json")

    parametros = config[id_agente]
    provider = parametros.get("llm_provider", "").lower()
    model_name = parametros.get("llm_model")
    temperature = parametros.get("temperature", 0.0)

    if provider == "openai":
        if 'OPENAI_API_KEY' not in os.environ:
            raise ValueError("La variable OPENAI_API_KEY no está configurada en el .env")
        
        # print(f"🧠 [CoreLogic] Instanciando OpenAI ({model_name}) para: {id_agente}")
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    elif provider == "gemini":
        if 'GOOGLE_API_KEY' not in os.environ:
            raise ValueError("La variable GOOGLE_API_KEY no está configurada en el .env")
        
        # print(f"🧠 [CoreLogic] Instanciando Gemini ({model_name}) para: {id_agente}")
        return ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
    # Aquí en el futuro puede agregar 'elif provider == "grok":'
    
    else:
        raise ValueError(f"Proveedor LLM no soportado: {provider}")