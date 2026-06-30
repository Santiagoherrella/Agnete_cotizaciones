import re
import pandas as pd
import os
import json
import streamlit as st
import oracledb
from dotenv import load_dotenv
from src.utils.logger import get_logger
logger = get_logger("NormalizadorSdm")


try:
    from src.corelogic import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    pass # Por si no se ejecuta en un entorno donde esté disponible

load_dotenv()

# Inicializar Thick Mode de forma segura
try:
    oracle_client_lib_dir = os.environ.get("ORACLE_CLIENT_LIB_DIR", "").strip()
    if not oracle_client_lib_dir:
        oracle_client_lib_dir = r"C:\oracleinstantclient.23.26.1.0.0"
    oracledb.init_oracle_client(lib_dir=oracle_client_lib_dir)
except oracledb.ProgrammingError:
    pass
except Exception as e:
    logger.info(f" Aviso Oracle Client: {e}")

@st.cache_data(show_spinner=False, ttl=3600)
def cargar_tablas_desde_oracle():
    logger.info("\\n[Caché] Conectando a Oracle DB para cargar tablas maestras...")
    db_local = {}
    user     = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    dsn      = os.environ.get("DB_DSN")

    if not all([user, password, dsn]):
        logger.info(" Error: Credenciales incompletas en .env")
        return db_local

    try:
        conexion = oracledb.connect(user=user, password=password, dsn=dsn)
        # Definimos las consultas con nombres de tabla limpios (sin _BK)
        consultas = {
            "paises": "SELECT IDPAIS, PAIS, FRECUENCIA FROM DISENO.PAISES",
            "normas": "SELECT IDNORMA, NORMA FROM DISENO.NORMAS",
            "potencias": "SELECT IDKVA, POTENCIA FROM DISENO.POTENCIA",
            "voltajes_pri": "SELECT IDVP, VP, E1, E11 FROM DISENO.VOLTAJE_PRIMARIO",
            "voltajes_sec": "SELECT IDVS, VS, E2, E21 FROM DISENO.VOLTAJE_SECUNDARIO",
            "caracteristicas_electricas": "SELECT * FROM DISENO.CARACTERISTICAS_ELECTRICAS",
            "eficiencia": "SELECT * FROM DISENO.EFICIENCIA_BK"
        }
        
        for clave, sql in consultas.items():
            try:
                df = pd.read_sql(sql, con=conexion)
                db_local[clave] = df
                logger.info(f"OK: Tabla {clave} cargada correctamente ({len(df)} registros).")
            except Exception as e:
                logger.info(f"ERROR: Error cargando tabla {clave}: {e}")
        
        conexion.close()
    except Exception as e:
        logger.info(f" Error crítico de conexión a Oracle: {e}")
    return db_local

