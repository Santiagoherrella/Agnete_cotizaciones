from pydantic import BaseModel, Field
from typing import List, Optional

# ==========================================
# FASE 1 Y 2: ENRUTAMIENTO E INVENTARIO 
# ==========================================
class ClasificacionDocumento(BaseModel):
    tipo: str = Field(description="Clasifica el documento. Usa 'PLIEGO' si es un pliego de condiciones/RFP, de lo contrario 'OTRO'.")
    justificacion: str = Field(description="Breve justificación de la decisión")

class ItemTransformador(BaseModel):
    item_id: str = Field(description="Identificador del ítem o variante")
    cantidad: int = Field(description="Cantidad solicitada")
    potencia: str = Field(description="Potencia (ej. 50 kVA)")
    voltaje_primario: str = Field(description="Voltaje de alta tensión")
    voltaje_secundario: str = Field(description="Voltaje de baja tensión")
    tipo_transformador: str = Field(description="Familia o tipo constructivo (ej. CSP Polemount, Padmounted)")
    fases: str = Field(default="No especificado", description="Fases (ej. Monofásico, Trifásico)")

class InventarioPedido(BaseModel):
    equipos: List[ItemTransformador] = Field(description="Lista de todos los equipos encontrados en el pliego")


# ==========================================
# EL "SUB-MOLDE" DE RASTREO (Trazabilidad)
# ==========================================
class DatoValidado(BaseModel):
    valor: str = Field(description="El valor técnico extraído con sus unidades. Si no está en el pliego, pon 'No especificado'. NO INVENTES.")
    origen: str = Field(description="Origen del dato: 'Pliego', 'Norma ANSI', o 'No especificado'.")

# ==========================================
# FASE 3: LOS 4 ESCUADRONES (Ultra-Granulares)
# ==========================================

class DatosElectricos(BaseModel):
    # SECCIÓN 1: GENERALES
    tipo_transformador: DatoValidado = Field(description="Tipo de transformador(es) requerido(s)")
    capacidad_nominal: DatoValidado = Field(description="Capacidad(es) nominal(es) en kVA o MVA")
    aplicacion_entorno: DatoValidado = Field(description="Aplicación y entorno de instalación")
    altitud_temperatura: DatoValidado = Field(description="Altitud, temperatura ambiente y condiciones especiales")
    condiciones_servicio: DatoValidado = Field(description="Condiciones de servicio")
    
    # SECCIÓN 2: ELÉCTRICOS
    voltajes_nominales: DatoValidado = Field(description="Voltajes nominales (primario/secundario) y configuración")
    frecuencia: DatoValidado = Field(description="Frecuencia de operación")
    grupo_conexion_desfase: DatoValidado = Field(description="Grupo de conexión e información de desfase (Ej: 30°)")
    impedancia_cortocircuito: DatoValidado = Field(description="Impedancia de cortocircuito (%)")
    regulacion_taps: DatoValidado = Field(description="Regulación de tensión (taps)")
    nivel_perdidas_maximas: DatoValidado = Field(description="Nivel de pérdidas máximas permitidas. (Aclarar si es doble voltaje)")
    bil_primario_secundario: DatoValidado = Field(description="BIL (Nivel Básico de Aislamiento) primario y secundario")

class DatosMecanicos(BaseModel):
    # SECCIÓN 3: CONSTRUCTIVAS
    tipo_refrigeracion: DatoValidado = Field(description="Tipo de refrigeración (si es con aceite vegetal colocar KNAN)")
    material_bobinados: DatoValidado = Field(description="Materiales de bobinados")
    forma_constructiva: DatoValidado = Field(description="Forma constructiva de la parte activa")
    tipo_nucleo_material: DatoValidado = Field(description="Tipo de núcleo y material")
    sistema_aislamiento: DatoValidado = Field(description="Sistema de aislamiento")
    fluido_dielectrico: DatoValidado = Field(description="Aceite o fluido dieléctrico")
    caracteristicas_tanque: DatoValidado = Field(description="Características del tanque")
    sistemas_sellado: DatoValidado = Field(description="Sistemas de sellado")
    requisitos_sismicos: DatoValidado = Field(description="Requisitos sísmicos")
    dimensiones_peso_limites: DatoValidado = Field(description="Dimensiones y peso límites")
    radiadores_enfriamiento: DatoValidado = Field(description="Radiadores y sistemas de enfriamiento")
    
    # SECCIÓN 4: PINTURA
    preparacion_superficial: DatoValidado = Field(description="Preparación superficial requerida")
    tipo_pintura_acabado: DatoValidado = Field(description="Tipo de pintura base y acabado")
    espesor_pelicula_seca: DatoValidado = Field(description="Espesor mínimo de película seca")
    color_ral: DatoValidado = Field(description="Color RAL especificado")
    resistencia_corrosion: DatoValidado = Field(description="Requisitos de resistencia a corrosión y tratamientos")

