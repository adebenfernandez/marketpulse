# Registro de decisiones técnicas

Cada decisión importante, con su contexto, las opciones, la decisión y el motivo.
Formato inspirado en los ADR (*Architecture Decision Records*).

---

## D-001 · Seguir con la "nueva experiencia de AWS" y el plan gratuito
**Fecha:** 2026-10-19 · **Fase:** 0

**Contexto:** la cuenta se creó con *Sign up for AWS (new)*. En esta modalidad se entra con AWS Builder ID, no hay usuarios IAM con consola, ni IAM Identity Center ni AWS Organizations, y AWS aplica SCP propias. La cuenta tiene el plan gratuito, con 100 USD de créditos durante 183 días.

**Opciones:**
1. Quedarse en la nueva experiencia y el plan gratuito.
2. Activar las "funciones avanzadas", que dan Identity Center, el resto de regiones y todos los servicios. Exige el plan de pago y es irreversible.

**Decisión:** opción 1.

**Motivo:** todos los servicios del proyecto (S3, Lambda, EventBridge, CloudWatch, SNS, Glue, Athena, Systems Manager, Budgets e IAM) están incluidos en el plan gratuito de esta modalidad. El proyecto no le cuesta dinero a Alberto y la decisión no cierra puertas: siempre se puede activar más adelante.

**Consecuencias:** el plan gratuito termina a los 6 meses (hacia abril de 2027); antes de esa fecha habrá que decidir si se pasa al plan de pago o se destruye la infraestructura con Terraform. Hay que vigilar las SCP gestionadas (ver D-003 y los riesgos abiertos en `PROGRESS.md`).

