"""
state.py - Definición del Estado Global del Grafo (Memoria del Bot).

Propósito general:
Este módulo define el esquema `BotState` utilizando `TypedDict` y `Annotated`. 
Sirve como la "memoria RAM" compartida entre todos los nodos y escuadrones del sistema.
Todo agente lee de este estado y escribe sus resultados en él a medida que avanza el flujo.

Cuándo usarlo:
Se importa en la inicialización del `StateGraph` en `grafo.py` y se pasa como 
parámetro a todas las funciones nodo (ej. `def nodo_extractor_electrico(state: BotState):`).

Requisitos:
- Librería `typing` y `operator`.
"""

from typing import TypedDict, List, Dict, Any, Annotated
import operator

class BotState(TypedDict):
    # ==========================================
    # FASE 1: ENTRADAS Y EXTRACCIÓN
    # ==========================================
    run_id: str                     # Identificador de la corrida actual
    modo_interaccion: str           # cli | web
    archivos_entrada: List[str]     # Rutas locales de los archivos cargados
    ruta_documento: str             # El PDF, Excel o Word que subió el cliente
    texto_extraido: str             # El crudo (OCR / PyMuPDF)
    
    # ==========================================
    # FASE 2: INVENTARIO GLOBAL
    # ==========================================
    inventario_global: List[Dict]   # Ej: [{item: 1, kVA: 100}, {item: 2, kVA: 25}]
    ruta_excel_inventario: str      # Donde guardaremos el primer "Entregable Excel"
    cliente_identificado: str       # Nombre del cliente extraído de los datos de entrada
    # ==========================================
    # FASE 3: EL ENRUTADOR Y SUB-GRAFOS (TRABAJO POR FAMILIA)
    # ==========================================
    # Mantendremos este nombre por compatibilidad con tu código actual, 
    # pero ahora guardará la "Familia" en proceso (ej. "Convencional Pedestal")
    item_actual_id: str             
    
    # --- A. Datos de los 4 Escuadrones (Memoria de Trabajo) ---
    datos_electricos: Dict[str, Any]          # Lo que llene el Escuadrón Eléctrico
    datos_mecanicos: Dict[str, Any]           # Lo que llene el Escuadrón Mecánico
    datos_accesorios: Dict[str, Any]          # Lo que llene el Escuadrón de Accesorios
    datos_logisticos: Dict[str, Any]          # Lo que llene el Escuadrón Comercial/Logístico

    # --- B. Contadores de Reintentos (Fallback Logic) ---
    # Controlan cuántas veces el Extractor ha intentado buscar el dato antes de usar Norma ANSI
    intentos_electrico: int
    intentos_mecanico: int
    intentos_accesorios: int
    intentos_logistico: int

    # --- C. Canal de Comunicación Revisor -> Extractor ---
    # Aquí el Revisor anota: "Te faltó la impedancia, búscala en la página 4"
    feedback_electrico: str
    feedback_mecanico: str
    feedback_accesorios: str
    feedback_logistico: str
    errores_extraccion: List[str]   # Logs de errores del sistema

    # --- D. Alertas de Diseño (El Valor Agregado) ---
    # Los revisores anotarán aquí sus sugerencias normativas si el pliego es deficiente
    alertas_diseno: Annotated[List[str], operator.add]

    # --- E. Control SDM e Intervención Humana ---
    auditoria_sdm_ok: bool
    campos_faltantes_sdm: List[str]  # Lista de campos que el humano debe llenar
    respuestas_humanas: Dict[str, str] # Respuestas manuales inyectadas desde UI o consola
    datos_normalizados_sdm: dict
    # ==========================================
    # FASE 4: ESQUADRÓN COMERCIAL (Gaveta Comercial)
    # ==========================================
    # Estos campos son independientes de los técnicos
    resumen_comercial_ejecutivo: str  # El texto de las 8 secciones
    tabla_comercial_checklist: str    # La tabla Markdown para Excel

    # ==========================================
    # FASE 5: ENTREGABLES Y CIERRE (Acumuladores)
    # ==========================================
    # El operador 'operator.add' hace que los datos se concatenen en lugar de sobrescribirse
    resumenes_completados: Annotated[List[str], operator.add]
    fichas_tecnicas_finales: Annotated[List[Dict], operator.add]
    rutas_fichas_word: Annotated[List[str], operator.add]
    rutas_tablas_ctg: Annotated[List[str], operator.add] # Actualizado según tu test_martes.py
    rutas_sdm_json: Annotated[List[str], operator.add]
    # ==========================================
    # FASE 6: MODULOS DE TRABAJO --> LLAMADO A FUNCIONES ESPECIFICAS
    # ==========================================    
    configuracion: Dict[str, bool]  # Ej: {"solo_comercial": True, "generar_sdm": False}   
    

# ==========================================
# METADATA
# tools_used: [typing, operator]
# use_cases: [Gestión del estado de LangGraph, Pasaje de contexto entre agentes]
# reusable_components: [BotState]
# dependencies: []
# ==========================================