class DatosAccesorios(BaseModel):
    # SECCIÓN 5: ACCESORIOS Y COMPONENTES
    equipamiento_proteccion: DatoValidado = Field(description="Equipamiento de protección")
    cambiadores_tension: DatoValidado = Field(description="Cambiadores de tensión o conmutadores")
    aisladores_at: DatoValidado = Field(description="Aisladores de alta tensión (Dependiendo del amperaje)")
    aisladores_bt_perforaciones: DatoValidado = Field(description="Aisladores de baja tensión (cantidad de perforaciones/spades por potencia)")
    pararrayos: DatoValidado = Field(description="Información de pararrayos (Surge arresters)")
    transformadores_corriente: DatoValidado = Field(description="Transformadores de corriente (CTs) u otros medidores")
    sistemas_monitoreo: DatoValidado = Field(description="Sistemas de monitoreo")
    gabinetes_cajas: DatoValidado = Field(description="Gabinetes/cajas de conexión")
    valvulas_alivio: DatoValidado = Field(description="Válvulas y dispositivos de alivio")
    sistemas_puesta_tierra: DatoValidado = Field(description="Sistemas de puesta a tierra")
    accesorios_especiales: DatoValidado = Field(description="Otros accesorios especiales")
    
    # SECCIÓN 7: IDENTIFICACIÓN 
    placa_caracteristicas: DatoValidado = Field(description="Requisitos de placas de características (cantidad y obligatoriedad)")
    etiquetado_documentacion: DatoValidado = Field(description="Etiquetado, marcación especial y documentación técnica requerida")

class DatosLogisticos(BaseModel):
    # SECCIÓN 6 Y JURÍDICA
    normas_aplicables: DatoValidado = Field(description="Estándares aplicables con número y título completo (IEEE/ANSI)")
    pruebas_ensayos: DatoValidado = Field(description="Pruebas, ensayos requeridos y certificaciones exigidas")
    penalizaciones_multas: DatoValidado = Field(description="Penalizaciones, multas o anexos jurídicos")
    
    # SECCIÓN 8 Y 9: EMBALAJE Y ENTREGABLES
    tipo_embalaje_preservacion: DatoValidado = Field(description="Tipo de embalaje, materiales, y requisitos de preservación")
    condiciones_transporte: DatoValidado = Field(description="Condiciones de transporte y horarios de entrega")
    lugar_entrega_incoterm: DatoValidado = Field(description="Lugar de entrega (Zip code) e Incoterm")
    entregables_oferta: DatoValidado = Field(description="Planos, declaración de pérdidas o formatos solicitados con la oferta")

# ==========================================
# FASE 4: CTG INDEPENDIENTE (Restaurado)
# ==========================================
class VarianteCTG(BaseModel):
    fabricante: str = Field(description="Manufacturer")
    tipo: str = Field(description="Type")
    normas: str = Field(description="Manufacturing standards")
    kva: str = Field(description="kVA Rating")
    fases: str = Field(description="Phase")
    voltaje_primario: str = Field(description="Primary Voltage")
    bil_primario: str = Field(description="Primary BIL")
    taps: str = Field(description="Taps")
    voltaje_secundario: str = Field(description="Secondary Voltage")
    bil_secundario: str = Field(description="Secondary BIL")
    grupo_conexion: str = Field(description="Connection group")
    frecuencia: str = Field(description="Frequency")
    eficiencia: str = Field(description="DOE 2016 Efficiency (%)")
    perdidas_vacio: str = Field(description="No-load losses @20°C (W)")
    perdidas_carga: str = Field(description="Load losses @ 85°C - 100% loaded (W)")

class TablaCTGFamilia(BaseModel):
    tipo_transformador: str = Field(description="Tipo de transformador")
    variantes: List[VarianteCTG] = Field(description="Lista de variantes, UNA POR CADA EQUIPO solicitado")