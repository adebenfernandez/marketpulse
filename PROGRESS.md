# PROGRESS.md — MarketPulse

**Fase actual:** Fase 3 en curso (2026-10-20)
**Siguiente paso:** 2026-10-21 a partir de las 06:35 UTC (08:35 en España): comprobar la ejecución programada (criterio 3) y cerrar la Fase 3

Leyenda: ⬜ pendiente · 🟡 en curso · ✅ terminada

| Fase | Nombre | Estado |
|------|--------|--------|
| 0 | Preparación y seguridad | ✅ |
| 1 | Ingesta en local | ✅ |
| 2 | Transformación y data lake en S3 | ✅ |
| 3 | Automatización con Lambda y EventBridge | 🟡 |
| 4 | SQL y modelo analítico en Athena | ⬜ |
| 5 | Infraestructura como código completa | ⬜ |
| 6 | CI/CD con GitHub Actions | ⬜ |
| 7 | Agente text-to-SQL | ⬜ |
| 8 | Escaparate | ⬜ |

<!--
Plantilla para cada fase (se rellena al trabajarla):

## Fase N · Nombre
**Criterios de aceptación:**
- [ ] ...

### Pasos completados
- Paso N.1 — ... · Evidencia: `comando` → salida resumida

### Problemas encontrados
- ...

### Qué ha aprendido Alberto
- ...

### Cómo contarlo en una entrevista
...

### Pregunta típica de entrevista
**P:** ...
**R:** ...
-->

## Fase 0 · Preparación y seguridad
**Criterios de aceptación:**
- [x] `aws sts get-caller-identity` devuelve el usuario (no la raíz) — rol temporal `AccountFullAccessRole`
- [x] El presupuesto aparece en AWS Budgets
- [x] `terraform -version` funciona
- [x] `pytest` se ejecuta (aunque no haya tests)
- [x] `.env` está ignorado

### Pasos completados
- Paso 0.1 — MFA (TOTP, Google Authenticator) activado en la cuenta raíz · Evidencia: dispositivo listado en "Credenciales de seguridad" (TOTP, 2026-10-19); al volver a iniciar sesión AWS pidió el código.
- Paso 0.2 — Cubierto sin crear usuario IAM: la cuenta usa la "nueva experiencia de AWS" y se entra con AWS Builder ID (propietario del proyecto "First Principles") protegido con MFA, con credenciales temporales. En esta modalidad no se pueden crear usuarios IAM con acceso a consola. Comprobación de identidad pendiente con `aws sts get-caller-identity` en el paso 0.4.
- Paso 0.3 — Presupuesto `marketpulse-mensual` creado en AWS Budgets (2026-10-20): coste mensual recurrente, fijo 5,00 USD, costes sin combinar, ámbito con filtro "Tipo de cargos excluye Credit", alertas reales al 50/80/100 % por email. Evidencia: aparece en la lista de Budgets con estado OK, 5,00 USD presupuestados, 0,00 USD usados. Pendiente: confirmar las 3 alertas y el email verificado.
  - Problema: al enviar la verificación del email sale "You do not have permission to send verification emails… notifications-contacts:CreateEmailContact…". Causa: la SCP de la nueva experiencia (`DenyNotificationContactsOperations`) deniega `notifications-contacts:*` a todos los usuarios del proyecto, incluido el propietario. Las alertas por email directo de Budgets no pueden llegar. Alternativa propuesta: tema de SNS con suscripción por email (SNS está permitido) como destino de las alertas. Aprobada por Alberto.
- Paso 0.3b — Tema SNS estándar `marketpulse-alertas` creado en `eu-north-1` (sin cifrado: los mensajes no son sensibles y evita permisos de KMS; etiqueta `project=marketpulse`). Suscripción por email confirmada. Evidencia: estado "Confirmada" y mensaje de prueba publicado y recibido en el correo.
- Paso 0.3c — Política de acceso del tema: nueva sentencia `PermitirBudgetsPublicar` (principal `budgets.amazonaws.com`, solo `SNS:Publish`, solo este tema, condiciones `aws:SourceAccount` y `aws:SourceArn` = presupuestos de la cuenta). Las 3 alertas del presupuesto ahora van al tema SNS (email directo eliminado). Evidencia: Budgets guardó la configuración sin errores de permisos. **Paso 0.3 completado.**
- Paso 0.4a — AWS CLI v2 y Terraform instalados con winget (2026-10-20). Evidencia: `aws --version` → `aws-cli/2.38.1`; `terraform -version` → `Terraform v1.16.6 on windows_amd64`.
- Paso 0.4b — Terminal conectada con `aws login --profile marketpulse` (región `eu-north-1`; se rechazó la oferta de configurar el MCP de AWS). Evidencia: `aws sts get-caller-identity --profile marketpulse` → la cuenta del proyecto, `arn:aws:sts::<ID-CUENTA>:assumed-role/AccountFullAccessRole/<sesión>` (rol temporal, no raíz); `aws configure get region --profile marketpulse` → `eu-north-1`. Pendiente: comprobar que Terraform lee estas credenciales (primer `terraform plan`, Fase 2).
- Paso 0.5 — `git init -b main`; `.gitignore` (secretos, Terraform state/tfvars, `data/`, Python, cachés); `.env.example`; `pyproject.toml` (Python 3.13, ruff y pytest como extras `dev`, config de ruff y pytest); `src/marketpulse/__init__.py`, `tests/`, README provisional. Venv **fuera de OneDrive** en `C:\Users\deben\.venvs\marketpulse` (aprobado por Alberto) con `pip install -e ".[dev]"`. Evidencia: Python 3.13.15 · ruff 0.17.1 `All checks passed!` · pytest 9.1.1 `collected 0 items / no tests ran` (código 5, esperado sin tests) · `git check-ignore -v .env` → `.gitignore:2:.env` · `.env.example` no ignorado.
- Paso 0.6 — `docs/GLOSARIO.md` (términos del informe + los de la Fase 0, en orden alfabético) y `docs/DECISIONES.md` (D-001 a D-007). `INFORME_PROYECTO.pdf` añadido a `.gitignore`. Repositorio privado `marketpulse` creado por Alberto en GitHub (todavía sin `git push`). Primer commit en local.

