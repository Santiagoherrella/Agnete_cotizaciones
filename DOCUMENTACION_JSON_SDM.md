# Documentación del JSON de Integración SDM (Agente de Cotizaciones)

Este documento explica la estructura del JSON generado por el **Agente de Cotizaciones** para su consumo en el sistema de diseño **SDM**. Está dirigido al equipo de desarrollo (backend/integración) para que comprendan qué significa cada campo, sin necesidad de ser expertos en diseño de transformadores eléctricos.

---

## Estructura General

El JSON representa **un único equipo (o ítem) solicitado en un pliego de condiciones**. Si un cliente pide varios tipos de transformadores, el agente generará un archivo JSON independiente para cada uno.

El archivo está dividido en **tres grandes bloques**:
1. **Metadatos Básicos**: Información general de trazabilidad.
2. **IDs de Mapeo (Oracle)**: Llaves foráneas (`Foreign Keys`) listas para cruzar con la base de datos maestra.
3. **Parámetros de Diseño**: El corazón técnico del equipo, con datos crudos y normalizados.

---

## 1. Metadatos Básicos

Ubicados en la raíz del JSON, sirven para identificar el contexto de la solicitud.

```json
"software": "SDM - Magnetron",
"identificador_pliego": "300 KVA Padmounted Transformer",
"cantidad_solicitada": 1
```

* **`software`**: Constante que indica el sistema destino.
* **`identificador_pliego`**: Nombre o título del ítem tal como venía en el documento del cliente. Útil para logs y UI.
* **`cantidad_solicitada`**: Número de unidades que el cliente desea comprar de este diseño exacto.

---

## 2. Bloque `ids_mapeo_oracle`

Este objeto es vital para el equipo de Backend. Contiene los IDs de las tablas maestras de Oracle (`DISENO.PAISES`, `DISENO.NORMAS`, `DISENO.POTENCIA`, etc.). 
Si el agente logró hacer *match* entre el texto del cliente y la base de datos de Magnetrón, estos campos tendrán un número. Si no hubo *match* o no se requiere, serán `null`.

```json
"ids_mapeo_oracle": {
    "id_pais": "H",
    "id_norma": "41",
    "id_kva": "27",
    "id_vp": "41",
    "id_vs": "17"
}
```

* **`id_pais`**: ID en la tabla `PAISES`. 
* **`id_norma`**: ID de la norma de fabricación (ej. ANSI, IEC) en la tabla `NORMAS`.
* **`id_kva`**: ID de la potencia del transformador en la tabla `POTENCIA`.
* **`id_vp`**: ID de la configuración del Voltaje Primario en `VOLTAJE_PRIMARIO`.
* **`id_vs`**: ID de la configuración del Voltaje Secundario en `VOLTAJE_SECUNDARIO`.

> **Nota para el desarrollador**: Usen estos IDs para hacer los `JOINs` directos en Oracle. Eviten hacer cruces por texto.

---

## 3. Bloque `parametros_diseno`

Este es el bloque más extenso y contiene todos los datos de ingeniería eléctrica y mecánica traducidos a un formato estándar.

### Potencia y Voltaje (Eléctricos Base)
```json
"potencia_kva": 300.0,
"voltaje_primario_texto": "13200 Grd. Y / 7620",
"voltaje_secundario_texto": "480 Y / 277",
"fases": 3
```
* **`potencia_kva`**: La "fuerza" del transformador (kVA) como valor numérico flotante.
* **`voltaje_primario_texto` / `voltaje_secundario_texto`**: Cadenas de texto crudas con la configuración del voltaje (incluyendo si están conectados en Estrella "Y", Delta, etc). **Importante**: No conviertan esto ciegamente a números solos, ya que la letra "Y" o el símbolo "/" indican el conexionado físico (fase-neutro).
* **`fases`**: `1` (monofásico) o `3` (trifásico).

### Geografía y Norma
```json
"pais_instalacion": "ESTADOS UNIDOS",
"norma_diseno": "ANSI C57.12.34",
"tipo_transformador": "Padmount"
```
* Indican el entorno de trabajo del equipo. El `tipo_transformador` hace referencia a la familia constructiva (ej. poste, pedestal/padmount).

