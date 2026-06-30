import oracledb
import pandas as pd
import os
from dotenv import load_dotenv
from src.utils.logger import get_logger
logger = get_logger("TestOracle")


load_dotenv()


def probar_conexion_magnetron():
    logger.info("="*50)
    logger.info("INICIANDO PRUEBA DE EXTRACCIÓN ORACLE DB")
    logger.info("="*50)
    
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracleinstantclient.23.26.1.0.0")
    except Exception as e:
        pass # Si ya está iniciado no pasa nada

    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    dsn = os.environ.get("DB_DSN")

    try:
        conexion = oracledb.connect(user=user, password=password, dsn=dsn)
        cursor = conexion.cursor()
        
        # ==========================================
        # PRUEBA 1: DESCUBRIR LOS NOMBRES REALES
        # ==========================================
        logger.info("\n 1. Buscando el nombre exacto de las tablas en el esquema DISENO...")
        consulta_tablas = """
        SELECT table_name 
        FROM all_tables 
        WHERE owner = 'DISENO' 
        AND (table_name LIKE '%PAIS%' 
             OR table_name LIKE '%NORMA%' 
             OR table_name LIKE '%POTENCIA%' 
             OR table_name LIKE '%VOLTAJE%')
        ORDER BY table_name
        """
        cursor.execute(consulta_tablas)
        tablas = cursor.fetchall()
        
        if tablas:
            logger.info("Tablas encontradas:")
            for t in tablas:
                logger.info(f"   {t[0]}")
        else:
            logger.info("No se encontraron tablas con esos nombres clave.")

        # ==========================================
        # PRUEBA 2: EXTRAER DATOS (Ejemplo con PAISES)
        # ==========================================
        # NOTA: Si en la Prueba 1 viste que la tabla se llama distinto (Ej: PAISES_BK), 
        # cámbialo en la línea de abajo.
        tabla_a_probar = "DISENO.PAISES"  
        
        logger.info(f"\n2. Intentando extraer 5 registros de {tabla_a_probar}...")
        try:
            # Usamos Pandas para que la tabla se vea bonita en la terminal
            df = pd.read_sql(f"SELECT * FROM {tabla_a_probar} WHERE ROWNUM <= 5", con=conexion)
            logger.info("\n¡EXTRACCIÓN EXITOSA! Aquí tienes los datos:")
            logger.info("-" * 50)
            logger.info(df.to_string(index=False))
            logger.info("-" * 50)
        except Exception as e:
            logger.info(f" Falló la extracción de la tabla. Puede que el nombre no sea {tabla_a_probar}.")
            logger.info(f"Error: {e}")

        conexion.close()
        logger.info("\n Conexión cerrada de forma segura.")

    except oracledb.DatabaseError as e:
        error, = e.args
        logger.info(f"ERROR DE BASE DE DATOS: {error.code} - {error.message}")
    except Exception as e:
        logger.info(f"ERROR INESPERADO: {e}")
def listar_columnas():
    conexion = oracledb.connect(user=os.environ.get("DB_USER"), password=os.environ.get("DB_PASSWORD"), dsn=os.environ.get("DB_DSN"))
    cursor = conexion.cursor()
    
    # Vamos a revisar una tabla, por ejemplo NORMAS
    cursor.execute("SELECT column_name FROM all_tab_columns WHERE table_name = 'NORMAS' AND owner = 'DISENO'")
    columnas = cursor.fetchall()
    logger.info(f"Columnas en DISENO.NORMAS: {[c[0] for c in columnas]}")
    
    # Hagamos lo mismo con VOLTAJE_PRIMARIO
    cursor.execute("SELECT column_name FROM all_tab_columns WHERE table_name = 'VOLTAJE_PRIMARIO' AND owner = 'DISENO'")
    columnas = cursor.fetchall()
    logger.info(f"Columnas en DISENO.VOLTAJE_PRIMARIO: {[c[0] for c in columnas]}")
    
    conexion.close()

#listar_columnas()
if __name__ == "__main__":
    probar_conexion_magnetron()
    listar_columnas()