### Problemas encontrados
- La carpeta del proyecto está dentro de OneDrive y Alberto decide mantenerla ahí → venv fuera de OneDrive (D-006).
- La cuenta usa la **"nueva experiencia de AWS"**: no hay usuarios IAM con consola, ni Identity Center ni Organizations, y la región es fija (`eu-north-1`). Se adapta el plan (D-001, D-002, D-003).
- La SCP gestionada impide verificar el email de las alertas de Budgets → alertas a través de SNS (D-004).
- **Riesgos abiertos:** (1) ~~comprobar que Terraform lee las credenciales de `aws login`~~ → resuelto en el paso 2.2; (2) comprobar que el OIDC de GitHub Actions funciona con las SCP de los proyectos (Fase 6) → **la SCP deniega `iam:*Provider*`** (ver Fase 3, paso 3.1); (3) el plan gratuito termina hacia abril de 2027.

### Qué ha aprendido Alberto
- La diferencia entre cuenta raíz, identidad personal con MFA y credenciales temporales (roles asumidos con STS), y por qué no se usan claves permanentes.
- Que el control de costes empieza antes de crear nada: presupuesto con umbrales, sin contar créditos, y que Budgets **avisa pero no frena**, y con retraso.
- A leer un error de permisos (`servicio:acción`) y que una SCP con `Deny` gana a cualquier permiso de IAM.
- A escribir una política de recurso con mínimo privilegio: principal, acción, recurso y condiciones contra el *confused deputy*.
- Cómo preparar un repositorio Python profesional: `.gitignore` antes del primer commit, `pyproject.toml`, entorno virtual, ruff y pytest.

### Cómo contarlo en una entrevista
"Antes de escribir código preparé la cuenta de AWS con seguridad y control de costes: identidad con MFA y credenciales temporales en lugar de claves permanentes, y un presupuesto con alertas. Mi cuenta usaba la nueva modalidad de AWS, con políticas de organización gestionadas que bloqueaban las alertas por email; lo diagnostiqué leyendo el error y la SCP, y lo resolví enviando las alertas por un tema de SNS con una política de mínimo privilegio. También adapté la región a la restricción de la plataforma y documenté cada decisión con su motivo."

### Pregunta típica de entrevista
**P:** ¿Por qué no usas claves de acceso de IAM en tu portátil o en GitHub?
**R:** Porque son permanentes: si se filtran, sirven hasta que alguien las borra. Uso credenciales temporales (`aws login` en local y OIDC en GitHub Actions), que caducan solas en horas, de modo que una filtración tiene un impacto muy limitado. Además, así no hay ningún secreto de AWS que guardar ni que rotar.

## Fase 1 · Ingesta en local
**Criterios de aceptación:**
- [x] `python -m marketpulse.ingest` genera ficheros para todas las fuentes — `Resumen: 3/3`, 5 ficheros en `data/bronze/`
- [x] Ejecutarlo dos veces el mismo día no duplica datos — siguen siendo 5 ficheros tras varias ejecuciones
- [x] `pytest` pasa — `64 passed`
- [x] `ruff check` sin errores — `All checks passed!`