class MotorNormalizacionSDM:
    def __init__(self):
        self.db = cargar_tablas_desde_oracle()

    def clasificar_eficiencia_y_toc(self, texto_eficiencia, texto_perdidas):
        """Usa el LLM para identificar si aplica evaluación de pérdidas (TOC) y qué norma de eficiencia se requiere."""
        try:
            llm = get_llm("agente_electrico")
            system_prompt = '''Eres un experto en ingeniería eléctrica clasificando datos de transformadores.
Tu tarea es devolver un JSON estricto con la siguiente estructura:
{
    "aplica_capitalizacion": bool, // true si el texto habla de TOC, factores de capitalización monetaria, K1, K2, o evaluación de pérdidas en dólares/moneda.
    "norma_eficiencia_clasificada": string // Nombre de la norma de eficiencia encontrada (ej. "DOE 2016", "NTC 819"). null si no se identifica.
}
Responde ÚNICAMENTE con el JSON validado. No añadas markdown ni texto adicional.
'''
            user_prompt = f"Texto Eficiencia: {texto_eficiencia}\nTexto Pérdidas: {texto_perdidas}"
            resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
            
            match = re.search(r'\{.*\}', resp.content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"aplica_capitalizacion": False, "norma_eficiencia_clasificada": None}
        except Exception as e:
            logger.info(f"Error en clasificador LLM de eficiencia: {e}")
            return {"aplica_capitalizacion": False, "norma_eficiencia_clasificada": None}

    def extraer_numero(self, texto) -> float | None:
        """Mejorada para manejar comas, espacios y decimales correctamente"""
        if pd.isna(texto) or str(texto).strip() in ("", "No especificado"):
            return None
        
        # Eliminar comas usadas como separador de miles
        texto_limpio = str(texto).replace(",", "")
        
        # Buscar el primer número, permitiendo decimales (Sin dobles barras)
        match = re.search(r"[-+]?\d*\.?\d+", texto_limpio)
        if match:
            num_str = match.group()
            if num_str == ".": return None
            return float(num_str)
        return None

    def _df_vacio(self, clave: str, nombre_display: str):
        df = self.db.get(clave, pd.DataFrame())
        if df.empty:
            return df, True, f"[!] Advertencia: Tabla {nombre_display} vacía o no cargada desde Oracle."
        df.columns = [col.upper() for col in df.columns]
        return df, False, None

    def normalizar_pais(self, pais_crudo: str):
        df, vacio, alerta_error = self._df_vacio("paises", "PAISES")
        if vacio: return None, None, alerta_error

        texto_geografico = str(pais_crudo).upper() if not pd.isna(pais_crudo) else "COLOMBIA"
        
        # Lógica de Inferencia Geográfica (Sin dobles barras)
        if re.search(r"\b(USA|US|EEUU|ESTADOS UNIDOS|AL|TX|FL|CA|NY|OH|SD)\b", texto_geografico):
            pais_limpio = "ESTADOS UNIDOS"
        elif re.search(r"\b(COLOMBIA|BOGOTA|MEDELLIN|PEREIRA|CALI)\b", texto_geografico):
            pais_limpio = "COLOMBIA"
        else:
            pais_limpio = texto_geografico.strip()

        filtro = df[df["PAIS"].astype(str).str.upper() == pais_limpio]
        if not filtro.empty:
            return str(filtro.iloc[0]["IDPAIS"]), str(filtro.iloc[0]["PAIS"]), None
        return None, None, f"SDM: País '{texto_geografico}' no encontrado."

    def normalizar_norma(self, norma_cruda: str, id_pais: str):
        df, vacio, alerta_error = self._df_vacio("normas", "NORMAS")
        if vacio: return None, None, alerta_error

        norma_limpia = str(norma_cruda).strip().upper()
        if norma_limpia in ("", "NO ESPECIFICADO", "NAN"):
            if id_pais == "H": norma_limpia = "ANSI"
            elif id_pais == "0": norma_limpia = "NTC"
            else: return None, None, "SDM: Norma no especificada."

        # Extraer palabras clave de la norma cruda (ANSI, IEEE, NTC)
        palabras_clave = []
        if "ANSI" in norma_limpia: palabras_clave.append("ANSI")
        if "IEEE" in norma_limpia: palabras_clave.append("IEEE")
        if "NTC" in norma_limpia: palabras_clave.append("NTC")
        
        # Si extrajo alguna palabra clave, usarla para buscar. Si no, fallback a ANSI si el país es H (USA)
        busqueda = palabras_clave[0] if palabras_clave else ("ANSI" if id_pais == "H" else "NTC")

        filtro = df[
            df["NORMA"].astype(str).str.upper().str.contains(busqueda, na=False) |
            (df.get("NORMA_ABR", pd.Series(dtype=str)).astype(str).str.upper().str.contains(busqueda, na=False))
        ]
        if not filtro.empty:
            if id_pais and "IDPAIS" in filtro.columns and not filtro[filtro["IDPAIS"] == id_pais].empty:
                filtro = filtro[filtro["IDPAIS"] == id_pais]
            return str(filtro.iloc[0]["IDNORMA"]), str(filtro.iloc[0]["NORMA"]), None
        return None, None, f"SDM: Norma asociada a '{busqueda}' no encontrada."

    def normalizar_potencia(self, kva_crudo: str):
        valor_num = self.extraer_numero(kva_crudo)
        if valor_num is None: return None, None, "SDM: Potencia inválida."

        df, vacio, alerta_error = self._df_vacio("potencias", "POTENCIA")
        if vacio: return None, None, alerta_error

        df["POTENCIA"] = pd.to_numeric(df["POTENCIA"], errors="coerce")
        # Tolerancia pequeña para flotantes
        filtro = df[abs(df["POTENCIA"] - valor_num) < 0.01]
        
        if not filtro.empty:
            return str(filtro.iloc[0]["IDKVA"]), f"{int(filtro.iloc[0]['POTENCIA'])} kVA", None
        return None, None, f"SDM: Potencia {valor_num} kVA no encontrada."

    def normalizar_voltaje_primario(self, vp_crudo: str):
        valor_num = self.extraer_numero(vp_crudo)
        if valor_num is None: return None, None, None, None, "SDM: Voltaje Primario inválido."
        if valor_num < 1000 and "kv" in str(vp_crudo).lower(): valor_num *= 1000

        df, vacio, alerta_error = self._df_vacio("voltajes_pri", "VOLTAJE_PRIMARIO")
        if vacio: return None, None, None, None, alerta_error

        valor_str = str(int(valor_num)) if valor_num == int(valor_num) else str(valor_num)
        filtro = df[df["E1"].astype(str).str.strip() == valor_str]
        if not filtro.empty:
            fila = filtro.iloc[0]
            e1 = fila.get("E1")
            e11 = fila.get("E11") if pd.notna(fila.get("E11")) else None
            return str(fila["IDVP"]), str(fila["VP"]), e1, e11, None
        return None, None, None, None, f"SDM: Voltaje primario {valor_str} V no encontrado."

    def normalizar_voltaje_secundario(self, vs_crudo: str):
        valor_num = self.extraer_numero(vs_crudo)
        if valor_num is None: return None, None, None, None, "SDM: Voltaje Secundario inválido."

        df, vacio, alerta_error = self._df_vacio("voltajes_sec", "VOLTAJE_SECUNDARIO")
        if vacio: return None, None, None, None, alerta_error

        df["E2"] = pd.to_numeric(df["E2"], errors="coerce")
        # Tolerancia pequeña para flotantes
        filtro = df[abs(df["E2"] - valor_num) < 0.01]
        if not filtro.empty:
            fila = filtro.iloc[0]
            e2 = fila.get("E2")
            e21 = fila.get("E21") if pd.notna(fila.get("E21")) else None
            return str(fila["IDVS"]), str(fila["VS"]), e2, e21, None
        return None, None, None, None, f"SDM: Voltaje secundario {valor_num} V no encontrado."
