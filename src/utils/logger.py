import logging
import os
import getpass
import contextvars
from logging.handlers import RotatingFileHandler

# Define el directorio base donde se encuentra este archivo y sube dos niveles (hasta la raíz del proyecto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Asegura que el directorio de logs exista
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "agente_cotizaciones.log")

# Obtener nombre del usuario del sistema operativo
try:
    SYSTEM_USER = getpass.getuser()
except Exception:
    SYSTEM_USER = "UsuarioDesconocido"

# Variable de contexto para soportar múltiples usuarios en la app web concurrentemente
current_user = contextvars.ContextVar('current_user', default=SYSTEM_USER)

class ContextUserFilter(logging.Filter):
    """Inyecta el valor actual de current_user en el registro del log"""
    def filter(self, record):
        record.user_context = current_user.get()
        return True

# Configuración básica
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - Usuario: %(user_context)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_logger(name: str) -> logging.Logger:
    """
    Crea o recupera un logger configurado con el nombre dado.
    
    El logger enviará los mensajes tanto a la consola como a un archivo rotativo.
    """
    logger = logging.getLogger(name)
    
    # Evitar agregar múltiples handlers si el logger ya existe
    if not logger.handlers:
        logger.setLevel(LOG_LEVEL)
        
        # Formateador común para todos los handlers
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        
        # 1. Handler para Archivo (con rotación: max 5MB, mantiene 3 respaldos)
        file_handler = RotatingFileHandler(
            filename=LOG_FILE,
            mode='a',
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.ERROR)  # Guarda únicamente errores en el archivo físico
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ContextUserFilter())
        logger.addHandler(file_handler)
        
        # 2. Handler para Consola (Terminal)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(ContextUserFilter())
        logger.addHandler(console_handler)
        
        # Evitar que los logs se propaguen al logger root (para no duplicarlos)
        logger.propagate = False
        
    return logger