### Pasos completados
- Paso 1.1 — `config/watchlist.yaml` (EUR→USD/GBP · BTC, ETH, SOL con `coingecko_id` · SPY, VT, QQQ) y `src/marketpulse/common/config.py` (lectura con `yaml.safe_load`, validación con `ConfigError`, dataclasses inmutables, normalización de mayúsculas/minúsculas). Dependencias `requests`, `PyYAML` y `python-dotenv` añadidas (D-008). Evidencia: `pytest -q` → `4 passed` · `ruff check .` → `All checks passed!` (ejecutado también por Alberto).
- Paso 1.2 — `src/marketpulse/common/http.py`: `HttpClient.get_json()` con timeout (10 s), reintentos con espera exponencial (1/2/4 s, tope 30 s, respeta `Retry-After`) solo para errores pasajeros (429, 5xx, red), sin reintento para 4xx ni para cuerpos que no son JSON, logging con las claves de API ocultas (`redact`). Sesión y `sleep` inyectados para poder probar sin internet. Evidencia: `pytest -q` → `14 passed` · `ruff check .` → `All checks passed!`.
- Paso 1.3 — `src/marketpulse/common/storage.py`: `bronze_path()` (`bronze/source=<fuente>/dt=<AAAA-MM-DD>/<nombre>.json`, nombres validados contra *path traversal*) y `write_bronze()` (respuesta original tal cual, escritura atómica con temporal + `os.replace`, fecha UTC). D-009. Evidencia: `pytest -q` → `27 passed` (incluye "dos ejecuciones el mismo día dejan 1 fichero" y "un fallo a mitad deja intacto el anterior") · `ruff check .` → `All checks passed!`.
- Paso 1.4 — `src/marketpulse/ingest/frankfurter.py` (API **v2**, `providers=ECB`, una petición para todas las divisas, validación de forma con `UnexpectedResponseError`, aviso si falta una divisa) y `ingest/errors.py`. Documentación oficial consultada: v1 obsoleta y v2 mezcla bancos por defecto (D-010). Evidencia: `pytest -q` → `33 passed` · llamada real → `200 en 406 ms`, `data/bronze/source=frankfurter/dt=2026-10-20/frankfurter.json` con GBP 0,84028 y USD 1,1215; `data/` no aparece en `git status`.
- Paso 1.5 — `src/marketpulse/ingest/coingecko.py`: `/simple/price` en una llamada (precio, capitalización, volumen, variación 24 h, `last_updated_at`), clave Demo **opcional** en cabecera `x-cg-demo-api-key` (D-011), aviso si falta un id. `COINGECKO_API_KEY` añadida a `.env.example`. Evidencia: `pytest -q` → `42 passed` · llamada real sin clave → `200 en 402 ms`, `data/bronze/source=coingecko/dt=2026-10-20/coingecko.json` con BTC, ETH y SOL. Pendiente: clave Demo antes de la Fase 3 y texto de atribución (Fase 8).
- Paso 1.6 — `src/marketpulse/ingest/alphavantage.py`: `TIME_SERIES_DAILY` `compact` (100 días), 1 petición por símbolo con pausa de 1,5 s (*throttling*), detección de los "200 con aviso" (`Information`/`Note`/`Error Message`), fallo parcial (`PartialIngestError`) y `MissingApiKeyError` sin clave (D-012). Clave de Alpha Vantage creada por Alberto y guardada solo en `.env`. Evidencia: `pytest -q` → `54 passed` · llamada real → SPY, VT y QQQ con `200` y "100 días guardados"; la clave aparece como `'apikey': '***'` en todos los logs.
- Paso 1.7 — `src/marketpulse/ingest/run.py` (`run_all()`: las tres fuentes siempre, una sola `dt`, `except Exception` por fuente con `logger.exception`; `main()`: `load_dotenv`, logging con hora, resumen, código de salida 0/1; `get_secret()`: clave vacía o de solo espacios = `None`) y `ingest/__main__.py`. Mejora de seguridad en `HttpClient`: cualquier otro `requests.RequestException` se convierte en `HttpError` sin el mensaje original ni encadenamiento (D-013). Evidencia: `pytest -q` → `64 passed` · `python -m marketpulse.ingest` → `Resumen: 3/3 fuentes correctas`, `$LASTEXITCODE` → `0` · con `ALPHAVANTAGE_API_KEY=" "` → `2/3`, `MissingApiKeyError` sin llamar a Alpha Vantage, `$LASTEXITCODE` → `1` · tras varias ejecuciones el mismo día `(Get-ChildItem -Recurse data -File).Count` → `5` (sin duplicados).
  - **Nota para la Fase 2:** `dt` es la fecha de **ingesta** y `date` (dentro del JSON) la fecha del **dato**. Con la Lambda a las 06:00 UTC no coinciden (el BCE publica ~16:00 CET), y en fines de semana se repite el último día hábil. Silver debe usar `date` como fecha del dato y deduplicar por (`date`, `base`, `quote`).

### Problemas encontrados
- Al ejecutar `pytest` desde `C:\WINDOWS\system32` (PowerShell de administrador), pytest recorrió carpetas del sistema y dio `PermissionError`. Causa: pytest y ruff trabajan sobre la carpeta actual. Solución: `cd` a la raíz del proyecto y usar una PowerShell normal (mínimo privilegio).
- `.env` existía pero estaba vacío (0 bytes): `.env.example` es solo la plantilla, y las líneas se escriben a mano en `.env`.
- Primera ejecución real de Alpha Vantage: SPY bien, y VT y QQQ con un `200` y `Information: ... (1 request per second)`. Hay un límite de ráfaga no documentado en la página de soporte. Solución: pausa de 1,5 s entre símbolos. El fallo parcial funcionó como estaba diseñado.
- Al probar el código de salida, `$env:ALPHAVANTAGE_API_KEY = ""` no dejó la clave vacía: en PowerShell eso **borra** la variable, y `load_dotenv()` cargó la clave real (3 peticiones gastadas). Se probó con `" "` y se añadió `get_secret()` para que una clave de solo espacios cuente como ausente.

- **Riesgos abiertos de esta fase:** (1) ~~crear la clave Demo de CoinGecko antes de la Fase 3~~ → resuelto en el paso 3.2; (2) fijar el texto de atribución de CoinGecko y la cita del BCE (Fase 8); (3) los precios de Alpha Vantage no están ajustados por dividendos (Fase 4).

### Qué ha aprendido Alberto
- Qué es una API REST, cómo se lee una respuesta JSON y qué significan los códigos HTTP (2xx/4xx/5xx, 429).
- Por qué toda llamada necesita *timeout*, y cuándo reintentar con espera exponencial (errores pasajeros) y cuándo no (4xx: el error es nuestro).
- Que un 200 no siempre es un éxito (los avisos de Alpha Vantage) y que la documentación no lo cuenta todo (el límite de ráfaga): siempre hace falta una prueba real.
- A proteger las claves de API: `.env` ignorado, plantilla `.env.example`, cabecera mejor que URL, `redact` en los logs y nunca el texto de las excepciones de `requests`.
- Idempotencia mediante nombres de fichero deterministas, particionado `clave=valor`, escritura atómica y fecha UTC; la diferencia entre fecha de ingesta (`dt`) y fecha del dato (`date`).
- A tratar los fallos parciales y a decidir dónde atrapar errores (solo los esperables abajo, todos arriba y con traza), y qué es un código de salida.
- A probar sin internet con mocks, `monkeypatch`, `tmp_path`, `caplog`, `parametrize` y fixtures propias, inyectando dependencias (sesión HTTP, `sleep`).
- Detalles de Windows: ejecutar desde la carpeta del proyecto, no usar PowerShell de administrador, y que `$env:X = ""` borra la variable.