Fuentes: [Sign up for AWS (new)](https://docs.aws.amazon.com/accounts/latest/reference/sign-in-new.html) · [Supported services](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html) · [Activate advanced features](https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.html)

---

## D-002 · Región `eu-north-1` (Estocolmo) en lugar de `eu-west-1` (Irlanda)
**Fecha:** 2026-10-19 · **Fase:** 0

**Contexto:** el informe proponía `eu-west-1`. En la nueva experiencia, la región la asigna AWS según el país del contacto y no se puede cambiar: a España le corresponde `eu-north-1`.

**Opciones:** aceptar `eu-north-1` o activar las funciones avanzadas para elegir región (ver D-001).

**Decisión:** `eu-north-1`.

**Motivo:** tiene todos los servicios del proyecto y está en Europa (los datos no salen de la UE). Es una restricción real de la plataforma a la que el proyecto se adapta.

Fuente: [AWS Regions for your projects](https://docs.aws.amazon.com/accounts/latest/reference/project-regions.html)

---

## D-003 · Identidad de trabajo: Builder ID con MFA y `aws login`
**Fecha:** 2026-10-19 · **Fase:** 0

**Contexto:** el informe pedía un usuario administrador con Identity Center (o un usuario IAM con MFA). En la nueva experiencia no se pueden crear usuarios IAM con acceso a la consola, e Identity Center no está disponible.

**Decisión:** trabajar con el Builder ID del propietario, protegido con MFA (TOTP). En la terminal se usa `aws login --profile marketpulse`, que da credenciales temporales de 12 h al asumir el rol `AccountFullAccessRole`. **No se crean claves de acceso permanentes.**

**Motivo:** cumple el objetivo del paso, que era no trabajar con una identidad todopoderosa ni con credenciales permanentes. Coincide con la buena práctica de AWS: personas con identidad federada y credenciales temporales.

---

## D-004 · Alertas del presupuesto a través de un tema de SNS
**Fecha:** 2026-10-20 · **Fase:** 0

**Contexto:** el presupuesto `marketpulse-mensual` (5 USD, excluye créditos, umbrales reales del 50/80/100 %) no podía verificar el email del destinatario. La SCP de la nueva experiencia (`DenyNotificationContactsOperations`) deniega `notifications-contacts:*` a todos los usuarios, incluido el propietario.

**Opciones:**
1. Dejar el presupuesto sin alertas y revisarlo a mano.
2. Enviar las alertas a un tema de SNS con una suscripción por email.

**Decisión:** opción 2. Tema estándar `marketpulse-alertas` en `eu-north-1`, sin cifrado y con la etiqueta `project=marketpulse`. Su política de recurso permite **solo** a `budgets.amazonaws.com` hacer `SNS:Publish` en ese tema, con las condiciones `aws:SourceAccount` y `aws:SourceArn` (presupuestos de esta cuenta), para evitar el *confused deputy*.

**Motivo:** SNS está permitido por la SCP y por el informe ("SNS, solo emails de alerta"), y su confirmación de email no depende del servicio bloqueado. El mismo tema servirá para las alarmas de CloudWatch de la Fase 3.

**Por qué sin cifrado:** los mensajes solo contienen importes de gasto (no son datos sensibles), y cifrarlo con KMS obligaría a dar permisos extra a Budgets sobre la clave.

Fuente: [Managed policies for your organization](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html)

---

## D-005 · El presupuesto excluye los créditos
**Fecha:** 2026-10-20 · **Fase:** 0

**Contexto:** con el plan gratuito, los créditos pagan todo el consumo. Si el presupuesto los restara, el coste sería siempre de unos 0 USD y las alertas no saltarían nunca. La documentación no deja claro el comportamiento por defecto.

**Decisión:** filtro explícito en el ámbito: "Tipo de cargos, excluye Credit". Costes agregados como "sin combinar".

**Motivo:** queremos vigilar lo que costaría de verdad el consumo, independientemente de quién lo pague.

---

## D-006 · El proyecto sigue en OneDrive, pero el entorno virtual va fuera
**Fecha:** 2026-10-19 / 2026-10-20 · **Fase:** 0

**Contexto:** la carpeta del proyecto está dentro de OneDrive, y Alberto prefiere no moverla. OneDrive sincroniza con la nube de Microsoft todo lo que hay dentro.

**Decisión:**
- El proyecto se queda en OneDrive.
- El entorno virtual se crea **fuera**, en `C:\Users\deben\.venvs\marketpulse`, para que OneDrive no intente subir miles de ficheros ni los bloquee mientras se usan.
- Las credenciales de AWS ya están fuera del proyecto (`C:\Users\deben\.aws\`).

**Riesgo aceptado:** `.env` (con la clave de Anthropic, a partir de la Fase 7) y el *state* local de Terraform se sincronizarán con OneDrive. Mitigaciones: el *state* irá a un *backend* remoto en S3 en la Fase 5, y la clave de Anthropic tendrá un límite de gasto en la consola de Anthropic.

---

## D-007 · `INFORME_PROYECTO.pdf` no se sube al repositorio
**Fecha:** 2026-10-20 · **Fase:** 0

**Contexto:** el repositorio `marketpulse` en GitHub es privado, pero se hará público en la Fase 8. El PDF contiene datos personales y las instrucciones originales para Claude Code.

**Decisión:** añadirlo a `.gitignore`. El resumen de las reglas vive en `CLAUDE.md`.

**Motivo:** un fichero que entra en el historial de Git es muy difícil de eliminar después. Es más fácil no subirlo nunca.

---

## D-008 · Dependencias de la ingesta: `requests`, `PyYAML` y `python-dotenv`
**Fecha:** 2026-10-20 · **Fase:** 1

**Contexto:** la Fase 1 necesita hacer llamadas HTTP, leer un fichero YAML y cargar claves de API desde `.env`.

**Opciones:**
- HTTP: `urllib` (librería estándar, sin dependencias, pero incómoda), `httpx` (moderna, con modo asíncrono que no necesitamos) o `requests` (la más usada y la más fácil de leer).
- YAML: Python no trae lector de YAML; `PyYAML` es el estándar de facto.
- `.env`: leer el fichero a mano o usar `python-dotenv`.
- Mocks en los tests: `unittest.mock` (incluido en Python) frente a librerías como `responses`.

**Decisión:** `requests`, `PyYAML` y `python-dotenv`, aprobadas por Alberto. Los mocks se hacen con `unittest.mock`, sin dependencia extra.

**Motivo:** son librerías maduras y muy conocidas, y el código queda sencillo de leer. En Lambda (Fase 3) habrá que empaquetarlas; `python-dotenv` solo se usa en local, porque en AWS las claves vendrán de SSM Parameter Store.

---

## D-009 · Bronze: respuesta original, un fichero por fuente/día/nombre, sobrescritura atómica y fecha UTC
**Fecha:** 2026-10-20 · **Fase:** 1

**Contexto:** la ingesta debe guardar la respuesta original de cada API y, si se ejecuta dos veces el mismo día, no duplicar datos.

**Opciones:**
- Nombre del fichero con la hora de ejecución (`frankfurter_0612.json`): nunca se pierde nada, pero se duplican datos y la limpieza pasa a silver.
- Nombre determinista (`source=.../dt=.../<nombre>.json`) y sobrescribir: idempotente por construcción.
- Envolver la respuesta con metadatos (`{"ingested_at": ..., "payload": ...}`) frente a guardarla tal cual.

**Decisión:** nombre determinista con sobrescritura **atómica** (temporal y después `os.replace`); la respuesta se guarda **tal cual**, sin envoltorio; la fecha de partición `dt` es la fecha de ejecución en **UTC**. Los nombres se validan con `[A-Za-z0-9_-]` para evitar *path traversal*.

**Motivo:** cumple el criterio de aceptación sin lógica de deduplicación; bronze es la copia fiel de la fuente (si silver tiene un error, se puede rehacer desde aquí); UTC hace que el portátil y Lambda generen la misma partición. Contrapartida aceptada: una segunda ejecución del mismo día sustituye a la primera (se queda el dato más reciente).

---

## D-010 · Frankfurter: API v2 y solo el proveedor BCE
**Fecha:** 2026-10-20 · **Fase:** 1

**Contexto:** al consultar la documentación oficial (frankfurter.dev, 2026-10-20) se ve que la API v1 está **obsoleta** (sigue disponible) y que la v2 combina por defecto los datos de unos 100 bancos centrales. El informe pide los tipos de referencia del BCE.

**Opciones:** v1 (`/v1/latest`, la que aparece en muchos tutoriales) · v2 sin filtro (media de varios bancos) · v2 con `providers=ECB`.

**Comprobación real:** `GET /v2/rates?base=EUR&quotes=USD,GBP` → USD 1,1226 (media) frente a `...&providers=ECB` → USD 1,1215 (BCE). No son el mismo dato.

**Decisión:** v2 con `providers=ECB`. La respuesta es una lista de filas `{date, base, quote, rate}`.

**Motivo:** la v2 es la versión mantenida; el BCE es la fuente oficial que pide el informe y su origen es trazable. Condiciones del BCE: uso libre, citando al BCE como fuente e indicando cualquier transformación de los datos (se citará en el README). Sin clave de API; la documentación habla de "sin cuotas", con un límite de peticiones contra el abuso (hacemos 1 al día).

---

## D-011 · CoinGecko: `/simple/price` con clave Demo opcional en cabecera
**Fecha:** 2026-10-20 · **Fase:** 1

**Contexto:** documentación oficial (docs.coingecko.com y la página de precios, 2026-10-20): existe un acceso **sin clave** con un límite por IP compartido entre todos los usuarios de esa IP, y un plan **Demo** gratuito (sin tarjeta) con 100 llamadas/min y 10.000/mes. La clave Demo va en la cabecera `x-cg-demo-api-key` o en el parámetro `x_cg_demo_api_key`. El plan gratuito exige **atribución** a CoinGecko.

**Opciones:** solo sin clave · exigir siempre la clave · clave **opcional** · clave en la URL o en una cabecera.

**Decisión:** endpoint `/simple/price` (una llamada para todas las monedas, con capitalización, volumen, variación 24 h y `last_updated_at`); clave **opcional** leída de `COINGECKO_API_KEY`, y siempre en **cabecera**.

**Motivo:** en local funciona sin registrarse (comprobado: 200 sin clave). En Lambda las IP de AWS se comparten, así que antes de la Fase 3 Alberto creará la clave Demo y se guardará en SSM Parameter Store. La cabecera evita que la clave aparezca en URLs y logs, como recomienda la propia documentación. Uso: 1 llamada/día ≈ 30/mes, muy por debajo del límite. **Pendiente:** fijar el texto exacto de la atribución antes de mostrar datos (Fase 8, dashboard y README).

---

## D-012 · Alpha Vantage: `TIME_SERIES_DAILY` compacta, un fichero por símbolo y fallo parcial
**Fecha:** 2026-10-20 · **Fase:** 1

**Contexto:** documentación oficial (2026-10-20): clave gratuita obligatoria, 25 peticiones/día; `TIME_SERIES_DAILY_ADJUSTED` es *premium*; con `TIME_SERIES_DAILY`, `outputsize=full` también es *premium* y `compact` devuelve los últimos 100 días. La clave se pasa en la URL (`apikey`). Los errores llegan como **200** con un campo `Information`, `Note` o `Error Message` (comprobado con la clave `demo`). Términos de uso: uso personal y no comercial.

**Opciones:** `GLOBAL_QUOTE` (solo el último día) · `TIME_SERIES_DAILY` compacta · la serie ajustada (de pago). Si falla un símbolo: parar todo · ignorarlo en silencio · seguir y avisar al final.

**Decisión:** `TIME_SERIES_DAILY` con `compact` (1 petición por símbolo: 3/día de 25), un fichero por símbolo (`source=alphavantage/dt=.../SPY.json`), los 200 con aviso se tratan como error y, si falla un símbolo, se guardan los demás y se lanza `PartialIngestError`. Sin clave no se hace ninguna llamada (`MissingApiKeyError`).

**Motivo:** la serie diaria trae OHLCV, y los 100 días rellenan huecos sin coste extra. Contrapartida: los precios **no están ajustados** por dividendos ni *splits* (en ETF el efecto es pequeño, pero queda anotado como limitación para la Fase 4). La clave en la URL la impone la API: `HttpClient` la oculta en los logs y el texto de los avisos se limpia de la clave.

**Actualización (2026-10-20, primera ejecución real):** SPY se guardó, pero VT y QQQ, pedidos 133 ms después, recibieron un 200 con `Information: ... spreading out your free API requests more sparingly (1 request per second)`. Hay un **límite de ráfaga** de 1 petición por segundo que la página de soporte no menciona. Solución: pausa de `REQUEST_INTERVAL = 1,5 s` entre símbolos (*throttling*), con `sleep` inyectado para que los tests no esperen. El fallo parcial funcionó como se diseñó: se guardó SPY, sin basura para VT ni QQQ, y se lanzó `PartialIngestError` con el motivo.

---

## D-013 · Orquestador: todas las fuentes se ejecutan siempre y el código de salida resume el resultado
**Fecha:** 2026-10-20 · **Fase:** 1

**Contexto:** `python -m marketpulse.ingest` tiene que lanzar las tres fuentes. Hay que decidir qué pasa si una falla y cómo se entera quien lo ejecuta (Alberto, Lambda o GitHub Actions).

**Opciones:** parar en el primer fallo · seguir y devolver siempre 0 · seguir y devolver 1 si algo falló.

**Decisión:**
- Lógica en `ingest/run.py` (`run_all()` y `main()`); `__main__.py` solo llama a `main()`.
- Se ejecutan **todas** las fuentes y se atrapa cualquier excepción por fuente (`logger.exception`, con la traza).
- Al final, un resumen y **código de salida 1** si alguna fuente falló (0 si todas fueron bien).
- `.env` y el logging se configuran solo en `main()`. Las claves se leen de las variables de entorno y se pasan a cada cliente como parámetro.
- Una sola fecha `dt` para todas las fuentes.

**Motivo:** un fallo en una fuente no debe costar los datos de las otras. El código distinto de 0 hace que el fallo sea visible: en la Fase 3 activará la alarma y en la Fase 6 pondrá el *job* en rojo. `run_all()` sin efectos globales la podrá llamar el *handler* de Lambda directamente.

**Mejora de seguridad asociada:** `HttpClient` convierte cualquier otro `requests.RequestException` en `HttpError` sin el mensaje original, que puede contener la URL con la clave, y sin encadenarlo. Así la traza de `logger.exception` no puede filtrar claves.

**Robustez de las claves:** `get_secret()` trata una clave vacía o hecha solo de espacios como inexistente (`None`). Se detectó al probar el código de salida: en PowerShell, `$env:X = ""` borra la variable, y la prueba con `" "` habría llamado a Alpha Vantage con una clave basura, gastando cupo.

---

## D-014 · Primer Terraform: bucket del data lake con *state* local
**Fecha:** 2026-10-20 · **Fase:** 2

**Contexto:** el informe pide crear el bucket con Terraform desde el principio (mini-introducción), y el resto de la infraestructura llegará en la Fase 5.

**Decisión:**
- `infra/` con un fichero por tema: `versions.tf` (Terraform ≥ 1.10 y `hashicorp/aws ~> 6.69`; *lock file* con 6.69.1, que se sube a Git), `providers.tf` (región y `default_tags` `project` y `managed_by`), `variables.tf`, `s3.tf` y `outputs.tf`.
- Bucket con `bucket_prefix = "marketpulse-datalake-"`: nombre único sin el número de cuenta. `force_destroy = false`.
- Las tres protecciones: bloqueo de acceso público (las 4 opciones), cifrado **SSE-S3** (AES256, sin coste) y `BucketOwnerEnforced` (sin ACL).
- **Credenciales fuera del código:** Terraform usa `AWS_PROFILE=marketpulse`, igual que la CLI. Así el mismo código servirá con OIDC en la Fase 6.
- ***State* local** en `infra/terraform.tfstate` (ignorado por Git) hasta la Fase 5, cuando pasará a un *backend* en S3.
- **`TF_DATA_DIR` fuera de OneDrive**, en `C:\Users\deben\.terraform-data\marketpulse` (aprobado por Alberto): el proveedor de AWS ocupa unos 819 MB (medido), por el mismo motivo que D-006.
- `plan -out=tfplan` y `apply tfplan`, para aplicar exactamente lo revisado (`*.tfplan` y `tfplan` añadidos a `.gitignore`).

**Descartado por ahora:** versionado del bucket (duplica el almacenamiento y bronze se puede regenerar), SSE-KMS (coste por clave y por petición) y política de "solo HTTPS" (se propondrá aparte, porque es una política de acceso).

**Actualización (2026-10-20, paso 2.2b):** aprobada por Alberto la política de bucket **"solo HTTPS"** (`aws_s3_bucket_policy` generada con el *data source* `aws_iam_policy_document`): `Deny` de `s3:*` para cualquier principal sobre el bucket y sus objetos cuando `aws:SecureTransport = false`. No concede permisos y no es pública (un `Deny` no abre acceso), así que es compatible con `block_public_policy`. `depends_on` del bloqueo de acceso público para fijar el orden.

---

## D-015 · Silver: tres tablas con esquema explícito, reconstrucción completa y partición por año
**Fecha:** 2026-10-20 · **Fase:** 2

**Contexto:** hay que pasar el JSON original de tres APIs a tablas limpias en Parquet, sin duplicados, aunque cada fuente repite datos de forma distinta (el BCE no publica en fin de semana; Alpha Vantage devuelve 100 días cada día).

**Decisión:**
- **Librerías:** `pandas`, `pyarrow` y `boto3` (aprobadas por Alberto). Versiones mínimas `pandas>=2.2` y `pyarrow>=18`, para no atarnos a pandas 3.0: hay que comprobar qué versiones trae la capa *AWS SDK for pandas* en la Fase 3. En local están instaladas pandas 3.0.6, pyarrow 26.0.0 y boto3 1.43.115.
- **Tres tablas:** `fx_rates`, `crypto_prices` y `stock_prices`, con un **esquema `pyarrow` explícito** (`transform/schemas.py`), forzado al escribir. Precios en `float64` (suficiente para análisis; `decimal` se reservaría para contabilidad). Nombres en *snake_case*.
- **Tiempo:** `price_at` (CoinGecko) es un `timestamp` UTC y su `date` es el día UTC. Las fechas de sesión de Alpha Vantage y del BCE son fechas de calendario y **no se convierten** de zona horaria.
- **Deduplicado por clave:** fx `(date, base, quote)` y acciones `(date, symbol)` → gana el `ingest_date` más reciente; cripto `(date, coin_id, vs_currency)` → gana el `price_at` más tardío. Columna `ingest_date` como linaje.
- **Reconstrucción completa** desde todo bronze en cada ejecución, escrita en una carpeta temporal y sustituida al final; nombres de fichero fijos (`part-0.parquet`).
- **Partición por `year`** (layout Hive `year=2026/`), no por día, para evitar el problema de los ficheros pequeños.

**Alternativas descartadas:** carga incremental (más compleja, y no compensa con unos pocos MB al año); partición diaria (miles de ficheros de 1 KB); dejar que pandas deduzca los tipos (un texto inesperado acabaría como `object` sin avisar).

**Limitación aceptada:** el precio cripto es una **foto** del momento de la ingesta (~06:00 UTC con Lambda), no un cierre diario oficial; el mercado cripto no cierra. Se documentará en el modelo de la Fase 4.

---

## D-016 · Gold: tabla larga `daily_prices` con moneda y tipo de precio explícitos
**Fecha:** 2026-10-20 · **Fase:** 2

**Contexto:** gold es lo que consultarán Athena (Fase 4), el agente text-to-SQL (Fase 7) y el dashboard. Hay que unir tres clases de activo con precios que no significan lo mismo.

**Opciones:** tabla **ancha** (una columna por activo) · tabla **larga** (una fila por día y activo) · una tabla gold por clase de activo.

**Decisión:** una tabla **larga** `daily_prices` con las columnas `date`, `asset`, `asset_class` (`crypto` | `equity` | `fx`), `price`, `currency`, `price_type` (`close` | `snapshot` | `reference_rate`) y `source`. Clave `(date, asset)`, partición `year=`.
- **Divisas:** `asset = "EUR/USD"`, y `currency` es la *quote* (el precio del EUR expresado en USD).
- **Cripto:** solo la `vs_currency` de la watchlist, para que la clave sea única.
- **Acciones/ETF:** `currency = "USD"`. Es un **supuesto documentado** (los símbolos de la watchlist cotizan en EE. UU.); si se añade un valor europeo habrá que llevar la moneda a la watchlist.
- **Sin volumen:** el de las acciones son títulos negociados y el de cripto son USD en 24 h; mezclarlos en una columna invitaría a errores. Sigue disponible en silver.
- Nuevo punto de entrada `python -m marketpulse.transform` (silver y después gold). Si una capa falla, el proceso para: gold depende de silver.

**Motivo:** la tabla larga admite activos nuevos sin cambiar el esquema, es la forma natural para SQL (`WHERE asset = 'BTC'`, `GROUP BY asset_class`) y, con `currency` y `price_type` en cada fila, el agente no puede confundir un tipo de cambio con un precio en dólares. La tabla ancha obligaría a cambiar el esquema con cada activo nuevo.

**Actualización (2026-10-20, paso 2.5):** gold publica **solo los activos de la watchlist actual**. Silver lo guarda todo; si se quita un activo de la watchlist, su historia sigue en bronze y en silver. Se hace así para que la comprobación de frescura de cada activo no falle para siempre por un activo retirado. La definición de "activos publicados" está en una sola función (`gold.watchlist_assets`), que usan gold y calidad.

---

## D-017 · Calidad de datos: reglas propias, *fail fast* antes de escribir y dos severidades
**Fecha:** 2026-10-20 · **Fase:** 2

**Contexto:** el criterio de aceptación pide comprobaciones de nulos, duplicados, rangos y frescura que pasen con datos buenos y fallen con un dato erróneo.

**Opciones:** librerías de calidad (Great Expectations, pandera, Soda) · comprobaciones propias con pandas.

**Decisión:**
- **Comprobaciones propias** (`quality/checks.py`): `not_null`, `unique`, `in_range`, `rule` (entre columnas), `accepted_values`, `freshness` y `max_daily_jump`. Cada una devuelve un `CheckResult` con el número de filas que fallan y hasta 5 ejemplos.
- **Reglas de MarketPulse** (`quality/rules.py`):
  - silver: claves únicas, sin nulos (salvo `symbol` de cripto), precios > 0, volúmenes ≥ 0 y coherencia OHLC (`low ≤ open, close ≤ high`);
  - gold: sin nulos, `(date, asset)` única, precio > 0, valores admitidos en `asset_class` y `price_type`, y **frescura por activo de la watchlist** (máximo 2 días en cripto y 5 en bolsa y divisas, por el peor caso de Semana Santa). Un activo esperado sin datos también falla.
- **Dos severidades:** `ERROR` para y `WARNING` solo avisa. Los saltos diarios (> 50 % cripto, > 25 % bolsa, > 10 % divisas) son aviso, porque pueden ser reales (un desplome, un *split*).
- ***Fail fast* antes de escribir:** `run_transform` construye silver y gold en memoria, los comprueba y **solo escribe si no hay errores**. Si los hay, se conserva la última versión buena y el proceso sale con código 1.

**Motivo:** son pocas reglas y muy claras. Escribirlas enseña qué hace una librería de calidad por dentro, sin añadir una dependencia pesada; en un equipo real se valoraría pandera o Great Expectations. Comprobar antes de escribir evita publicar datos malos aunque sea un instante.

**Bug encontrado al probar con datos reales:** `max_daily_jump` daba 305 falsos positivos. Si el filtro dejaba la tabla vacía, `.assign()` adoptaba el índice de la columna asignada y fabricaba filas con NaN. Se corrigió añadiendo las columnas antes de filtrar, con un test de regresión.

---

## D-018 · Subida a S3: mismas rutas, solo lo que cambia y nunca borrar
**Fecha:** 2026-10-20 · **Fase:** 2

**Contexto:** el último criterio de la fase pide las tres capas en S3. En la Fase 3, Lambda escribirá directamente en el bucket; ahora hay que subir lo que se ha generado en local.

**Opciones:** `aws s3 sync` (CLI, sin código) · subida con `boto3` · sincronizar borrando lo que sobra (`--delete`).

**Decisión:**
- `common/s3.py` con `boto3`. Se ejecuta con `python -m marketpulse.common.s3`, y el bucket sale de `MARKETPULSE_BUCKET` (en `.env`; no es secreto).
- **Mismas rutas** que en local, con `/` como separador aunque Windows use `\`.
- **Solo sube lo que cambia:** compara el MD5 local con el ETag de S3, que con `put_object` (sin multiparte) y SSE-S3 es el MD5. Es una petición LIST por capa y un PUT por fichero cambiado.
- **Nunca borra objetos en S3.** No hace falta, porque los nombres son fijos y volver a subir sobrescribe. Borrar es la operación peligrosa e irreversible (el bucket no tiene versionado).
- Tests con un `FakeS3` en memoria: sin AWS ni credenciales.

**Motivo:** `aws s3 sync` haría lo mismo hoy, pero la Fase 3 necesita esa lógica en Python dentro de Lambda. Escribirla ahora deja el código probado y reutilizable. **Contrapartida aceptada:** si una partición desaparece en local (por ejemplo, un año entero de silver), su objeto se quedaría huérfano en S3. Con particiones por año, en la práctica no ocurre, y si hiciera falta se borraría a mano tras revisarlo.


---

## D-019 · `botocore[crt]` en el grupo `dev` para usar `aws login` desde boto3
**Fecha:** 2026-10-20 · **Fase:** 2

**Contexto:** la primera subida real a S3 falló con `MissingDependencyException: Using the login credential provider requires an additional dependency ... pip install "botocore[crt]"`. boto3 necesita la librería oficial `awscrt` para leer las credenciales de `aws login`. La AWS CLI la trae incorporada y Terraform (Go) tiene su propio lector, por eso no había fallado antes.

**Opciones:** instalar `botocore[crt]` · exportar las credenciales temporales a la ventana con `aws configure export-credentials --format powershell` en cada sesión.

**Decisión:** `botocore[crt]` en el grupo `dev` de `pyproject.toml` (aprobado por Alberto). Instalado: `awscrt` 0.36.0. Comprobado con una llamada de solo lectura a STS desde boto3 → `assumed-role/AccountFullAccessRole`.

**Motivo:** es la solución que indica el propio error, es oficial de AWS y no cambia el código. Va en `dev` porque solo hace falta en local: en Lambda y en GitHub Actions las credenciales vienen de un rol. La alternativa obliga a repetir un paso manual y deja las credenciales en variables de entorno.

---

## D-020 · Lambda en arm64 con la capa AWS SDK for pandas y un zip determinista construido con Python
**Fecha:** 2026-10-20 · **Fase:** 3

**Contexto:** las Lambdas necesitan pandas y pyarrow (cientos de MB) además de `requests`, `PyYAML` y `python-dotenv`. El límite de Lambda es de 250 MB descomprimidos, sumando función y capas, y 50 MB para un zip subido directamente.

**Opciones:**
- Arquitectura: x86_64 o arm64 (Graviton).
- Dependencias pesadas: meterlas en nuestro zip, crear nuestra propia capa o usar la capa gestionada *AWS SDK for pandas*.
- Construcción del zip: el proveedor de Terraform `hashicorp/archive` (dependencia nueva), una imagen de contenedor o un script de Python propio.

**Decisión (aprobada por Alberto):**
- **arm64**: un 20 % más barato por GB-s en `eu-north-1` (0,0000133334 frente a 0,0000166667 USD) y la capa existe para arm64.
- **Capa gestionada** `arn:aws:lambda:eu-north-1:336392948345:layer:AWSSDKPandas-Python313-Arm64:16` (versión 3.17.1: pandas 3.0.1 y pyarrow 24.0.0).
- **`scripts/build_lambda.py`** genera `build/lambda.zip` (ignorado por Git) con nuestro código, `config/watchlist.yaml` y las dependencias que no trae la capa. Esas dependencias se leen de `pyproject.toml`, se fijan con `==` a la versión del venv local (la que pasó los tests) y se instalan con `pip --platform manylinux2014_aarch64 --only-binary=:all: --no-compile`. Resultado: 1,48 MB comprimido y 5,21 MB descomprimido.
- **Zip determinista:** orden alfabético, fecha fija (1980-01-01), sin `.pyc`, sin `bin/` y sin los `RECORD` de pip. Así, el mismo contenido da el mismo SHA-256 y Terraform solo redespliega cuando algo cambia de verdad.

**Motivo:** el código del proyecto no cambia según la arquitectura, porque las librerías compiladas se descargan ya hechas para arm64. La capa gestionada la mantiene AWS y evita compilar pyarrow. El script no añade dependencias y verifica el resultado: ficheros obligatorios presentes, nada de la capa duplicado, solo binarios de Linux arm64 y dentro de los límites de tamaño.

**Problema encontrado:** las dos primeras construcciones daban hashes distintos. Causa: pip compilaba `.pyc` y generaba lanzadores `.exe` de Windows con la hora dentro, y sus huellas acababan en los ficheros `RECORD`. Solución: `--no-compile` y excluir los `RECORD`, que solo usa pip para desinstalar.

**Limitación aceptada:** el zip solo se puede probar de verdad en Lambda (Linux arm64). La comprobación real será la invocación manual del paso 3.7.

---

## D-021 · Claves de API: parámetros SecureString creados por Terraform con valor de relleno y escritos con la CLI
**Fecha:** 2026-10-20 · **Fase:** 3

**Contexto:** la Lambda de ingesta necesita las claves de CoinGecko y Alpha Vantage. En AWS no hay `.env`, y el *state* de Terraform guarda en texto plano todos los valores que gestiona.

**Opciones:**
1. Variables de entorno de la Lambda.
2. Parámetro con el valor real pasado a Terraform.
3. `value_wo`, atributo de solo escritura que no se guarda en el *state*.
4. Parámetro con valor de relleno + `ignore_changes`, y el valor real escrito con la CLI.
5. Secrets Manager.

**Decisión:** opción 4. Dos `aws_ssm_parameter` (`/marketpulse/coingecko_api_key` y `/marketpulse/alphavantage_api_key`) de tipo `SecureString`, nivel Standard y cifrados con la clave gestionada `alias/aws/ssm`. Alberto escribe el valor con `aws ssm put-parameter --overwrite`, leyendo la clave de `.env` a una variable de PowerShell para que no quede en el historial.

**Motivo:**
- Opciones 1 y 2: el secreto acabaría en el *state*, y en el caso 1 también sería visible en la consola de Lambda.
- Opción 3: obliga a tener las claves en cada `plan`, también en GitHub Actions (Fase 6).
- Opción 5: es de pago y está en la lista de servicios prohibidos sin permiso.
- Opción 4: el secreto no pasa nunca por Terraform, y el "cajón" (nombre, tipo, cifrado y etiquetas) sí queda como código.

**Comprobado:**
- La política de la clave `aws/ssm` permite `kms:Decrypt` a cualquier principal de la cuenta, pero solo a través de SSM (`kms:CallerAccount` + `kms:ViaService = ssm.eu-north-1.amazonaws.com`).
- Por lo tanto, el rol de la Lambda **no necesita `kms:Decrypt`**: le basta con `ssm:GetParameters` sobre los dos ARN.

---

## D-022 · Carga histórica (*backfill*) única en fuentes bronze propias
**Fecha:** 2026-10-21 · **Fase:** 4

**Contexto:** con solo la ingesta diaria, cripto tenía 2 días de historia y divisas 1. Las vistas de la Fase 4 (volatilidad a 30 días, correlación) no podían dar resultados coherentes hasta pasados 1 o 2 meses.

**Opciones:** esperar a acumular datos · validar las vistas solo con bolsa · carga histórica única.

**Decisión (aprobada por Alberto):** `python -m marketpulse.ingest.backfill`, ejecutado a mano.
- **Frankfurter:** `/v2/rates` con `from`/`to` (un año, BCE) en una sola petición. La respuesta tiene la misma forma que la diaria: silver la lee con el mismo `fx_rows` y la validación se comparte (`frankfurter.validate_rates`).
- **CoinGecko:** `/coins/{id}/market_chart?days=365&interval=daily`, el máximo del plan Demo, con un fichero por moneda.
- **Fuentes bronze separadas**, `source=frankfurter_backfill` y `source=coingecko_backfill`: se ve de dónde viene cada dato, se puede rehacer sin tocar la ingesta diaria y es idempotente (mismo nombre → sobrescribe).
- **Subida a S3 solo de esas dos carpetas.** Subir todo `data/` pisaría en S3 bronze, silver y gold con versiones locales más antiguas.
- **Alpha Vantage queda fuera:** más de 100 días (`outputsize=full`) es de pago.

**Reglas en silver (`crypto_history_rows`):**
- Solo se usan los puntos de las **00:00 UTC exactas**. El último punto de la serie es "ahora" y se descarta.
- `change_24h_pct` se calcula con el punto del día anterior (el primer punto se descarta).
- Si un día tiene histórico (00:00) y foto diaria (~06:00), **gana la foto diaria** por ser más tardía. Es el deduplicado de siempre, sin lógica especial.

**Limitación aceptada:** en cripto, los días anteriores al 2026-10-20 son precios de las 00:00 UTC y los posteriores, de hacia las 06:00 UTC. Las dos son fotos (`price_type = snapshot`), pero de horas distintas. Afecta poco a las rentabilidades diarias, y se documentará en el modelo de datos.

**Ensayo local (sin AWS):** fx 510 filas (2025-10-21 → 2026-10-20), cripto 1.092 (2025-10-23 → 2026-10-21), `Calidad: 59 comprobaciones, 0 fallan`.

---

## D-023 · Modelo en estrella: dimensiones y hechos como vistas sobre gold, desplegadas con `terraform_data`
**Fecha:** 2026-10-21 · **Fase:** 4

**Contexto:** el informe pide `dim_asset`, `dim_date` y `fact_daily_price`, con "todo el DDL en `sql/`" y desplegado con Terraform. El proveedor de AWS no tiene un recurso de "vista de Athena".

**Decisión:**
- **`dim_asset`** es una **tabla física** en gold (`gold/dim_asset/part-0.parquet`, sin particiones), que **escribe la Lambda de transformación a partir de `watchlist.yaml`**. Tiene 8 filas: `asset`, `asset_name`, `asset_class`, `currency`, `price_type`, `source` y `annualization_days` (365 cripto, 252 bolsa y divisas). La moneda, el tipo de precio y la fuente salen de las **mismas constantes** (`gold.PRICE_TYPE`, `gold.SOURCE`) que la tabla de hechos.
- **Integridad referencial como regla de calidad:** todo `asset` de `daily_prices` debe existir en `dim_asset` (`check_dim_asset`). Si no, la transformación no publica nada.
- **`dim_date`** es una **vista generada** (`sequence` + `UNNEST`) desde 2025-01-01 hasta `current_date`: no ocupa S3 y nunca se queda corta.
- **`fact_daily_price`** es una **vista** sobre `daily_prices` con solo claves y medidas: `date`, `asset`, `price` y `year` (este último para poder filtrar por partición).
- **Clave natural** (`asset`, `date`) en lugar de claves subrogadas. Los activos no cambian de atributos con el tiempo (no hay dimensión lentamente cambiante) y la clave natural es corta, estable y legible para el agente de la Fase 7.
- **DDL:** las tablas, en Terraform (`glue.tf`); las vistas, en `sql/views/NN_nombre.sql`. Un `terraform_data` con `local-exec` ejecuta `python -m marketpulse.common.athena --deploy-views sql/views` (en orden alfabético y con `CREATE OR REPLACE`, así que es idempotente). Solo se vuelve a lanzar si cambia la huella de algún `.sql`, una tabla o el *workgroup*. **Requisito:** `terraform apply` con el venv activado.

**Alternativas descartadas:**
- **Tablas físicas para hechos y fechas (CTAS):** duplicarían datos que ya están en gold y obligarían a refrescarlas.
- **`dim_asset` como vista con `VALUES` escritos a mano:** duplicaría la watchlist.
- **El proveedor `null`:** sería una dependencia nueva.
- **`aws_athena_named_query`:** solo guarda la consulta, no la ejecuta.

**Limitaciones:**
- Si se borra un fichero de `sql/views/`, la vista no se elimina sola: hay que hacer `DROP VIEW` a mano.
- `terraform destroy` no borra las vistas. No pasa nada: viven en la base de datos de Glue, que sí se borra.

**Errores reales al desplegar:**
1. `sequence(DATE, DATE, INTERVAL '1' DAY)` produjo `timestamp(0)`, que Glue no admite como tipo de columna de una vista.
2. `sequence(DATE, DATE)` no existe en Athena v3.

Solución: generar *timestamps* y convertirlos a `date` en una subconsulta, antes de calcular cualquier columna.

---

## D-024 · La fecha de un precio cripto es la del cierre (00:00 UTC) más cercano
**Fecha:** 2026-10-21 · **Fase:** 4 · **Modifica:** D-015 (silver) y D-022 (*backfill*)

**Contexto:** al validar `v_correlation_matrix` (paso 4.8), la correlación entre cripto y bolsa salía ≈ 0 (BTC-SPY −0,03). La `date` de cripto era el día UTC del instante del precio: el histórico de las 00:00 UTC del día D y la foto de las ~06:00 UTC de D. Su rentabilidad medía, sobre todo, lo que pasó **el día anterior**, mientras que el cierre de SPY del día D es de las 20:00 UTC de D. Comprobación: desplazando la cripto un día, BTC-SPY pasaba a 0,33 y ETH-SPY a 0,26.

**Opciones:** (A) corregir la fecha en silver · (B) desplazar la cripto solo en la vista de correlación · (C) documentarlo y no tocar nada.

**Decisión (aprobada por Alberto):** A. `silver.crypto_close_date(price_at) = (price_at − 12 h).date()`: cada precio es del día cuyo **cierre de las 00:00 UTC** tiene más cerca. Es la convención habitual de cierre diario en cripto.
- 00:00 UTC del 16 (histórico) → **15**.
- ~06:00 UTC del 21 (foto diaria) → **20**.
- 17:50 UTC del 20 (ejecución manual) → **20**.

**Motivo:** el error estaba en el **dato** (la etiqueta `date` no significaba lo mismo para cripto que para bolsa), no en la consulta. Corregirlo en silver arregla todas las vistas y lo que consulte el agente de la Fase 7. La opción B dejaría la trampa en gold para cada consulta futura.

**Consecuencias:**
- La última fecha cripto ahora es "ayer", como en bolsa y divisas. Rango de gold cripto: 2025-10-22 → 2026-10-20.
- La frescura de cripto (2 días como máximo) sigue cumpliéndose.
- Si un día tiene histórico (00:00) y foto diaria (06:00), sigue ganando la foto (`price_at` más tardío). Solo pasa en los días del *backfill* que solapan con la ingesta diaria.

**Verificación:**
- `Calidad: 69 comprobaciones, 0 fallan`.
- Correlación cripto-bolsa del mismo día: BTC-SPY **0,33**, ETH-SPY **0,26**, SOL-SPY **0,34**. Si se desplaza la cripto un día, sale ≈ 0 (−0,00 y −0,06), así que **ya no queda desfase**.
- Rentabilidades (1.897 filas) y volatilidad (1.665 filas) siguen idénticas a pandas.

---

## D-025 · *State* remoto en S3 con bloqueo nativo y bucket creado por un *bootstrap*
**Fecha:** 2026-10-22 · **Fase:** 5 · **Modifica:** D-014 (*state* local)

**Contexto:** el *state* estaba en `infra/terraform.tfstate`, dentro de OneDrive (riesgo de corrupción al sincronizar, sin copias y sin acceso para GitHub Actions en la Fase 6).

**Opciones:**
1. Bucket propio para el *state*, creado por una configuración aparte (`infra/bootstrap/`) con *state* local.
2. Guardar el *state* en el bucket del data lake, bajo `tfstate/`.
3. Gestionar el bucket del *state* dentro de `infra/` (se guardaría en sí mismo).
4. Bloqueo con DynamoDB.

**Decisión:** opción 1 con `use_lockfile = true` (sin DynamoDB).
- **Bucket** `marketpulse-tfstate-<sufijo>`: versionado, bloqueo de acceso público, SSE-S3, `BucketOwnerEnforced`, "solo HTTPS", `prevent_destroy` y ciclo de vida (versiones no actuales a 90 días, marcadores de borrado huérfanos, *multipart* a 1 día). Etiqueta `stack = bootstrap`.
- **`infra/bootstrap/`**: *state* local (ignorado por Git), `TF_DATA_DIR` propio y copia del *lock file* para usar el mismo proveedor (6.69.1).
- ***Backend*** en `infra/versions.tf`: `key = "marketpulse/terraform.tfstate"`, `encrypt = true`, `use_lockfile = true`. El nombre del bucket va aparte (configuración parcial): `backend.hcl` ignorado y `backend.hcl.example` en Git.

**Motivo:**
- Opción 2: mezcla datos con la "llave" de la infraestructura, y un `destroy` del data lake arrastraría su propio *state*.
- Opción 3: es el problema del huevo y la gallina.
- Opción 4: la documentación oficial del *backend* S3 dice que el bloqueo con DynamoDB está obsoleto (*"deprecated and will be removed in a future minor version"*). Además, sería un servicio más que no está en la lista permitida.
- Configuración parcial: un bloque `backend` no admite variables, y cada despliegue desde cero tiene un bucket con otro sufijo.

**Coste:** unos 90 KB por versión del *state*, conservadas 90 días. Menos de 0,01 USD al mes.

**Permisos (para la Fase 6):** según la documentación, `s3:ListBucket` sobre el bucket; `s3:GetObject` y `s3:PutObject` sobre `marketpulse/terraform.tfstate`; y `s3:GetObject`, `s3:PutObject` y `s3:DeleteObject` sobre `marketpulse/terraform.tfstate.tflock`.

**Comprobado:** la migración copió los mismos recursos y *outputs* (el *state* remoto empieza con *serial* 1 y otro *lineage*); el `plan` dice `No changes`; y con dos `plan` a la vez, el segundo falla con `Error acquiring the state lock` (S3 412 *PreconditionFailed*).

Fuente: [Terraform · Backend type: s3](https://developer.hashicorp.com/terraform/language/backend/s3)
