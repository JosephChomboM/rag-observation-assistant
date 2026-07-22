# Handoff del proyecto Gestor de Observaciones

> Documento de continuidad para retomar el proyecto en otro dispositivo o en otra tarea de Codex.
>
> Estado comprobado del repositorio: 22 de julio de 2026.
> Rama: `main`.
> Commit actual: `d970c54` (`Refactor configuration and enhance observation generation with new schemas and runtime settings`).
> El worktree estaba limpio al crear este documento.

## 1. Objetivo del proyecto

El proyecto genera observaciones metodologicas a partir de:

- un Excel maestro administrado por el equipo responsable de los controles;
- evidencia que un usuario carga para un `METOD`;
- contexto global del modelo compartido por todos los `METOD` del usuario;
- un glosario administrado centralmente;
- Azure OpenAI para embeddings y generacion multimodal.

El primer frontend es un Databricks Notebook. Streamlit queda como una etapa posterior y debe reutilizar el mismo paquete `metod_observations/`.

La salida oficial es una observacion consolidada por **prueba**, no una observacion por control. Cada prueba puede contener varios controles, que el modelo evalua internamente en una unica llamada.

## 2. Decisiones funcionales vigentes

Estas decisiones ya fueron discutidas y no deben cambiarse sin una nueva indicacion del usuario:

1. Cada hoja del Excel representa un `METOD`, por ejemplo `BBDD1`.
2. `Detalle_prueba` representa el nombre de una prueba.
3. Cuando `Detalle_prueba` viene vacio en las filas siguientes, se hereda el ultimo valor no vacio.
4. Cada fila con contenido dentro de una prueba representa un control.
5. Las columnas obligatorias son:
   - `Detalle_prueba`
   - `Detalle`
   - `Prompt`
   - `Limites`
   - `Criticidad`
   - `Excepciones`
6. Los identificadores se generan por orden de aparicion:
   - `metod_id`: `BBDD1`
   - `prueba_id`: `BBDD1_P01`
   - `control_id`: `BBDD1_P01_C01`
7. Se genera un Markdown por prueba, con sus controles como secciones internas.
8. Se realiza una llamada LLM por prueba, no una llamada por control.
9. La evidencia se carga por `METOD`; el usuario no crea carpetas por prueba o por control.
10. El sistema recupera del pool del `METOD` la evidencia semanticamente relevante para cada prueba.
11. El usuario puede cargar contexto compartido en `inputs/_global/`, por ejemplo:
    - un `.sas` que define target, `CODMES` y variables explicativas;
    - un `.txt` con contexto general del modelo.
12. El contexto global ayuda a interpretar la evidencia, pero no demuestra por si mismo que un control se cumple o incumple.
13. La criticidad final solo puede ser:
    - `Critico`
    - `Relevante`
    - `Moderado`
    - `Baja`
    - `Potencial`
14. Si no existe sustento suficiente:
    - `hay_observacion` debe ser `false`;
    - `criticidad` debe ser `null`;
    - `observacion` debe ser una cadena vacia;
    - `informacion_faltante` puede explicar que falta.

## 3. Separacion admin/usuario

### Admin

El admin es la unica persona que modifica:

- el Excel maestro;
- los Markdown generados de pruebas;
- los `manifest.json`;
- `knowledge/_shared/glossary_data.json`;
- los embeddings estables de perfiles de prueba;
- los embeddings estables del glosario;
- deployments, razonamiento, retrieval, chunking y limites de imagenes en `.env`.

### Usuario final

El usuario solamente:

1. indica su carpeta base;
2. selecciona el `METOD`;
3. coloca evidencia en `inputs/<METOD>/`;
4. opcionalmente coloca contexto compartido en `inputs/_global/`;
5. ejecuta el notebook;
6. revisa los resultados.

No debe ver widgets de providers, deployments, top-k, glosario, reconstruccion de indices, razonamiento, cantidad de imagenes ni seleccion de pruebas individuales.

## 4. Limite exacto del RAG

El sistema es hibrido. No todo pasa por RAG.

### Lookup deterministico

Se lee directamente desde el Markdown y el manifest de la prueba:

- detalle de cada control;
- prompt del control;
- limites;
- criticidad configurada;
- excepciones;
- lista de controles esperados.

No tiene sentido recuperar semanticamente estas reglas porque el sistema ya conoce exactamente que prueba esta evaluando.

### RAG principal