### Cómo contarlo en una entrevista
"Construí la ingesta diaria de tres APIs públicas (BCE vía Frankfurter, CoinGecko y Alpha Vantage) como un paquete Python con un cliente HTTP común: *timeout*, reintentos con espera exponencial solo para errores pasajeros y logs sin claves. Cada respuesta se guarda tal cual en una capa bronze particionada por fuente y fecha UTC, con escritura atómica, de modo que relanzar el proceso nunca duplica datos. Al probarlo con las APIs reales descubrí que Alpha Vantage devuelve errores con código 200 y tiene un límite de una petición por segundo que su documentación no menciona; lo detecté, lo documenté y lo resolví espaciando las peticiones. Todo está cubierto con 64 tests que no llaman a internet, y el proceso devuelve un código de salida que permite automatizarlo y vigilarlo."

### Pregunta típica de entrevista
**P:** Tu proceso de ingesta falla a mitad y alguien lo relanza. ¿Cómo evitas datos duplicados o corruptos?
**R:** Con idempotencia y escritura atómica. Cada fichero tiene una ruta que depende solo de la fuente, la fecha y el símbolo (`source=.../dt=.../SPY.json`), nunca de la hora, así que relanzar sobrescribe en lugar de añadir. Escribo primero en un temporal de la misma carpeta y lo renombro con `os.replace`, que es atómico: o queda el fichero anterior completo o el nuevo completo, nunca uno a medias. Además, valido la respuesta antes de escribir, para que un aviso de la API no se guarde como si fueran datos.

## Fase 2 · Transformación y data lake en S3
**Criterios de aceptación:**
- [x] El bucket tiene acceso público bloqueado y cifrado — comprobado con `get-public-access-block` y `get-bucket-encryption` (paso 2.2), más "solo HTTPS" (2.2b)
- [x] Existen las tres capas en S3 — `aws s3 ls --recursive`: 5 objetos en `bronze/`, 3 en `silver/` y 1 en `gold/`
- [x] Las comprobaciones de calidad pasan, y fallan con un dato erróneo a propósito en un test — `Calidad: 59 comprobaciones, 0 fallan` con los datos reales; `tests/test_quality.py` las hace fallar a propósito

### Pasos completados
- Paso 2.1 — Precios oficiales de S3 en `eu-north-1` (AWS Price List API, publicada el 2026-10-15): S3 Standard 0,023 USD/GB-mes (primeros 50 TB) · PUT/COPY/POST/LIST 0,005 USD por 1.000 · GET 0,0004 USD por 1.000 · entrada desde internet 0 USD · salida a internet 0,09 USD/GB, con los primeros 100 GB/mes gratis (agregados en toda AWS). Volumen medido: bronze ≈ 55 KB/día. Estimación: < 0,01 USD/mes durante el primer año. Dependencias aprobadas por Alberto: `pandas`, `pyarrow`, `boto3` y el proveedor de Terraform `hashicorp/aws`.
- Paso 2.2 — `infra/` (Terraform): bucket `marketpulse-datalake-<sufijo>` con bloqueo de acceso público, SSE-S3, `BucketOwnerEnforced` y `default_tags` (D-014). `TF_DATA_DIR` en `C:\Users\deben\.terraform-data\marketpulse`. `terraform init/fmt/validate/plan` → `Plan: 4 to add`; `terraform apply "tfplan"` ejecutado por Alberto tras su "sí" → `Apply complete! Resources: 4 added`. Evidencia con la API de AWS: `get-public-access-block` → las 4 a `true` · `get-bucket-encryption` → `AES256` (y SSE-C bloqueado por defecto por AWS) · `get-bucket-ownership-controls` → `BucketOwnerEnforced` · `get-bucket-tagging` → `project`/`managed_by`. `terraform.tfstate` y `tfplan` ignorados por Git. **Riesgo de la Fase 0 resuelto:** Terraform lee las credenciales de `aws login`.
- Paso 2.2b — Política de bucket "solo HTTPS" (`Deny s3:*` si `aws:SecureTransport = false`), aprobada por Alberto. `plan` → `1 to add`; `apply` → `1 added`. Evidencia: `get-bucket-policy` → la política guardada · `aws s3 ls s3://<bucket>` por HTTPS → sin error (bucket vacío) · el mismo comando con `--endpoint-url http://...` → `AccessDenied ... with an explicit deny in a resource-based policy`. Un segundo `apply "tfplan"` por error → `Saved plan is stale` (Terraform se niega a aplicar un plan desactualizado; no cambió nada).
- Paso 2.3 — `src/marketpulse/transform/` (`schemas.py`, `bronze.py`, `silver.py`, `tables.py`): tres tablas silver (`fx_rates`, `crypto_prices`, `stock_prices`) con esquema `pyarrow` explícito, nombres en snake_case, precios de texto a número, `price_at` en UTC, deduplicado por clave (gana lo más reciente), reconstrucción completa con sustitución segura de carpeta y partición `year=` (D-015). `pandas` 3.0.6, `pyarrow` 26.0.0 y `boto3` 1.43.115 instalados. Evidencia: `pytest -q` → `75 passed` · con los datos reales → `fx_rates` 2 filas, `crypto_prices` 3, `stock_prices` 300 · tipos dentro del Parquet: `date32`, `float64`, `int64`, `timestamp[us, tz=UTC]` · compresión Snappy: 54,7 KB de JSON → 14,7 KB de Parquet.
- Paso 2.4 — `transform/gold.py`: tabla gold `daily_prices` en formato largo (`date`, `asset`, `asset_class`, `price`, `currency`, `price_type`, `source`), sin volumen, partición `year=` (D-016). Punto de entrada `python -m marketpulse.transform` (`transform/run.py`). Evidencia: `pytest -q` → `81 passed` · con los datos reales → `Gold daily_prices: 305 filas {'equity': 300, 'crypto': 3, 'fx': 2}`, código de salida 0; EUR/GBP con `currency = GBP`.
  - **Nota para la Fase 4:** las rentabilidades se calculan con `LAG` sobre la sesión anterior **del mismo activo** (`PARTITION BY asset ORDER BY date`), nunca sobre "ayer" en el calendario. El lunes de una acción compara con el viernes (3 días naturales), mientras que cripto tiene 7 sesiones por semana. Para comparar clases: alinear fechas o comparar rentabilidades semanales o mensuales. Al anualizar la volatilidad: unas 252 sesiones al año en bolsa frente a 365 en cripto.
