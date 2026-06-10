import re
import pandas as pd
import os
import streamlit as st
import oracledb
from dotenv import load_dotenv

load_dotenv()

# Inicializar Thick Mode de forma segura
try:
    oracle_client_lib_dir = os.environ.get("ORACLE_CLIENT_LIB_DIR", "").strip()
    if oracle_client_lib_dir:
        oracledb.init_oracle_client(lib_dir=oracle_client_lib_dir)
except oracledb.ProgrammingError:
    pass
except Exception as e:
    print(f"⚠️ Aviso Oracle Client: {e}")

@st.cache_data(show_spinner=False, ttl=3600)
def cargar_tablas_desde_oracle():
    print("\\n🔌 [Caché] Conectando a Oracle DB para cargar tablas maestras...")
    db_local = {}
    user     = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    dsn      = os.environ.get("DB_DSN")

    if not all([user, password, dsn]):
        print("❌ Error: Credenciales incompletas en .env")
        return db_local

    try:
        conexion = oracledb.connect(user=user, password=password, dsn=dsn)
        consultas = {
            "paises":        "SELECT IDPAIS, PAIS, FRECUENCIA FROM DISENO.PAISES",
            "normas":        "SELECT IDNORMA, NORMA, NORMA_ABR, IDPAIS, ALTURA, TI, TR, DTC, DTA FROM DISENO.NORMAS",
            "potencias":     "SELECT IDKVA, POTENCIA, FASES FROM DISENO.POTENCIA",
            "voltajes_pri":  "SELECT IDVP, VP, E1, E11, CONEXE1, CONEXE11 FROM DISENO.VOLTAJE_PRIMARIO",
            "voltajes_sec":  "SELECT IDVS, VS, E2, E21, CONEXE2, FASES FROM DISENO.VOLTAJE_SECUNDARIO",
        }
        cursor = conexion.cursor()
        for clave, query in consultas.items():
            try:
                cursor.execute(query)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                db_local[clave] = pd.DataFrame(rows, columns=cols)
            except Exception as e:
                db_local[clave] = pd.DataFrame()
        cursor.close()
        conexion.close()
        print("🔌 Conexión a Oracle DB cerrada exitosamente.\\n")
    except Exception as e:
        print(f"❌ Error crítico de conexión a Oracle: {e}")
    return db_local

class MotorNormalizacionSDM:
    def __init__(self):
        self.db = cargar_tablas_desde_oracle()

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
            return df, True, f"🚨 SDM: Tabla {nombre_display} vacía o no cargada desde Oracle."
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
        return None, None, f"🚨 SDM: País '{texto_geografico}' no encontrado."

    def normalizar_norma(self, norma_cruda: str, id_pais: str):
        df, vacio, alerta_error = self._df_vacio("normas", "NORMAS")
        if vacio: return None, None, alerta_error

        norma_limpia = str(norma_cruda).strip().upper()
        if norma_limpia in ("", "NO ESPECIFICADO", "NAN"):
            if id_pais == "H": norma_limpia = "ANSI"
            elif id_pais == "0": norma_limpia = "NTC"
            else: return None, None, "🚨 SDM: Norma no especificada."

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
            if id_pais and not filtro[filtro["IDPAIS"] == id_pais].empty:
                filtro = filtro[filtro["IDPAIS"] == id_pais]
            return str(filtro.iloc[0]["IDNORMA"]), str(filtro.iloc[0]["NORMA"]), None
        return None, None, f"🚨 SDM: Norma asociada a '{busqueda}' no encontrada."

    def normalizar_potencia(self, kva_crudo: str):
        valor_num = self.extraer_numero(kva_crudo)
        if valor_num is None: return None, None, "🚨 SDM: Potencia inválida."

        df, vacio, alerta_error = self._df_vacio("potencias", "POTENCIA")
        if vacio: return None, None, alerta_error

        df["POTENCIA"] = pd.to_numeric(df["POTENCIA"], errors="coerce")
        # Tolerancia pequeña para flotantes
        filtro = df[abs(df["POTENCIA"] - valor_num) < 0.01]
        
        if not filtro.empty:
            return str(filtro.iloc[0]["IDKVA"]), f"{int(filtro.iloc[0]['POTENCIA'])} kVA", None
        return None, None, f"🚨 SDM: Potencia {valor_num} kVA no encontrada."

    def normalizar_voltaje_primario(self, vp_crudo: str):
        valor_num = self.extraer_numero(vp_crudo)
        if valor_num is None: return None, None, "🚨 SDM: Voltaje Primario inválido."
        if valor_num < 1000 and "kv" in str(vp_crudo).lower(): valor_num *= 1000

        df, vacio, alerta_error = self._df_vacio("voltajes_pri", "VOLTAJE_PRIMARIO")
        if vacio: return None, None, alerta_error

        valor_str = str(int(valor_num)) if valor_num == int(valor_num) else str(valor_num)
        filtro = df[df["E1"].astype(str).str.strip() == valor_str]
        if not filtro.empty:
            return str(filtro.iloc[0]["IDVP"]), str(filtro.iloc[0]["VP"]), None
        return None, None, f"🚨 SDM: Voltaje primario {valor_str} V no encontrado."

    def normalizar_voltaje_secundario(self, vs_crudo: str):
        valor_num = self.extraer_numero(vs_crudo)
        if valor_num is None: return None, None, "🚨 SDM: Voltaje Secundario inválido."

        df, vacio, alerta_error = self._df_vacio("voltajes_sec", "VOLTAJE_SECUNDARIO")
        if vacio: return None, None, alerta_error

        df["E2"] = pd.to_numeric(df["E2"], errors="coerce")
        # Tolerancia pequeña para flotantes
        filtro = df[abs(df["E2"] - valor_num) < 0.01]
        if not filtro.empty:
            return str(filtro.iloc[0]["IDVS"]), str(filtro.iloc[0]["VS"]), None
        return None, None, f"🚨 SDM: Voltaje secundario {valor_num} V no encontrado."