Se usa sobre la evidencia subida por el usuario para encontrar que fragmentos aplican a cada prueba.

### RAG de contexto global

Se usa sobre `inputs/_global/` para recuperar configuracion y contexto compartido relevante para cada prueba.

### RAG auxiliar de glosario

Se recuperan terminos por coincidencia de terminos/aliases y por similitud semantica.

### Perfil de prueba

El admin genera un embedding estable por prueba a partir de su nombre y sus controles. Ese vector se reutiliza como consulta contra:

- evidencia del `METOD`;
- contexto global;
- glosario.

Esto evita volver a generar un embedding de consulta por cada prueba en cada ejecucion de usuario.

## 5. Arquitectura vigente

```text
Excel maestro administrado
        |
        v
notebooks/01_admin_build_knowledge.py
        |
        +--> Markdown por prueba
        +--> manifest.json por METOD
        +--> embeddings de perfiles por METOD
        +--> embeddings compartidos del glosario

Evidencia del usuario por METOD ----+
Contexto del usuario en _global ----+--> parseo / chunks / embeddings cacheados
                                     |
Perfil admin de cada prueba ---------+--> cosine similarity local
                                     |
                                     +--> top evidence
                                     +--> top global context
                                     +--> glossary relevante
                                     |
                                     v
Azure OpenAI Responses API
GPT-5.4 + reasoning high + imagenes base64 + JSON Schema
                                     |
                                     v
JSON + Markdown + retrieval debug por ejecucion
```

No se usa LangChain, una base vectorial externa, Delta ni una jerarquia compleja de clases. El retrieval local lee JSONL y calcula cosine similarity en Python.

## 6. Modelo y proveedor vigentes

El flujo productivo actual utiliza solamente **Azure OpenAI**.

- Generacion: deployment GPT-5.4 configurado en `.env`.
- Valor comunicado para el deployment GPT-5.4: `OAIXXX05`.
- Razonamiento: `reasoning={"effort": "high"}`.
- API: `OpenAI(...).responses.create(...)` contra Azure OpenAI v1.
- Multimodalidad: un mismo mensaje contiene `input_text` y cero o mas `input_image`.
- Imagenes: se envian como data URL base64.
- Salida: Structured Outputs mediante un JSON Schema estricto.
- Embeddings: deployment Azure configurado por `DEPLOYMENT_EMB_SMALL` o `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.

Claude y Databricks Model Serving ya no forman parte del flujo productivo. No reintroducir `mlflow.deployments`, providers seleccionables ni widgets de endpoints en los notebooks productivos.

La carpeta `chunking_experiment/` conserva comparaciones historicas con otros providers. Es material experimental aislado y no debe usarse como referencia del runtime actual.

## 7. Configuracion `.env`

`.env` esta ignorado por Git. En un dispositivo nuevo debe crearse manualmente a partir de `.env.example`, sin incluir secretos en commits.

Configuracion esperada:

```env
AZURE_OPENAI_API_KEY=<secreto>
AZURE_OPENAI_ENDPOINT=https://<recurso>.openai.azure.com/

DEPLOYMENT_AZURE=OAIXXX05
DEPLOYMENT_EMB_SMALL=<deployment-de-embeddings>

SOFTIA_KNOWLEDGE_BASE_DIR=/dbfs/FileStore/softia_mvp/knowledge
SOFTIA_WORKSPACE_BASE_DIR=/Workspace/Users/<usuario>/softia_mvp
SOFTIA_CODE_PATH=/Workspace/Users/<admin>/gestor_observaciones

SOFTIA_REASONING_EFFORT=high
SOFTIA_TOP_K_EVIDENCE=8
SOFTIA_TOP_K_GLOBAL_CONTEXT=4
SOFTIA_TOP_K_GLOSSARY=5
SOFTIA_MAX_PROMPT_IMAGES=2
SOFTIA_CHUNK_SIZE=1800
SOFTIA_CHUNK_OVERLAP=200
```

Compatibilidad de nombres:

- chat: primero `AZURE_OPENAI_CHAT_DEPLOYMENT`, luego `DEPLOYMENT_GPT54`, luego `DEPLOYMENT_AZURE`;
- embeddings: primero `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, luego `DEPLOYMENT_EMB_SMALL`.

`AZURE_OPENAI_API_VERSION` puede seguir existiendo en el `.env`, pero el cliente v1 implementado no lo consume.

