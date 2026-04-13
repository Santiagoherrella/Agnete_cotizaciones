from langchain_core.prompts import ChatPromptTemplate
from src.corelogic import get_llm
from src.schemas.modelos import TablaCTGFamilia
from src.schemas.state import BotState
from src.tools.exportador import exportar_ctg_excel
from datetime import datetime

# ==========================================
# PROMPT: AGENTE DE CARACTERÍSTICAS GARANTIZADAS
# ==========================================
PROMPT_CTG = """
Eres un Ingeniero Eléctrico Especialista en Diseño de Transformadores en Magnetron S.A.S.
Tu tarea es extraer rigurosamente las Características Técnicas Garantizadas (CTG) para la siguiente familia de transformadores: {tipo_transformador}.

En el inventario del cliente, se solicitan las siguientes potencias (kVA) para esta familia específica: 
{variantes_solicitadas}

INSTRUCCIONES CRÍTICAS (PARA EL EQUIPO DE DETALLE):
1. Debes generar una columna de datos (VarianteCTG) por CADA UNA de las potencias solicitadas.
2. CERO ALUCINACIONES: Extrae los valores numéricos y técnicos exactos del pliego. 
3. Si un dato no se menciona en absoluto (ej. Impedancia, Pérdidas), debes escribir obligatoriamente "No especificado".
4. Presta especial atención al nivel de aislamiento (BIL), voltajes, derivaciones (Taps) y la eficiencia exigida.
5. Si el cliente indica una fórmula de pérdidas evaluadas (No-load / Load), inclúyela en los campos correspondientes.

TEXTO DEL PLIEGO Y CORREOS:
{texto_pliego}
"""

def nodo_generar_tablas_ctg(state: BotState):
    print("\n📊 [Agente CTG] Iniciando estructuración de Características Técnicas Garantizadas...")
    inventario = state.get("inventario_global", [])
    texto_crudo = state.get("texto_extraido", "")

    if not inventario or not texto_crudo:
        print("⚠️ [Agente CTG] Faltan datos en el estado para operar.")
        return {"rutas_tablas_ctg": []}

    # 1. Agrupar por familia (Ej: 'Padmounted', 'CSP')
    tipos_unicos = list(set([t["tipo_transformador"] for t in inventario if t["tipo_transformador"] != "No especificado"]))

    # 2. Configurar el LLM estricto
    llm = get_llm("agente_ctg")
    llm_estructurado = llm.with_structured_output(TablaCTGFamilia)
    prompt = ChatPromptTemplate.from_template(PROMPT_CTG)
    cadena = prompt | llm_estructurado

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    rutas_generadas = []

    # 3. Iterar sobre cada familia y generar su matriz
    for tipo in tipos_unicos:
        print(f"⚙️ [Agente CTG] Procesando matriz transversal para: {tipo}")
        
        # Filtrar solo los kVA que pertenecen a este tipo
        kvas_tipo = [item["potencia"] for item in inventario if item["tipo_transformador"] == tipo]
        variantes_str = ", ".join(kvas_tipo)

        # Invocar al modelo
        resultado: TablaCTGFamilia = cadena.invoke({
            "tipo_transformador": tipo,
            "variantes_solicitadas": variantes_str,
            "texto_pliego": texto_crudo
        })

        # 4. Enviar a la herramienta de exportación (Excel)
        ruta_excel = exportar_ctg_excel(resultado, timestamp)
        rutas_generadas.append(ruta_excel)

    return {"rutas_tablas_ctg": rutas_generadas}