### Aislamiento (BIL)
```json
"bil_primario_kv": 95.0,
"bil_secundario_kv": 30.0
```
* **BIL** (*Basic Insulation Level*): Nivel de aislamiento para soportar descargas (como rayos). Son valores flotantes (en kV).

### Conmutación (Taps)
```json
"conmutacion": {
    "es_conmutable": true,
    "taps_rango_porcentaje": "Dos derivaciones 2,5 % arriba y dos derivaciones 2,5 % abajo",
    "cantidad_taps": 4,
    "paso_porcentaje": 2.5
}
```
* Define si el voltaje primario se puede ajustar ligeramente con un selector (conmutador). Si `es_conmutable` es `false`, los demás campos serán `null`.

### Impedancia y Fluidos (Requisitos SDM)
```json
"impedancia_porcentaje": 5.75,
"impedancia_estandar_tccf": "ANSI",
"tipo_aceite": "Aceite Mineral Tipo II"
```
* **Impedancia**: Resistencia interna del equipo al flujo eléctrico. 
* **Aceite**: El líquido usado para enfriar el equipo por dentro.
>  Estos dos datos **son obligatorios** para que el SDM pueda iniciar un diseño geométrico. Si llegan en `null` o `"No especificado"`, significa que el pliego no los traía.

### Pérdidas (Eficiencia Eléctrica)
```json
"perdidas_no_carga_w": 500,
"perdidas_no_carga_estandar_w": null,
"perdidas_carga_w": 2500,
"perdidas_carga_estandar_w": null
```
* Representan cuánta energía desperdicia el transformador (en Watts `W`) al estar encendido sin uso (`no_carga_w`) o operando al 100% (`carga_w`).

### Eficiencia Global
```json
"eficiencia_pliego_texto": "Cumplimiento con requisitos DOE 2016",
"eficiencia_porcentaje": 99.5,
"eficiencia_estandar_clasificada": "DOE",
```
* **`eficiencia_estandar_clasificada`**: Normalizado por la Inteligencia Artificial a valores estandarizados como `"DOE"`, `"ECCC"`, etc., para cruzar con la tabla `EFICIENCIA_BK` de Oracle.

### Evaluación de Pérdidas (TOC - Total Ownership Cost)
```json
"evaluacion_perdidas_economicas": {
    "aplica_capitalizacion": true,
    "formula_capitalizacion_texto_crudo": "A = 4.5 USD/W, B = 1.2 USD/W",
    "k1_normalizado_usd_w": 4.5,
    "k2_normalizado_usd_w": 1.2,
    "k3_normalizado_usd_w": null,
    "k4_normalizado_usd_w": null
}
```
* Define si el cliente aplicará multas/bonificaciones económicas basadas en el desempeño del equipo. 
* Si `aplica_capitalizacion` es `true`, los valores `k1` y `k2` (y opcionalmente `k3`, `k4`) traerán un factor monetario **siempre normalizado a USD por Watt ($/W)**.
* Backend puede usar estos multiplicadores directamente en sus cálculos financieros sin preocuparse por si el pliego venía en kW o W.

### Dimensiones Físicas y Otros
```json
"dimensiones_limites": {
    "alto_mm": 1800.0,
    "ancho_mm": null,
    "largo_mm": null,
    "peso_total_kg": 2500.0
},
"certificacion_ul": false
```
* Restricciones físicas de tamaño impuestas por el cliente en el documento. Si todo es `null`, el diseñador tiene libertad para construirlo del tamaño estándar.
* **`certificacion_ul`**: Booleano que indica si se requiere el costoso sello de validación UL en EE.UU.

---

## Buenas prácticas al consumir este JSON

1. **Gestión de Nulos**: Todos los campos (excepto los garantizados en la validación inicial) pueden venir como `null`. Su código backend debe utilizar `.get("campo")` de manera segura y tener valores por defecto cuando aplique.
2. **Strings vs Floats**: Campos terminados en `_kva`, `_v`, `_w`, `_kv`, `_mm`, `_kg` o `_usd_w` están estrictamente tipados como flotantes (`Float`). Los campos terminados en `_texto` o `_crudo` son `String`.
3. **Flujo de Bloqueo**: Si reciben `impedancia_porcentaje = null`, el SDM no podrá iniciar el diseño automático y deberá levantar una alerta visual al usuario en el sistema.