- Paso 2.5 — `src/marketpulse/quality/` (`checks.py`, `rules.py`): nulos, duplicados, rangos, coherencia OHLC, valores admitidos, frescura por activo y saltos diarios (aviso). `run_transform` construye silver y gold en memoria, comprueba y solo escribe si no hay errores; gold publica solo los activos de la watchlist (D-017, actualización de D-016). Evidencia: `python -m marketpulse.transform` → `Calidad: 59 comprobaciones, 0 fallan`, código 0 · `pytest -q` → `103 passed`, incluidos `test_silver_con_dato_erroneo_falla` (×5), `test_un_dato_erroneo_no_se_publica_y_se_conserva_lo_anterior` y `test_datos_viejos_no_se_publican`.
- Paso 2.6 — `src/marketpulse/common/s3.py`: subida de bronze, silver y gold con las mismas rutas (claves con `/`), solo lo que cambia (MD5 local frente al ETag de S3) y sin borrar nunca (D-018). `MARKETPULSE_BUCKET` en `.env`. Dependencia `botocore[crt]` en `dev` para que boto3 lea `aws login` (D-019). Evidencia: `python -m marketpulse.common.s3` → `S3: 9 subidos, 0 sin cambios` · `aws s3 ls --recursive` → los 9 objetos en `bronze/`, `silver/` y `gold/` · segunda ejecución → `S3: 0 subidos, 9 sin cambios` · `pytest -q` → `108 passed`.
### Problemas encontrados
- La sesión de `aws login` caducó (12 h): `Your session has expired` → `aws login --profile marketpulse`.
- `max_daily_jump` daba 305 falsos positivos: `.assign()` sobre una tabla filtrada vacía fabricaba filas NaN. Corregido con un test de regresión (D-017).
- boto3 no podía leer las credenciales de `aws login` (`MissingDependencyException ... botocore[crt]`). Se instaló `botocore[crt]` en `dev` (D-019).
- Un segundo `terraform apply "tfplan"` por error → `Saved plan is stale`: Terraform se negó y no cambió nada.
- Barras invertidas de Windows rompiendo scripts (`\U` en `sed` y en textos de Python): se usan *raw strings* o ficheros de script.
- **Riesgos abiertos de esta fase:** (1) ~~comprobar las versiones de la capa *AWS SDK for pandas*~~ → pandas 3.0.5 y pyarrow 24.0.0, funciona (paso 3.7); (2) el precio cripto es una foto a la hora de la ingesta, no un cierre (documentarlo en el modelo de la Fase 4); (3) las rentabilidades de la Fase 4 deben usar la sesión anterior del mismo activo (ver la nota del paso 2.4).

### Qué ha aprendido Alberto
- Cuánto cuesta S3 y cómo se calcula (GB-mes, PUT/GET, transferencia), consultando la fuente oficial antes de crear nada.
- Terraform desde cero: provider, recurso, *state*, *lock file*, `init/fmt/validate/plan/apply`, `plan -out` + `apply tfplan`, grafo de dependencias, `data` y `depends_on`, y por qué un segundo `plan` dice "No changes".
- Las protecciones de un bucket: bloqueo de acceso público, cifrado en reposo (SSE-S3) y en tránsito (política "solo HTTPS"), sin ACL; y a leer un `AccessDenied ... explicit deny in a resource-based policy`.
- Parquet y el formato columnar, compresión, esquemas con tipos exactos, fecha de calendario frente a instante UTC, deduplicado por clave y la arquitectura medallion bronze → silver → gold.
- A diseñar una tabla gold para quien la consume: formato largo, moneda y tipo de precio explícitos, y no mezclar unidades.
- Calidad de datos: nulos, duplicados, rangos, coherencia, frescura, errores frente a avisos, *fail fast* antes de escribir y "todo o nada" frente a cuarentena.
- boto3, MD5/ETag para subir solo lo que cambia, y por qué el código no borra nunca en S3.
- Que los problemas reales aparecen al ejecutar de verdad (falsos positivos, la dependencia de `aws login`) y se resuelven leyendo el mensaje.

### Cómo contarlo en una entrevista
"Monté un data lake en S3 con tres capas: bronze con la respuesta original de cada API, silver con tablas Parquet limpias y tipadas, y gold con una tabla diaria por activo pensada para análisis. El bucket lo creé con Terraform, con el acceso público bloqueado, cifrado en reposo y una política que rechaza cualquier conexión sin HTTPS. La transformación construye las capas en memoria, pasa 59 comprobaciones de calidad (nulos, duplicados, rangos, coherencia OHLC y frescura por activo) y solo publica si no hay errores, así que un dato malo nunca llega a gold. Al probarlo con datos reales encontré un falso positivo en una de las reglas, lo diagnostiqué y lo blindé con un test de regresión."

### Pregunta típica de entrevista
**P:** ¿Por qué guardas los datos en Parquet y no en CSV o JSON?
**R:** Porque es columnar: cada columna se guarda junta, así que una consulta que solo usa dos columnas lee solo esas dos, y los valores parecidos se comprimen muy bien. En mi proyecto, 55 KB de JSON se quedaron en 15 KB de Parquet. Además, Parquet guarda el esquema con los tipos (fecha, decimal, entero), así que quien lo lee no tiene que adivinarlos. Con Athena, que cobra por datos escaneados, eso se traduce directamente en consultas más rápidas y más baratas.