Los notebooks y `load_config()` ejecutan:

```python
load_dotenv(".env", override=True)
truststore.inject_into_ssl()
```

`truststore` es necesario en el entorno corporativo para que el cliente use correctamente el almacen de certificados del sistema.

### Efecto de los parametros internos

| Variable | Efecto |
|---|---|
| `SOFTIA_REASONING_EFFORT` | Mayor razonamiento puede mejorar analisis, pero aumenta latencia y consumo. Actualmente `high`. |
| `SOFTIA_TOP_K_EVIDENCE` | Cantidad maxima de chunks de evidencia enviados por prueba. Mas alto aumenta contexto y costo, y puede agregar ruido. |
| `SOFTIA_TOP_K_GLOBAL_CONTEXT` | Cantidad de chunks globales enviados por prueba. |
| `SOFTIA_TOP_K_GLOSSARY` | Cantidad maxima de terminos recuperados. |
| `SOFTIA_MAX_PROMPT_IMAGES` | Cantidad maxima de imagenes reales adjuntadas por prueba. |
| `SOFTIA_CHUNK_SIZE` | Tamano de cada chunk en caracteres. |
| `SOFTIA_CHUNK_OVERLAP` | Solapamiento en caracteres entre chunks consecutivos. |

## 8. Rutas de Databricks

### Zona administrada en FileStore

```text
/dbfs/FileStore/softia_mvp/knowledge/
  _shared/
    glossary_data.json
  _indexes/
    _shared/
      glossary_embeddings.jsonl
    BBDD1/
      prueba_profile_embeddings.jsonl
  BBDD1/
    manifest.json
    pruebas/
      BBDD1_P01_<slug>.md
      BBDD1_P02_<slug>.md
```

Los embeddings estables pertenecen a FileStore porque son comunes a todos los usuarios y solo cambian cuando cambia el Excel, el glosario o el deployment de embeddings.

### Zona de cada usuario

```text
/Workspace/Users/<usuario>/softia_mvp/
  inputs/
    _global/
      configuracion_variables.sas
      contexto_modelo.txt
    BBDD1/
      <evidencias del usuario>
  indexes/
    _global/
      global_context_embeddings.jsonl
    BBDD1/
      evidence_chunks_embeddings.jsonl
  outputs/
    generated_observations/
      BBDD1_run_YYYYMMDD_HHMMSS.json
      BBDD1_run_YYYYMMDD_HHMMSS.md
      retrieval_debug_BBDD1_run_YYYYMMDD_HHMMSS.jsonl
```

El notebook del usuario puede estar en otra carpeta. El paquete compartido debe seguir siendo importable mediante `SOFTIA_CODE_PATH`.

## 9. Flujo admin

Entrada principal: `notebooks/01_admin_build_knowledge.py`.

Widgets del admin:

- `excel_path`: ruta del Excel maestro;
- `sheet_name`: hoja opcional; vacio procesa todas;
- `rebuild_embeddings`: fuerza reconstruccion si es `true`;
- `knowledge_base_dir`: destino administrado en FileStore.

Proceso:

1. Carga `.env` e inyecta `truststore`.
2. Lee el Excel con `openpyxl`.
3. Valida las columnas obligatorias de cada hoja.
4. Aplica el forward-fill logico de `Detalle_prueba`.
5. Agrupa filas en pruebas y controles.
6. Genera IDs segun el orden encontrado.
7. Escribe un Markdown por prueba.
8. Escribe un `manifest.json` por `METOD`.
9. Genera o reutiliza embeddings del glosario.
10. Genera o reutiliza embeddings de perfiles de prueba.
11. Guarda todos los embeddings administrados bajo `knowledge/_indexes/`.

El cache compara `id`, hash del texto y nombre del deployment de embeddings. `rebuild_embeddings=false` es el uso normal. Debe reconstruirse cuando cambie el deployment.

El Excel mencionado durante el desarrollo fue:

```text
C:\Users\User\Desktop\score_tradicional_y_ml.xlsx
```

Ese archivo no esta versionado en este repositorio y debe transferirse por separado si se necesita en el nuevo dispositivo.

## 10. Flujo usuario

Entrada principal: `notebooks/02_generate_observations_by_prueba.py`.

Widgets visibles:

- `metod_id`, por defecto `BBDD1`;
- `user_base_dir`, carpeta raiz del usuario.

