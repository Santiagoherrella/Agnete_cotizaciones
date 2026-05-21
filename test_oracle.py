import oracledb
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def probar_conexion_magnetron():
    print("="*50)
    print("🔌 INICIANDO PRUEBA DE CONEXIÓN A ORACLE DB")
    print("="*50)
    
    # --- NUEVA LÍNEA: ACTIVAR EL THICK MODE ---
    # Reemplaza la ruta por la carpeta exacta donde descomprimiste el archivo ZIP
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracleinstantclient.23.26.1.0.0")
        print("⚙️ Modo 'Thick' activado correctamente.")
    except Exception as e:
        print(f"⚠️ Nota sobre el cliente Oracle: {e}")

    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    dsn = os.environ.get("DB_DSN")

    if not all([user, password, dsn]):
        print("❌ ERROR: Faltan credenciales. Verifica tu archivo .env")
        return

    try:
        print(f"Intentando conectar a DSN: {dsn}...")
        # Al conectarnos ahora, usará automáticamente el Instant Client
        conexion = oracledb.connect(user=user, password=password, dsn=dsn)
        print("✅ ¡CONEXIÓN EXITOSA AL SERVIDOR!")
        print(f"🏛️ Versión del motor Oracle: {conexion.version}")

        # Aquí irá tu consulta después...
        
        conexion.close()
        print("\n🔌 Conexión cerrada de forma segura.")

    except oracledb.DatabaseError as e:
        error, = e.args
        print(f"\n❌ ERROR DE BASE DE DATOS:")
        print(f"Código: {error.code}")
        print(f"Mensaje: {error.message}")
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")

if __name__ == "__main__":
    probar_conexion_magnetron()