## Fase 3 · Automatización con Lambda y EventBridge
**Criterios de aceptación:**
- [x] Una ejecución manual de la Lambda escribe datos nuevos en S3 — paso 3.7
- [x] Los logs se ven en CloudWatch — `aws logs tail` (paso 3.7)
- [ ] La ejecución programada del día siguiente ha funcionado
- [x] La política de IAM no usa `*` en recursos — `get-role-policy` y simulador (paso 3.6)

### Pasos completados
- Plan aprobado por Alberto (2026-10-20): capa gestionada *AWS SDK for pandas*; zip con un script de Python (sin el proveedor `archive`); sin SQS, con destino *on-failure* de Lambda hacia el tema SNS; `"Resource": "*"` prohibido, pero se admiten rutas acotadas al bucket (`<bucket>/bronze/*`); tema SNS leído con `data` e importado en la Fase 5; ingesta a las 06:00 UTC y transformación a las 06:30 UTC.
- Paso 3.1 — Lectura de documentación y precios oficiales, sin cambios en AWS.
  - **SCP y RCP** (docs *Managed policies for your organization*): el plan gratuito permite `lambda:*`, `scheduler:*`, `logs:*`, `cloudwatch:*`, `ssm:*`, `kms:*`, `iam:*`, `sns:*`, `s3:*`, `events:*`, `glue:*` y `athena:*`. La SCP `ProtectManagedRoles` solo protege `role/managed/*`, así que nuestros roles se pueden crear. Las RCP solo bloquean a principales de fuera de la organización. Si se configurara un *spend limit*, cerca del límite se denegaría `lambda:InvokeFunction`.
  - **Capa:** `aws lambda get-layer-version-by-arn` → `AWS SDK for pandas Lambda Layer - 3.17.1 (Python 3.13)`, creada el 2026-08-03. arm64: `arn:aws:lambda:eu-north-1:336392948345:layer:AWSSDKPandas-Python313-Arm64:16` (55,7 MB comprimida). x86_64: `...:AWSSDKPandas-Python313:16` (59,5 MB). Según `uv.lock` y el script de construcción de la 3.17.1, trae **pandas 3.0.1** (en local, 3.0.6) y pyarrow **24.0.0** compilado (en local, 26.0.0), ambas compatibles con `pandas>=2.2` y `pyarrow>=18`. **No trae `requests` ni `PyYAML`**: van en nuestro zip. Las versiones reales se registrarán en el log al arrancar la Lambda (paso 3.7).
  - **Precios en `eu-north-1`** (AWS Price List API y páginas oficiales):
    - Lambda: 0,20 USD por millón de peticiones; 0,0000133334 USD/GB-s en arm64 frente a 0,0000166667 en x86 (−20 %); capa gratuita de 1 M peticiones y 400.000 GB-s al mes; 512 MB de `/tmp` sin coste.
    - EventBridge Scheduler: 14 M invocaciones al mes gratis; después, 1,09 USD por millón.
    - CloudWatch: logs a 0,54 USD/GB ingerido y 0,028 USD/GB-mes; alarmas a 0,10 USD cada una al mes. Capa gratuita: 5 GB de logs y 10 métricas de alarma.
    - SSM Parameter Store estándar: sin coste.
    - KMS con la clave gestionada por AWS: sin cuota mensual; 0,03 USD por cada 10.000 peticiones, con 20.000 gratis al mes.
  - **Estimación:** unos 600 GB-s y 60 invocaciones al mes → 0 USD con la capa gratuita. Sin ella, menos de 0,25 USD/mes (lo que más pesa son las alarmas).
- Paso 3.2 — Clave Demo de CoinGecko creada por Alberto (plan Demo gratuito, sin tarjeta, casilla de marketing sin marcar) y guardada solo en `.env` como `COINGECKO_API_KEY`. Evidencia: `/ping` con una clave inventada → `Unauthorized` (401) · con la clave real → `(V3) To the Moon!` · `python -m marketpulse.ingest` → CoinGecko `200 en 396 ms` sin el aviso "sin clave", `Resumen: 3/3 fuentes correctas`, y la clave no aparece en los logs. **Riesgo de la Fase 1 resuelto.**
- Paso 3.3 — Handlers de Lambda (solo código local, sin AWS):
  - `ingest/handler.py`: lee las claves de SSM, ejecuta `run_all` en un `TemporaryDirectory` de `/tmp`, sube bronze **aunque falle una fuente** y después lanza `JobFailedError`.
  - `transform/handler.py`: descarga todo bronze, ejecuta `run_transform`; si la calidad falla, lanza un error y no sube nada; si va bien, sube silver y gold. Deja en el log las versiones de pandas y pyarrow.
  - Módulos nuevos: `common/ssm.py` (`get_parameters`: una sola llamada, `WithDecryption=True`, error con nombres y nunca con valores), `common/lambda_runtime.py` (`JobFailedError`, `configure_logging`, `require_env`) y `common/s3.py` (`download_layer`, con defensa contra *path traversal*).
  - Tests: `FakeS3` se mueve a `tests/fakes.py`, junto con `FakeSSM`.
  - Evidencia: `pytest -q` → `121 passed` (13 nuevos) · `ruff check .` → `All checks passed!` · `ruff format --check .` → `48 files already formatted` · prueba de integración local con el bronze real y un S3 falso → `Calidad: 59 comprobaciones, 0 fallan`, `{'bronze_downloaded': 5, 'uploaded': 4, 'unchanged': 0}`.