El notebook deriva todas las demas rutas. No existe `run_mode` ni selector de prueba individual. Siempre procesa todas las pruebas del `METOD` seleccionado.

Proceso:

1. Carga `.env` e inyecta `truststore`.
2. Verifica que exista el manifest administrado.
3. Verifica que existan los indices admin de glosario y perfiles.
4. Verifica que el deployment que genero esos indices coincida con el deployment actual.
5. Descubre y parsea evidencia recursivamente en `inputs/<METOD>/`.
6. Descubre y parsea contexto recursivamente en `inputs/_global/`.
7. Genera chunks y reutiliza embeddings por hash cuando no hubo cambios.
8. Para cada prueba, reutiliza el embedding de su perfil como query.
9. Recupera evidencia, contexto global y glosario.
10. Convierte como maximo `SOFTIA_MAX_PROMPT_IMAGES` imagenes recuperadas a base64.
11. Construye el prompt con el Markdown completo de la prueba.
12. Ejecuta una llamada `responses.create` por prueba.
13. Valida la criticidad y los IDs de controles devueltos.
14. Guarda JSON, Markdown y retrieval debug.

## 11. Evidencias soportadas

Extensiones actuales:

```text
.txt .md .py .sql .sas .csv .xlsx .docx .html .htm .pdf .png .jpg .jpeg
```

Comportamiento relevante:

- TXT/Markdown/codigo: lectura UTF-8 con reemplazo de caracteres invalidos.
- CSV: maximo 1000 filas por archivo.
- XLSX de evidencia: maximo 300 filas por hoja.
- DOCX: extrae parrafos y tablas.
- HTML: usa BeautifulSoup si esta disponible.
- PDF: extrae texto pagina por pagina con `pypdf`.
- Imagenes: se registran como chunks y, si son recuperadas, se adjuntan realmente al request multimodal en base64.
- El descubrimiento de archivos es recursivo.

No existe OCR para PDFs escaneados ni embeddings visuales. La recuperacion inicial de una imagen se basa actualmente en un texto generico con su nombre de archivo; la lectura visual ocurre despues, cuando una imagen recuperada es adjuntada al modelo.

## 12. Prompt y salida estructurada

Cada request contiene:

- `METOD`, `prueba_id` y nombre de prueba;
- IDs de todos los controles esperados;
- Markdown completo de la prueba;
- glosario recuperado;
- contexto global recuperado;
- evidencia recuperada con archivo, chunk, score, extracto y metadata;
- nombres de imagenes adjuntas;
- data URLs base64 como `input_image`.

El JSON Schema exige:

```json
{
  "prueba_id": "BBDD1_P01",
  "nombre_prueba": "Nombre de la prueba",
  "hay_observacion": true,
  "criticidad": "Moderado",
  "observacion": "...",
  "sustento": "...",
  "controles_evaluados": ["BBDD1_P01_C01"],
  "controles_que_originan_observacion": ["BBDD1_P01_C01"],
  "evidencias_usadas": [
    {
      "archivo": "evidencia.sql",
      "chunk_id": "BBDD1_E0001_C001",
      "score": 0.82
    }
  ],
  "informacion_faltante": []
}
```

Ademas del schema de la API, `validate_observation_payload()` aplica validacion defensiva:

- fuerza la criticidad a `null` cuando no hay observacion;
- limpia el texto de observacion cuando no hay hallazgo;
- rechaza criticidades fuera del enum;
- elimina IDs de controles que no pertenecen a la prueba;
- completa `controles_evaluados` con todos los controles si el modelo no los entrega.

## 13. Modulos productivos

| Archivo | Responsabilidad |
|---|---|
| `metod_observations/config.py` | Configuracion, `.env`, `truststore` y resolucion de rutas. |
| `metod_observations/schemas.py` | Dataclasses, enum de criticidad y JSON Schema. |
| `metod_observations/excel_loader.py` | Lectura, validacion y normalizacion del Excel. |
| `metod_observations/knowledge_builder.py` | Markdown, manifest y texto de perfil de pruebas. |
| `metod_observations/parsers.py` | Extraccion de texto y registro de imagenes. |
| `metod_observations/chunking.py` | Chunking por caracteres con overlap y metadata. |
| `metod_observations/embeddings.py` | Cliente Azure OpenAI, Responses API y cache de embeddings. |
| `metod_observations/retrieval.py` | Cosine similarity y top-k local. |
| `metod_observations/prompt_builder.py` | Prompt consolidado por prueba. |
| `metod_observations/observation_generator.py` | Parseo y validacion defensiva de la respuesta. |
| `metod_observations/outputs.py` | Escritura de JSON, Markdown y JSONL debug. |
| `metod_observations/pipeline.py` | Orquestacion admin y usuario. |
| `notebooks/01_admin_build_knowledge.py` | Interfaz Databricks del admin. |
| `notebooks/02_generate_observations_by_prueba.py` | Interfaz Databricks del usuario final. |

