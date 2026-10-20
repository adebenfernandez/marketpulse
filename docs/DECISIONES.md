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