- Paso 3.4 — `scripts/build_lambda.py` genera `build/lambda.zip` para arm64 y Python 3.13 (D-020). Contenido: `marketpulse/`, `config/watchlist.yaml` y certifi, charset-normalizer, idna, python-dotenv, PyYAML, requests y urllib3, todas fijadas con `==` a la versión del venv. Evidencia: `python scripts/build_lambda.py` → `192 ficheros | 1.48 MB comprimido | 5.21 MB descomprimido`. Los únicos binarios son `*.cpython-313-aarch64-linux-gnu.so` (charset_normalizer y yaml). Sin pandas, pyarrow ni boto3, y sin `.env`, `data/` ni `tfstate`. Dos construcciones seguidas dan el mismo `SHA-256 (base64): nfFkGQVX...ERYQ=`. `pytest -q` → `121 passed`.
  - Problema: al principio los hashes cambiaban entre construcciones. Los `RECORD` de pip incluían la huella de `.pyc` y de lanzadores `.exe` con la hora dentro → se añadió `--no-compile` y se excluyeron los `RECORD`.
- Paso 3.5 — `infra/ssm.tf`: dos parámetros `SecureString` (`for_each`, nivel Standard, `alias/aws/ssm`) con valor de relleno e `ignore_changes = [value]`, y el *output* `api_key_parameter_names` (D-021). `terraform apply` ejecutado por Alberto → `2 added`. Las claves reales se escribieron con `aws ssm put-parameter --overwrite` desde variables de PowerShell → `Version: 2`.
  - Evidencia: `describe-parameters` → 2 filas `SecureString`, `alias/aws/ssm`, versión 2 · longitud del valor descifrado → 27 y 16 (igual que en `.env` sin espacios) · `Select-String` de las claves en `terraform.tfstate` → sin resultados (**el secreto no está en el *state***) · `terraform plan` → `No changes` · política de `aws/ssm` → `kms:Decrypt` permitido vía `kms:ViaService = ssm.eu-north-1.amazonaws.com`, así que la Lambda no necesita `kms:Decrypt`.
  - Hallazgo: en `.env` las tres líneas tienen un espacio después del `=`. No rompe nada, porque `python-dotenv` y `get_secret()` recortan, y a SSM se subió el valor recortado.
- Paso 3.6 — `infra/logs.tf` (`locals.lambda_functions`; grupos `/aws/lambda/marketpulse-{ingest,transform}` con retención de 14 días) e `infra/iam.tf` (un rol por función con política de confianza solo para `lambda.amazonaws.com` y políticas en línea sin `"Resource": "*"`: logs solo de su grupo, `ssm:GetParameters` solo en los 2 ARN y solo para la ingesta, `s3:ListBucket` con condición `s3:prefix`, ingesta `PutObject` solo en `bronze/*`, transformación `GetObject` en `bronze/*` y `PutObject` en `silver/*` y `gold/*`, nadie con `DeleteObject`). `terraform apply` ejecutado por Alberto → `6 added`.
  - Evidencia: `describe-log-groups` → 2 grupos con retención 14 · `get-role-policy` → 4 sentencias, todas con ARN concretos · `simulate-principal-policy` con `aws:RequestedRegion=eu-north-1`: ingesta `PutObject` bronze **allowed** y gold **implicitDeny**; transformación `GetObject` bronze **allowed**, `PutObject` y `DeleteObject` bronze **implicitDeny**; `ssm:GetParameters` **allowed** para la ingesta e **implicitDeny** para la transformación. **Criterio 4 cumplido.**
  - Problema: el simulador daba `explicitDeny` en todo, con `AllowedByOrganizations: false`. Causa: sin `--context-entries` no envía `aws:RequestedRegion`, y la SCP de restricción de región (`RegionFloor`) deniega cuando falta esa clave. Al pasar la región, los resultados son los esperados. Las peticiones reales sí llevan la región, así que no afecta a las Lambdas. Además: con varios `--resource-arns` el resultado de cada recurso va en `ResourceSpecificResults` (hay que simular uno a uno), y Git Bash convierte `/marketpulse/...` en una ruta de Windows (`MSYS_NO_PATHCONV=1`).
- Paso 3.7 — `infra/lambda.tf`: dos `aws_lambda_function` con `for_each`, el mismo zip y `source_code_hash`, `python3.13`, arm64 y `logging_config` hacia su grupo de logs. La ingesta tiene 256 MB, 300 s, sin capa y los nombres de SSM. La transformación tiene 1024 MB, 120 s y la capa AWS SDK for pandas. *Output* `lambda_function_names`. `terraform apply` ejecutado por Alberto → `2 added`.
  - Evidencia (invocación manual con `aws lambda invoke --cli-read-timeout 600`): ingesta → `StatusCode 200`, `{"sources_ok": ["alphavantage", "coingecko", "frankfurter"], "failed": {}, "uploaded": 5}`; transformación → `200`, `{"bronze_downloaded": 5, "uploaded": 4}`. `aws logs tail`: ingesta con 3 APIs en `200` y `apikey: '***'`, `REPORT Duration 7014 ms, Billed 7391 ms, Max Memory 114/256 MB, Init 376 ms`; transformación con `Versiones: pandas 3.0.5, pyarrow 24.0.0`, `Calidad: 59 comprobaciones, 0 fallan`, `REPORT Duration 1363 ms, Billed 4160 ms, Max Memory 237/1024 MB, Init 2796 ms`. `aws s3 ls`: `coingecko.json` 19:50:29 y `gold/.../part-0.parquet` 19:50:57 (hora de España), después de la subida de la Fase 2. **Criterios 1 y 2 cumplidos.**
  - Observaciones: (1) la capa trae **pandas 3.0.5** (no 3.0.1 como deducía el `uv.lock`), compatible con `>=2.2`, y los datos pasan la calidad → **riesgo de la Fase 2 resuelto**. (2) `Billed Duration` = duración + `Init Duration`: AWS cobra también el arranque en frío, y la capa de pandas añade unos 2,8 s. Coste aproximado por día: 0,25 GB × 7,4 s + 1 GB × 4,2 s ≈ 6 GB-s → unos 180 GB-s al mes, frente a 400.000 gratis. (3) `Found credentials in environment variables`: Lambda inyecta las credenciales temporales del rol como variables de entorno y boto3 las encuentra solo. (4) La transformación usa 237 de 1024 MB; se podría bajar memoria, pero también bajaría la CPU (idea para más adelante, sin cambiarlo ahora).