## 14. Uso de POO

La decision actual es no usar POO pesada.

- Se usan `dataclass` para contratos de datos estables.
- Existe una sola clase ligera, `ModelClient`, para encapsular el cliente Azure OpenAI.
- El resto son funciones pequenas y modulares.
- No crear jerarquias de providers, retrievers o pipelines salvo que aparezca una necesidad real nueva.

Esto mantiene el codigo legible en notebooks y facilita una futura interfaz Streamlit.

## 15. Archivos historicos y experimentales

No confundir estos artefactos con el nucleo productivo:

- `chunking_experiment/`: benchmark de chunking y comparacion historica de providers.
- `metod_rag_observation_generator.py`: MVP monolitico anterior.
- `project_doc.md`: documentacion de una etapa anterior del MVP.
- `seed_metod_test_files.py`: fixtures del prototipo anterior.
- `base64toimage/`: utilidad/experimento de conversion de imagenes.
- `experiment/` y `test.ipynb`: notebooks exploratorios.
- `tests/`: pruebas creadas anteriormente, pero no forman parte del flujo operativo solicitado actualmente.
- `knowledge/METOD5/*.md`: conocimiento del experimento anterior, no el layout generado por el Excel de produccion.

Para cambios nuevos, empezar por `metod_observations/` y los dos notebooks numerados.

## 16. Estado actual real

### Implementado

- paquete modular compatible con Databricks;
- lectura del Excel y agrupacion por prueba;
- Markdown por prueba y manifest por `METOD`;
- indices admin estables de perfiles y glosario;
- evidencia por carpeta de `METOD`;
- contexto global en `inputs/_global/`;
- parsers de formatos comunes;
- chunking y cache por hash;
- retrieval local por cosine similarity;
- una llamada LLM por prueba;
- Azure OpenAI Responses API;
- GPT-5.4 configurable por `.env`;
- razonamiento `high`;
- imagenes reales adjuntadas como base64;
- Structured Outputs con JSON Schema;
- JSON, Markdown y retrieval debug;
- notebook del usuario reducido a dos widgets.

### Validado hasta ahora

- sintaxis de los modulos modificados;
- imports locales;
- ausencia de referencias a Claude, Databricks Model Serving y `mlflow.deployments` en el flujo productivo;
- worktree limpio en el commit indicado.

### No validado todavia

- ejecucion end-to-end real en un cluster Databricks;
- llamada real al deployment GPT-5.4 `OAIXXX05`;
- compatibilidad real del deployment de embeddings configurado;
- escritura real en `/dbfs/FileStore/softia_mvp/knowledge`;
- procesamiento del Excel maestro completo en el nuevo flujo;
- calidad del retrieval para todos los `METOD`;
- costo, latencia y limites de rate del volumen completo;
- futura interfaz Streamlit.

El usuario pidio explicitamente evitar crear o ejecutar tests. La siguiente validacion debe ser un smoke run controlado en Databricks, no una ampliacion automatica del test suite.

## 17. Riesgos y pendientes conocidos

Prioridad alta:

1. Ejecutar el notebook admin con el Excel real y revisar manifests, Markdown e indices generados.
2. Ejecutar una prueba end-to-end pequena en Databricks con un `METOD` y evidencia conocida.
3. Confirmar que el deployment GPT-5.4 acepta Responses API, `reasoning=high`, imagenes y el JSON Schema actual.
4. Validar programaticamente que `evidencias_usadas` solo contenga chunks realmente recuperados. Hoy el schema valida la forma, pero no cruza esos IDs contra el conjunto enviado al modelo.
5. Validar tambien la criticidad proveniente del Excel. Actualmente el enum se aplica a la salida del modelo, pero el loader no rechaza valores administrativos fuera del enum.

Prioridad media:

1. Definir un score minimo de retrieval. Actualmente siempre se toman los mejores `top_k`, aunque todos tengan baja similitud; el prompt indica no usarlos si no sustentan el hallazgo.
2. Incorporar OCR para PDFs escaneados si aparecen en evidencia real.
3. Mejorar la recuperacion inicial de imagenes con captions u otro indice multimodal. Actualmente se recuperan por el texto generico asociado al nombre del archivo.
4. Agregar reintentos controlados para errores transitorios y rate limits de Azure OpenAI.
5. Registrar tokens/uso real devuelto por Responses API para estimar costo, no solo cantidad de requests y embeddings.
6. Decidir donde residira `.env` cuando el notebook del usuario este en una carpeta externa. `load_dotenv(".env")` depende del directorio de trabajo actual; en produccion puede convenir una variable de cluster o una ruta administrada.

Detalles a vigilar:

- reordenar pruebas en el Excel cambia `P01`, `P02`, etc.; los IDs no son independientes del orden;
- eliminar una prueba del Excel la retira del manifest y del indice, pero puede dejar un Markdown huerfano en `pruebas/`;
- PDFs de imagen no producen texto util sin OCR;
- el texto interno de `parse_image_file()` todavia menciona que vision seria una etapa posterior, aunque la etapa multimodal ya esta implementada;
- el contexto global se excluye de `evidencias_usadas` mediante el prompt, pero todavia no mediante una validacion programatica posterior;
- el run ID usa precision de segundos, por lo que dos ejecuciones simultaneas del mismo `METOD` podrian colisionar.

## 18. Como retomar en otro dispositivo

1. Clonar o copiar el repositorio y comprobar `main`/`d970c54` o un commit posterior que incluya este documento.
2. Copiar por separado el Excel maestro y cualquier evidencia que no este en Git.
3. Crear `.env` desde `.env.example` con credenciales y deployments reales.
4. No copiar ningun secreto dentro de este Markdown ni al repositorio.
5. Subir o sincronizar el codigo en Databricks Workspace Files.
6. Ajustar `SOFTIA_CODE_PATH` para que los notebooks importen `metod_observations`.
7. Confirmar donde se resolvera `.env` en Databricks.
8. Ejecutar primero `notebooks/01_admin_build_knowledge.py`.
9. Revisar en FileStore:
   - Markdown por prueba;
   - `manifest.json`;
   - embeddings de perfiles;
   - embeddings del glosario.
10. Crear para un usuario:
    - `inputs/<METOD>/`;
    - `inputs/_global/` si aplica.
11. Ejecutar `notebooks/02_generate_observations_by_prueba.py`.
12. Revisar el JSON final, el Markdown y especialmente `retrieval_debug_*.jsonl`.
13. Antes de ampliar funcionalidad, resolver los pendientes de prioridad alta.

## 19. Instrucciones para el siguiente Codex

- Leer primero este archivo y despues inspeccionar el checkout actual.
- Tratar el codigo como la fuente de verdad si difiere de este documento.
- Mantener el proyecto ejecutable en Databricks.
- Mantener el notebook del usuario simple: solamente carpeta y `METOD`.
- Mantener configuracion tecnica y modelos bajo control del admin.
- No reintroducir Claude ni Databricks Model Serving en produccion.
- No convertir las reglas del Excel en un RAG innecesario.
- Mantener una llamada LLM por prueba.
- Conservar trazabilidad de controles y evidencias.
- Enviar imagenes reales al prompt cuando sean recuperadas, respetando el limite.
- Evitar LangChain, vector DB externa y abstracciones que no aporten al MVP.
- No crear tests salvo que el usuario cambie explicitamente esa instruccion.
- Antes de editar, revisar `git status`; no revertir cambios ajenos.
- Al reportar avances, diferenciar claramente entre implementado, validado y pendiente.

## 20. Definicion de terminado para el MVP productivo

El MVP puede considerarse operativo cuando:

1. el admin procesa el Excel real sin errores;
2. FileStore contiene conocimiento e indices consistentes;
3. un usuario carga evidencia por `METOD` y contexto global opcional;
4. el pipeline procesa todas las pruebas del `METOD`;
5. GPT-5.4 devuelve una salida valida por prueba;
6. las observaciones citan solo evidencia recuperada real;
7. los casos sin evidencia suficiente no inventan hallazgos;
8. las imagenes relevantes llegan efectivamente al request multimodal;
9. el debug permite auditar retrieval y archivos utilizados;
10. costos y latencia son aceptables para el numero real de pruebas.

