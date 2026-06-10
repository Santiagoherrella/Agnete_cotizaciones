# 🤖 Sistema Multi-Agente de Análisis de Cotizaciones - Magnetron S.A.S.

![Estado](https://img.shields.io/badge/Estado-En_Pruebas-success)
![Arquitectura](https://img.shields.io/badge/Arquitectura-LangGraph_Multi--Agent-blue)
![Precisión](https://img.shields.io/badge/Precisi%C3%B3n-Granular-orange)
![Database](https://img.shields.io/badge/Database-Oracle_11g-red)

## 📖 1. Visión General del Proyecto

Este proyecto nació con un objetivo claro: **automatizar y blindar comercialmente la extracción de información técnica de pliegos de condiciones (RFPs/Licitaciones) complejos**. 

En la industria de transformadores, un error en la lectura de pérdidas, voltajes o accesorios puede costar decenas de miles de dólares. Este sistema actúa como un equipo de ingenieros virtuales que lee PDFs, clasifica los equipos requeridos y genera documentos listos para Ingeniería y Producción sin "alucinaciones" de Inteligencia Artificial.

---

## 🧠 2. La Filosofía MECE: Divide y Vencerás

Para evitar el "Efecto Embudo" (donde un solo modelo de lenguaje olvida detalles críticos al procesar mucha información), el sistema fue diseñado bajo el principio **MECE (Mutually Exclusive, Collectively Exhaustive)**:
* **Mutuamente Excluyentes:** La información eléctrica no se mezcla con la mecánica; cada una tiene su propio "cerebro" analizando el documento de forma paralela.
* **Colectivamente Exhaustivos:** Sumando todas las divisiones, abarcamos el 100% del pliego sin dejar "puntos ciegos".

Esto nos llevó a abandonar los "Prompts Gigantes" y crear **Escuadrones Especializados**.

---

## 🏗️ 3. Arquitectura de Agentes (El Core)

El sistema está orquestado con `LangGraph`, funcionando como una verdadera línea de ensamblaje de fábrica. Está compuesto por:

### Fase 1 y 2: Preparación e Inventario
* **🕵️‍♂️ Enrutador de Documentos:** Evalúa si el documento subido es un Pliego Técnico real o "basura" (Ej: correos de seguimiento). Si es pliego, autoriza el arranque.
* **📋 Agente de Inventario:** Escanea el pliego y extrae la lista exacta de transformadores solicitados (Cantidades, kVA, Voltajes y Familia).

### Fase 3: Los 5 Escuadrones (Mapeo Granular)
Cada familia de transformadores (Ej: *CSP*, *Padmounted*) pasa por 5 escuadrones compuestos por un **Extractor** y un **Revisor (Crítico)**. Utilizan modelos de datos estrictos (`Pydantic`) para forzar la extracción de variables específicas (ej. *perforaciones en aisladores BT*, *desfase angular*):
1.  **⚡ Escuadrón Eléctrico:** Impedancias, voltajes, BIL, grupos de conexión.
2.  **🔩 Escuadrón Mecánico:** Pintura, refrigeración (KNAN), núcleos, dimensiones.
3.  **🧰 Escuadrón Accesorios:** Pararrayos, CTs, válvulas, placas de características.
4.  **🚚 Escuadrón Logístico:** Normativa (ANSI/IEEE), embalaje, multas e Incoterms.
5.  **💼 Escuadrón Comercial:** Condiciones generales, formas de pago, garantías, pólizas y evaluación económica.

### Fase 4: Aduana de Integridad y HITL (Human-in-the-Loop)
Ates de generar cualquier archivo de ingeniería, un **Agente Auditor SDM** verifica que existan los datos críticos obligatorios (ej. Impedancia,BIL, Tipo de Aceite).
Si el pliego es omiso, el flujo se detiene y activa un nodo de **Intervención Humana**, permitiendo al usuario ingresar los datos faltantes por consola para reanudar el proceso sin perder el trabajo previo.

---

## ⚙️ 4. Flujo de Trabajo Automatizado (Pipeline)

La orquestación funciona mediante un **Supervisor por Familias**:
1. El sistema genera el *Inventario Global*.
2. El Supervisor toma la primera "Familia" encontrada (Ej: Transformadores Convencionales).
3. Pasa la batuta secuencialmente por los 5 Escuadrones.
4. Genera los entregables de esa familia.
5. Repite el ciclo con la siguiente familia hasta terminar.

---

## 📦 5. Entregables Desacoplados (Macro vs. Micro)

Una decisión arquitectónica clave del proyecto fue separar la información cualitativa de la cuantitativa para proteger la matriz comercial. "La precisión vale más que el ahorro de tokens".
### 📄 A. Resumen Ejecutivo (El Word) - *Visión Macro*
* **Objetivo:** Brindar contexto al diseñador.
* **Generación:** Determinista mediante `python-docx` puro. Ensambla los JSON previamente validados por los escuadrones y los limpia de caracteres basura OCR.
* **Resultado:** Un documento corporativo ordenado, señalando si un dato vino del pliego o fue asumido por norma, con alertas rojas 🚨 para vacíos de información crítica.

### 📊 B. Características Técnicas Garantizadas (Excel CTG) - *Visión Micro*
* **Objetivo:** Matriz comercial milimétrica.
* **Generación:** Posee un *Cerebro LLM Independiente* de alta capacidad (gpt-5.4/equivalente).
* **Mapeo 1 a 1:** Toma la lista exacta de equipos del inventario y fuerza al modelo a extraer de las tablas del pliego las **Pérdidas en vacío, Pérdidas con carga y Fases** específicas para cada kVA. No alucina voltajes porque los cruza directamente con el Excel de Inventario inicial.

### 💾 C. Archivo de Interfaz de Diseño (JSON SDM) - *Conexión con herramientas de Ingeniería*
* **Objetivo:** Conexión con herramientas de Ingeniería y eliminación de la re-digitación manual.
* **Generación:** Un archivo estructurado (`.json`) generado individualmente por cada transformador detectado en el inventario. Posee **conexión en vivo con Oracle 11g** (vía `oracledb` Thick Mode), mapeando el texto crudo del pliego a IDs relacionales oficiales del sistema de diseño (`IDKVA`, `IDVP`, `IDNORMA`).
* **Resultado:** Contiene los parámetros de diseño limpios, normalizados y cruzados contra la base de datos relacional de planta, listos para ser importados automáticamente por el Software de Diseño Magnetron (SDM).

### 💼 D. Checklist y Resumen Comercial - *Evaluación de Licitación*
* **Objetivo:** Definir las condiciones comerciales de la oferta (garantías, pólizas, penalidades, multas, tiempos de entrega, etc.).
* **Generación:** Procesado por el `escuadron_comercial` y exportado mediante el `exportador_comercial`.
* **Resultado:** 
  - **Resumen Ejecutivo Comercial (Word):** Análisis narrativo del pliego.
  - **Checklist Comercial (Excel):** Tabla estructurada con las condiciones de evaluación económica y legal, lista para la toma de decisiones comerciales.
---

## 🛠️ 6. Stack Tecnológico

* **Lenguaje:** Python 3.10+
* **Orquestación:** LangGraph / LangChain
* **Estructuración de Datos:** Pydantic
* **Procesamiento Documental:** PyPDF2 / pdfplumber (según parser configurado)
* **Generación de Entregables:** Pandas (`.xlsx`), python-docx (`.docx`)
* **Base de Datos:** `oracledb` (Thick Mode) → Oracle 11g de planta
* **Modelos de Lenguaje:** APIs de alta capacidad para razonamiento complejo de tablas de ingeniería (OpenAI GPT-5.4).

---

## 🚀 7. Instrucciones de Ejecución

Para iniciar el ciclo completo de procesamiento:

```bash
# Activar entorno virtual
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Ejecutar el motor orquestador
python test_martes.py
```

---

## 🛠️ 8. Instalación

Para configurar el entorno y correr el proyecto en local, sigue estos pasos:

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd agente_cotizaciones
   ```

2. **Crear y activar un entorno virtual (Recomendado):**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Descargar Oracle Instant Client (Requerido para Thick Mode):**
   El sistema se conecta a una base de datos Oracle 11g mediante `oracledb` en **Thick Mode**, lo cual requiere las librerías nativas de Oracle.
   - Descargar el **Oracle Instant Client (Basic Package)** desde [oracle.com](https://www.oracle.com/database/technologies/instant-client/downloads.html) (versión compatible con Oracle 11g).
   - Descomprimir en una ruta local (Ej: `C:\oracle\instantclient_21_x`).
   - Agregar dicha ruta a la variable de entorno `PATH` del sistema, o configurar `oracledb.init_oracle_client(lib_dir=...)` en el código.

4. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔐 9. Variables de Entorno

El sistema depende de múltiples proveedores de IA, debes proveer los tokens dentro de un archivo `.env` en la raíz del proyecto. Solo se requieren sus nombres (no incluyas valores reales en ramas públicas):

```env
# --- APIs de Modelos de Lenguaje ---
GOOGLE_API_KEY=tu_token_aqui
TOGETHER_API_KEY=tu_token_aqui
GROK_API_KEY=tu_token_aqui
OPENAI_API_KEY=tu_token_aqui

# --- Base de Datos Oracle (Magnetron Planta) ---
DB_USER=tu_usuario_aqui
DB_PASSWORD=tu_contraseña_aqui
DB_DSN=IP:PUERTO/SERVICIO
```

---

## 📂 10. Árbol de Estructura del Proyecto

```text
agente_cotizaciones/
├── data/                      # Archivos temporales o de entrada y salida
├── src/                       # Código fuente principal
│   ├── agents/                # Agentes IA especializados
│   │   ├── ctg.py                 # Agente de Características Técnicas Garantizadas
│   │   ├── escuadron_accesorios.py# Escuadrón Extractor de Accesorios
│   │   ├── escuadron_electrico.py # Escuadrón Extractor Eléctrico
│   │   ├── escuadron_logistico.py # Escuadrón Extractor Logístico
│   │   ├── escuadron_mecanico.py  # Escuadrón Extractor Mecánico
│   │   ├── inventario.py          # Agente para extracción de inventario y cantidades
│   │   └── resumen_general.py     # Generador de resumen ejecutivo
│   ├── schemas/               # Modelos Pydantic y estado 
│   │   ├── modelos.py             # Modelos de datos estrictos pydantic
│   │   └── state.py               # Definición de estados para LangGraph
│   ├── tools/                 # Herramientas y utilidades complementarias
│   │   ├── exportador.py          # Herramienta de generación de Excel/Word final
│   │   ├── exportador_comercial.py# Exportador de entregables comerciales (Word/Excel)
│   │   ├── exportador_sdm.py      # Exportador de archivos JSON SDM individuales
│   │   ├── extractor.py           # Scraping o preprocesamiento de PDF a texto
│   │   └── normalizador_sdm.py    # Conexión en vivo con Oracle DB y Regex
│   ├── corelogic.py           # Lógica central del sistema
│   └── grafo.py               # Definición y orquestación del LangGraph
├── test/                      # Entorno de pruebas
├── config.json                # Configuraciones del sistema
├── requirements.txt           # Dependencias del proyecto
├── start.py                   # Script base de inicio
└── test_martes.py             # Ejecutador/orquestador del pipeline principal
```

---

## 📤 11. Ejemplo de Salida (Resultados Generados)

Una vez que el sistema finaliza, genera dos entregables clave:

1. **📄 Resumen_Ejecutivo.docx (Visión Macro)**
   - *Sección Eléctrica:* "Transformador de 45 kVA, Voltaje Primario 13200V. (Extraído directo de tabla)"
   - *Sección Logística:* "Normativa aplicable: ANSI/IEEE C57.12.00 (Falta confirmar incoterm 🚨)"
2. **📊 CTG_Exportado.xlsx (Visión Micro)**
   - Una grilla (Excel) estricta, cruce directo "1 a 1" por kVA, garantizando sin alucinaciones: 
     - **Fabricante:** MAGNETRON S.A.S. (Forzado comercialmente)
     - **Fases, Pérdidas en vacío, Pérdidas bajo carga**, etc. Mapeadas y listas para el ERP o para su revisión final.

---

## 📝 12. CHANGELOG

* **2026-05-06 | `<hash>`:** CUS2024-021 - Estabilización de motor Regex en `normalizador_sdm.py` para ignorar separadores de miles y limpieza de inferencia geográfica (eliminación de dobles barras). Flujo de cruce con Oracle DB 100% exitoso y sin errores.
* **2026-05-05 | `fde34d1`:** CUS2024-020 - Integración de Alineador Normativo y motor de mapeo relacional SDM, conectado con base de datos SQLDeveloper de Oracle mediante `oracledb` (Thick Mode), con actualización de caché automática.
* **2026-04-30 | `87b34d9`:** CUS2024-019 - Integración de Alineador Normativo y motor de mapeo relacional SDM (CSV locales).
* **2026-04-28 | `1dbb604`:** CUS2024-018 - Fix lógica de enrutamiento para SDM y documentos técnicos, resolución de bucle infinito en supervisor.
* **2026-04-27 | `2040e62`:** CUS2024-017 - WIP: Implementación de enrutamiento modular con flags booleanos y flujo comercial independiente.
* **2026-04-26 | `51051a7`:** CUS2024-017 - Integración de Escuadrón Comercial con generación independiente de Word y Excel.
* **2026-04-25 | `a635694`:** CUS2024-016 - Generación dinámica de JSON SDM individuales. Prompts forzados en español.
* **2026-04-23 | `06fdf46`:** CUS2024-015 - Integración de Agente Auditor SDM, Intervención Humana (HITL) y exportación JSON.
* **2026-04-22 | `9d60b88`:** CUS2024-014 - Documentación exhaustiva: Metadata YAML, docstrings y estandarización.
* **2026-04-21 | `f685dfd`:** CUS2024-013 - Definición de arquitectura MECE y manual de usuario inicial.
* **2026-04-21 | `7c69f87`:** CUS2024-012 - Ajustes finales en validación de modelos Pydantic y lógica CTG.
* **2026-04-20 | `b51809f`:** CUS2024-011 - Refactorización del Ensamblaje Final. Cerebro CTG y limpieza OCR.
* **2026-04-07 | `86a3fef`:** CUS2024-010 - Integración Completa de la Fábrica de Especialistas.
* **2026-04-07 | `07cf253`:** CUS2024-009 - Escuadrón Eléctrico con Revisor Iterativo y Fallback ANSI.
* **2026-04-01 | `20f3a10`:** CUS2024-008 - Implementación de Fábrica de Modelos y enrutamiento dinámico.
* **2026-03-31 | `bcca073`:** CUS2024-007 - Integración de Agente CTG, extracción EML y escudo anti-basura.
* **2026-03-31 | `8606570`:** CUS2024-006 - Exportación nativa a Word/Excel.
* **2026-03-30 | `767ce8f`:** CUS2024-005 - Limpieza de repositorio e ignore de temporales.
* **2026-03-30 | `f6b83f4`:** CUS2024-004 - Implementar agente de resumen ejecutivo por familia.
* **2026-03-30 | `6439380`:** CUS2024-003 - Implementar Enrutador Multiagente Batch.
* **2026-03-30 | `3ec1125`:** CUS2024-001 - Primera base funcional Fase 1 - Extracción de Inventario.

---

## 📚 13. Documentación Extendida

Se ha realizado un proceso exhaustivo de documentación en todo el repositorio, agregando metadata YAML y docstrings detallando el propósito y uso de cada módulo:
- `src/corelogic.py`: Gestión de selección e inicialización de LLMs.
- `src/grafo.py`: Orquestador principal (Máquina Magnetrón).
- `src/agents/`: Nodos especializados de extracción técnica, logística y comercial, incluyendo Auditores y Alineadores Normativos.
- `src/tools/`: Utilidades exportadoras (Excel/Word/JSON), motores de conexión a bases de datos relacionales (`normalizador_sdm.py`) y lectores PDF/EML.
- `src/schemas/`: Componentes Pydantic strict-mode garantes del tipado desde el estado de LangGraph hasta el Output Parser final.