- Paso 3.8 — `infra/scheduler.tf`:
  - Rol `marketpulse-scheduler`: confianza solo para `scheduler.amazonaws.com` con `aws:SourceAccount` y `lambda:InvokeFunction` solo sobre los 2 ARN.
  - Dos `aws_scheduler_schedule`: `cron(0 6 * * ? *)` y `cron(30 6 * * ? *)` en UTC, `flexible_time_window OFF`, `retry_policy` de 3 intentos y 1 h, sin DLQ (no hay SQS).
  - En `lambda.tf`: `data "aws_sns_topic" "alertas"` (solo lectura) y `aws_lambda_function_event_invoke_config` con 2 reintentos, 1 h y `on_failure` hacia el tema SNS.
  - En `iam.tf`: sentencia `AvisarDeFallos` (`sns:Publish` solo sobre ese tema) en los dos roles.
  - `terraform apply` ejecutado por Alberto → `6 added, 2 changed` (sin errores de consistencia eventual).
  - Evidencia: `list-schedules` → 2 `ENABLED` · `get-schedule` → `cron(0 6 * * ? *)`, `UTC`, reintentos 3/3600 · `get-function-event-invoke-config` → `MaximumRetryAttempts 2`, `OnFailure` → `marketpulse-alertas` · `aws lambda invoke --invocation-type Event` → **`StatusCode 202`** · en el log, una ejecución a las 17:55:13 UTC con `Calidad: 59 comprobaciones, 0 fallan`, `uploaded 0, unchanged 4` (nada había cambiado: idempotencia y Parquet determinista) y `REPORT Duration 554 ms, Billed 555 ms`, **sin `Init Duration`** (arranque en caliente, frente a los 4.160 ms facturados en frío).
  - Nota: el primer `aws logs tail` salió vacío porque se lanzó justo después del `invoke` asíncrono. El evento tarda unos segundos en ejecutarse y en llegar a CloudWatch.
- Paso 3.9 — `infra/monitoring.tf`: una alarma por Lambda (`marketpulse-{ingest,transform}-errores`) sobre `AWS/Lambda` `Errors`, `Sum` ≥ 1 en 1 periodo de 300 s, `treat_missing_data = notBreaching` y `alarm_actions` → tema `marketpulse-alertas` (su política por defecto ya permite publicar a los servicios de la cuenta; comprobado con `get-topic-attributes`). `terraform apply` ejecutado por Alberto → `2 added`.
  - Evidencia: `describe-alarms` → 2 alarmas con 1 acción cada una · simulacro con `aws cloudwatch set-alarm-state --state-value ALARM` en `marketpulse-transform-errores` → historial `INSUFFICIENT_DATA to ALARM` (19:59 hora de España) y **email recibido por Alberto**.
  - No realizado (decisión de Alberto): la prueba de fallo real (bucket inexistente + invocación asíncrona + corrección de la deriva). El destino *on-failure* y los reintentos ante una excepción real **no se han visto funcionar**: solo están comprobados en su configuración (`get-function-event-invoke-config`).
### Problemas encontrados
- **Riesgo para la Fase 6 (encontrado en el paso 3.1):** la SCP del plan gratuito (y también la del plan de pago) incluye `DenyIAMRestrictedActions` con `iam:*Provider*`. Eso deniega `iam:CreateOpenIDConnectProvider`, así que no se podrá crear el proveedor OIDC de GitHub tal y como está planteado. No se resuelve ahora (no se adelantan fases), pero habrá que buscar alternativas al llegar a la Fase 6.
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

## Fase 4 · SQL y modelo analítico en Athena
**Criterios de aceptación:**
- [ ] Las cuatro vistas devuelven resultados coherentes (comprobados a mano con 2-3 cálculos)
- [ ] Ninguna consulta escanea más de unos pocos MB
- [ ] Alberto sabe explicar qué hace cada función ventana

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

## Fase 5 · Infraestructura como código completa
**Criterios de aceptación:**
- [ ] `terraform plan` dice "No changes"
- [ ] El README explica cómo desplegar desde cero
- [ ] Nada se ha creado a mano en la consola sin estar en Terraform

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

## Fase 6 · CI/CD con GitHub Actions
**Criterios de aceptación:**
- [ ] Un pull request con un test roto falla en CI
- [ ] Un merge a `main` despliega sin ninguna clave de AWS guardada en GitHub

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

## Fase 7 · Agente text-to-SQL
**Criterios de aceptación:**
- [ ] Al menos 12 de 15 preguntas correctas
- [ ] Un intento de `DROP TABLE` o de "ignora tus instrucciones" se bloquea y queda registrado
- [ ] La API responde en `localhost` dentro de Docker

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

## Fase 8 · Escaparate
**Criterios de aceptación:**
- [ ] Alguien que no conoce el proyecto puede ejecutarlo siguiendo el README
- [ ] El repositorio es público y no contiene ningún secreto (comprobado con una búsqueda en el historial)

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista
