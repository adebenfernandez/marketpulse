# PROGRESS.md — MarketPulse

**Fase actual:** Fase 6 · CI/CD (en curso desde 2026-10-22)
**Siguiente paso:** Fase 6, paso 6.2 (revisión de secretos en el historial y primer `git push`, con permiso de Alberto)

Leyenda: ⬜ pendiente · 🟡 en curso · ✅ terminada

| Fase | Nombre | Estado |
|------|--------|--------|
| 0 | Preparación y seguridad | ✅ |
| 1 | Ingesta en local | ✅ |
| 2 | Transformación y data lake en S3 | ✅ |
| 3 | Automatización con Lambda y EventBridge | ✅ |
| 4 | SQL y modelo analítico en Athena | ✅ |
| 5 | Infraestructura como código completa | ✅ |
| 6 | CI/CD con GitHub Actions | 🟡 |
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
- [x] La ejecución programada del día siguiente ha funcionado — 2026-10-21, 06:00 y 06:30 UTC (paso 3.10)
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
- Paso 3.10 — Ejecución programada del 2026-10-21, sin intervención:
  - Ingesta a las 06:00:12 UTC: las 3 APIs en `200`, `failed: {}`, `uploaded: 5`, `REPORT Duration 14376 ms, Init 378 ms`.
  - Transformación a las 06:30:18 UTC: `Calidad: 59 comprobaciones, 0 fallan`, `bronze_downloaded: 10, uploaded: 4`, `REPORT Duration 1648 ms, Billed 3842 ms, Init 2194 ms`.
  - S3: los 5 ficheros de `dt=2026-10-21` (08:00:27 hora de España) y silver y gold reescritos a las 08:30:23.
  - Métricas del día: `Invocations 1` y `Errors 0` en las dos funciones. Alarmas en `OK` (la de transformación volvió sola del simulacro a las 20:00:30 del día 20).
  - Gold leído desde S3: de 305 a **311 filas**. Cripto pasa de 3 a 6 (nueva foto del 21). Bolsa pasa de 300 a 303 (el cierre del 20, que la ejecución local de las 19:27 del día 20 aún no tenía). Divisas sigue en 2 (a las 06:00 UTC el BCE aún no ha publicado el día 21, como se anticipó en la nota del paso 1.7). **Criterio 3 cumplido.**
  - Observación: Frankfurter tardó **7.286 ms** (ayer, 148 ms) y el *timeout* de `HttpClient` es de 10 s. Si se repite, el reintento lo cubriría, pero conviene vigilarlo (riesgo abierto).
### Problemas encontrados
- **Riesgo para la Fase 6 (encontrado en el paso 3.1):** la SCP del plan gratuito (y también la del plan de pago) incluye `DenyIAMRestrictedActions` con `iam:*Provider*`. Eso deniega `iam:CreateOpenIDConnectProvider`, así que no se podrá crear el proveedor OIDC de GitHub tal y como está planteado. No se resuelve ahora (no se adelantan fases), pero habrá que buscar alternativas al llegar a la Fase 6.
- **Riesgos abiertos de esta fase:** (1) Frankfurter tardó 7,3 s el 2026-10-21, con un *timeout* de 10 s (vigilar); (2) los reintentos y el destino *on-failure* no se han visto funcionar ante un fallo real (prueba opcional pendiente); (3) la SCP deniega `iam:*Provider*`, lo que afecta al OIDC de la Fase 6; (4) idea: bajar la memoria de la transformación (usa 238 de 1024 MB), midiendo antes el efecto en la duración.

### Qué ha aprendido Alberto
- Qué es *serverless* y cómo funciona Lambda: *handler*, `event` y `context`, `/tmp` efímero, arranque en frío y en caliente (2,2-2,8 s con pandas frente a 0), y cómo se factura (GB-s, incluido el *init*).
- Empaquetar para otra plataforma: capas, *wheels* `manylinux` para arm64, versiones fijadas y por qué un *build* determinista evita redespliegues innecesarios.
- Secretos en la nube: SSM SecureString con la clave `aws/ssm`, por qué no van en variables de entorno ni en el *state*, y cómo leer una política de KMS con sus condiciones.
- IAM a fondo: rol de ejecución, política de confianza frente a política de permisos, políticas en línea, condiciones (`s3:prefix`, `aws:SourceAccount`), por qué `AWSLambdaBasicExecutionRole` usa `*`, y comprobar permisos con el simulador (y cómo una SCP de región puede engañarlo).
- Orquestación y fiabilidad: EventBridge Scheduler y expresiones cron en UTC, invocación síncrona (200) frente a asíncrona (202), reintentos seguros gracias a la idempotencia, y el destino *on-failure* como alternativa a la DLQ.
- Observabilidad: métricas de Lambda, alarmas con `treat_missing_data` y por qué un fallo debe lanzar una excepción para que se vea.
- Nota: el repaso de preguntas de cierre se saltó a petición de Alberto. Las preguntas rápidas de los pasos se respondieron en el propio paso, sin comprobar su comprensión.

### Cómo contarlo en una entrevista
"Automaticé el *pipeline* con dos funciones Lambda en arm64, programadas cada mañana con EventBridge Scheduler: la ingesta descarga tres APIs y escribe bronze, y media hora después la transformación reconstruye silver y gold y pasa 59 comprobaciones de calidad. Reutilicé el mismo código que ejecutaba en local: el *handler* solo adapta el entorno (claves desde SSM Parameter Store, disco temporal y S3) y lanza una excepción si algo falla, de modo que Lambda reintenta (es seguro porque todo es idempotente), la alarma de CloudWatch me avisa y, si se agotan los reintentos, llega el error por email a través de SNS. Cada función tiene su propio rol con permisos limitados a su prefijo del bucket, sin ningún `*` en recursos, y lo verifiqué con el simulador de IAM. Toda la infraestructura está en Terraform y cuesta prácticamente cero."

### Pregunta típica de entrevista
**P:** Tu Lambda programada falla de madrugada. ¿Cómo te enteras y qué evita que el reintento estropee los datos?
**R:** El *handler* no se traga el error: lanza una excepción, así que Lambda lo cuenta en la métrica `Errors`. Una alarma de CloudWatch sobre esa métrica me manda un email por SNS con el primer fallo. Como la invocación es asíncrona, Lambda reintenta dos veces y, si todo falla, el destino *on-failure* envía el evento con el error concreto. Los reintentos son seguros porque el proceso es idempotente: las rutas en S3 dependen solo de la fuente y la fecha, así que repetir sobrescribe en lugar de duplicar, y la transformación reconstruye silver y gold desde bronze y solo publica si pasan las comprobaciones de calidad.

## Fase 4 · SQL y modelo analítico en Athena
**Criterios de aceptación:**
- [x] Las cuatro vistas devuelven resultados coherentes (comprobados a mano con 2-3 cálculos) — pasos 4.6 a 4.9, más la comparación completa con pandas
- [x] Ninguna consulta escanea más de unos pocos MB — como mucho 43 KB (paso 4.10)
- [x] Alberto sabe explicar qué hace cada función ventana — ronda de 5 preguntas hecha al cerrar la Fase 5 (2026-10-22), ver la nota de abajo

### Pasos completados
- Plan aprobado por Alberto (2026-10-21):
  - *Backfill* único de CoinGecko (365 días) y Frankfurter (1 año); Alpha Vantage se queda en 100 días.
  - Vistas desplegadas con `terraform_data` y un script de Python, sin proveedores nuevos.
  - `dim_asset` generada por la transformación desde `watchlist.yaml`.
  - *Workgroup* con un límite de 100 MB por consulta.
  - Las explicaciones de las funciones ventana son criterio de cierre y no se pueden saltar.
- Paso 4.1 — Precios y documentación oficiales, sin cambios en AWS:
  - **Athena** (Price List API, `eu-north-1`): 5,00 USD por TB escaneado. Las consultas fallidas o canceladas también se cobran. El mínimo de 10 MB por consulta solo aparece explícito para las consultas federadas. Los resultados en S3 se pagan aparte, a precio de S3.
  - **Glue Data Catalog**: 1 USD por cada 100.000 objetos al mes y 1 USD por millón de peticiones, con 1 M de objetos y 1 M de peticiones gratis al mes.
  - **Workgroup**: el límite por consulta va de 10 MB a 7 EB; si se supera, la consulta se **cancela** (y se cobra lo escaneado). AWS recomienda una regla de ciclo de vida para abortar subidas *multipart* incompletas.
  - ***Partition projection***: propiedades `projection.enabled=true` y `projection.year.type=integer` + `range`, y opcionalmente `storage.location.template`. Sin *crawlers* ni `MSCK REPAIR`.
  - **Estimación:** gold ocupa unos 7 KB (unos 50 KB con el *backfill*). Aun cobrando 10 MB por consulta, 1.000 consultas al mes ≈ 10 GB ≈ 0,05 USD.
  - **APIs de historia (llamadas reales):**
    - Frankfurter `GET /v2/rates?from=2025-10-20&to=2026-10-21&providers=ECB` → `200`, 512 filas (256 días hábiles × 2 divisas), 32 KB, **con la misma forma `{date, base, quote, rate}` que la ingesta diaria**: silver lo puede leer sin cambios.
    - CoinGecko `GET /coins/bitcoin/market_chart?days=365&interval=daily` (clave Demo) → `200`, 366 puntos `[timestamp_ms, precio]` a las 00:00 UTC (el último es "ahora"), 37 KB. **Tiene otra forma**: hace falta un lector nuevo en silver.
    - El histórico de CoinGecko marca las 00:00 UTC y la foto diaria se toma hacia las 06:00 UTC. Hay que documentarlo en el modelo.
- Paso 4.2 — *Backfill* (D-022): `ingest/backfill.py` (Frankfurter `from`/`to` en una petición; CoinGecko `/market_chart` 365 días por moneda; fuentes `frankfurter_backfill` y `coingecko_backfill`; sube solo esas carpetas), `frankfurter.validate_rates()` compartida, `silver.crypto_history_rows()` (solo las 00:00 UTC, `change_24h_pct` calculado, la foto diaria gana al histórico). Tests: `129 passed` (8 nuevos). Ejecutado por Claude con la autorización expresa de Alberto ("lo puedes comprobar tú").
  - Evidencia:
    - `build_lambda.py` → 193 ficheros, el mismo SHA-256 en dos construcciones.
    - `terraform apply` → `2 changed` (solo `source_code_hash` de las Lambdas) y después `plan` → `No changes`.
    - `python -m marketpulse.ingest.backfill` → Frankfurter `200`, 510 tipos (255 días); CoinGecko `200`, 366 puntos × 3; `S3: 4 subidos`.
    - `aws lambda invoke marketpulse-transform` → `200`, `{"bronze_downloaded": 14, "uploaded": 6, "unchanged": 1}`, con `Deduplicado` fx 514→510, cripto 1098→1092 y bolsa 600→303, `Calidad: 59 comprobaciones, 0 fallan` y `Gold daily_prices: 1905 filas {'crypto': 1092, 'fx': 510, 'equity': 303}`. Hay particiones `year=2025` nuevas: 6 Parquet subidos y `stock_prices` sin cambios.
  - Problema: el primer `build_lambda.py` generó un zip **sin dependencias**. Las carpetas de `build/deps` se quedaron en "Acceso denegado" (pendientes de borrar, probablemente retenidas por la sincronización de OneDrive) y `shutil.rmtree(..., ignore_errors=True)` ocultó el fallo. El `plan` iba a subir ese zip roto, pero se detectó antes del `apply`. Solución: el trabajo intermedio va a una carpeta temporal del sistema (fuera de OneDrive) y **solo un zip ya verificado** sustituye al anterior (`os.replace`). Las carpetas bloqueadas de `build/deps` quedan como restos inofensivos (ignoradas por Git) hasta que Windows las libere.
- Paso 4.3 — `infra/athena.tf`: ciclo de vida del bucket (regla `borrar-resultados-athena`: prefijo `athena-results/`, expiración a 7 días y aborto de subidas *multipart* a 1 día) y *workgroup* `marketpulse` (`enforce_workgroup_configuration`, límite de 100 MB por consulta, Athena engine v3, resultados en `s3://<bucket>/athena-results/` con SSE-S3, sin métricas en CloudWatch). *Output* `athena_workgroup`. Ejecutado por Claude con la autorización expresa de Alberto → `2 added`.
  - Evidencia: `get-work-group` → límite `104857600`, forzado `true`, `Athena engine version 3`, `SSE_S3` · `get-bucket-lifecycle-configuration` → la regla con `Days: 7` y `DaysAfterInitiation: 1` · `SELECT 1 AS hola` → `SUCCEEDED`, `DataScannedInBytes 0`, 339 ms, resultado `hola 1` en `athena-results/<id>.csv` (+ `.metadata`) · una consulta que pedía guardar el resultado en `s3://otro-bucket-cualquiera/` → también acabó en `athena-results/` (**el *workgroup* manda**).
- Paso 4.4 — `infra/glue.tf`: base de datos `marketpulse` y tabla externa `daily_prices` (Parquet, `ParquetHiveSerDe`, 7 columnas con comentario y el mismo contrato que `schemas.py`, partición `year int` con *projection* `integer` en el rango 2025-2040, sin *crawlers*). `common/athena.py`: `run_query()` (espera asíncrona, error con motivo, para la consulta si tarda más de 120 s, devuelve los bytes escaneados) y la CLI `python -m marketpulse.common.athena "SQL"`. `tests/test_athena.py` (6). `pytest` → `135 passed`. **Alberto autoriza a Claude a ejecutar los `terraform apply` del resto de la Fase 4, enseñando antes el `plan`.** `apply` → `2 added`.
  - Evidencia (consultas reales):
    - Recuento por clase → crypto 1092 (2025-10-23 → 2026-10-21), equity 303 (2026-05-28 → 2026-10-20), fx 510 (2025-10-21 → 2026-10-20): **3.679 bytes**.
    - La misma con `WHERE year = 2025` → crypto 210 y fx 100: **764 bytes** (*partition pruning*).
    - `SELECT *` → 1.905 filas: **22.775 bytes**.
    - `avg(price) WHERE asset = 'BTC'` → 77.933,82: **18.075 bytes**. Lee solo 2 columnas, pero `price` es la que más ocupa (dobles casi sin repetir).
    - `count(*) GROUP BY year` → 2025: 310 y 2026: 1595: **0 bytes** (sale de los metadatos de Parquet, sin leer los datos).
- Paso 4.5 — Modelo en estrella (D-023):
  - `dim_asset`, tabla física escrita por la transformación desde la watchlist (`gold.dim_asset_from`, `write_unpartitioned_table`), con `annualization_days`.
  - Constantes compartidas `PRICE_TYPE`, `SOURCE` y `ANNUALIZATION_DAYS` en `gold.py`.
  - Regla `check_dim_asset`, que incluye la integridad referencial hechos → dimensión.
  - Vistas `sql/views/01_dim_date.sql` y `02_fact_daily_price.sql`.
  - `athena.deploy_views()` / `--deploy-views` / `--file`, la tabla `dim_asset` en `glue.tf` y `views.tf` (`terraform_data` + `local-exec`).
  - Tests: `test_dim_asset.py` (5) y 3 más en `test_athena.py`. `pytest` → `143 passed`.
  - Evidencia:
    - Primer `apply` → la Lambda y `dim_asset` bien, pero las vistas fallaron con `Unsupported Hive type: timestamp(0)`. Al probar `sequence(date, date)` → `FUNCTION_NOT_FOUND`. Tras corregir `dim_date`, segundo `apply` → `Vista desplegada: 01_dim_date.sql / 02_fact_daily_price.sql` (el `terraform_data` *tainted* se recreó; no se borró nada en AWS).
    - `invoke marketpulse-transform` → `Calidad: 69 comprobaciones, 0 fallan` (10 nuevas), `Gold dim_asset: 8 activos`, `uploaded 1`.
    - Consultas: `dim_asset` → 8 filas correctas (833 bytes) · `dim_date` → 659 días, 2025-01-01 → 2026-10-21, 188 de fin de semana (0 bytes) · estrella `fact ⋈ dim_asset ⋈ dim_date` para septiembre de 2026 → crypto 90 filas (30 días × 3), equity 63 (21 sesiones × 3; el día 7 fue Labor Day), fx 44 (22 días hábiles × 2) (19.061 bytes) · hechos sin dimensión → 0.
- Paso 4.6 — `sql/views/03_v_daily_returns.sql`: CTE con `LAG(price)` y `LAG("date")` `OVER (PARTITION BY asset ORDER BY "date")` sobre `fact_daily_price ⋈ dim_asset`; columnas `prev_date`, `prev_price`, `days_since_prev`, `simple_return`, `log_return` y `year`. Se descarta la primera fila de cada activo. Desplegada con `terraform apply` (el `terraform_data` se recrea al cambiar la huella de los `.sql`).
  - Comprobación a mano:
    - SPY 2026-10-19: 766,48 / 763,25 − 1 = **0,004232** y ln = **0,004223** (la vista da lo mismo), con `days_since_prev = 3`: el lunes se compara con el viernes.
    - SPY 2026-10-14: 769,60 / 778,01 − 1 = **−0,010810**.
    - EUR/USD 2026-10-20: 1,1215 / 1,1225 − 1 = **−0,000891**.
    - BTC 2026-10-20: 82.850 / 82.019,58 − 1 = **0,010125**.
  - Recuentos: crypto 1089 = 1092 − 3 primeras filas · equity 300 (237 de 1 día, 54 de 3 por los fines de semana, 9 de 4 por festivos de lunes o viernes) · fx 508 (402 de 1 día, 98 de 3, y de 2, 4 y 5 días por Año Nuevo, el 1 de mayo, Semana Santa y Navidad).
  - Comparación completa con pandas (`groupby(asset).shift(1)`, el equivalente de `LAG`) sobre los Parquet de S3: **1.897 de 1.897 filas emparejadas, diferencia máxima 6,9e-18** (ruido de coma flotante).
  - Limitación visible: el 2026-10-20 BTC compara la foto de las ~17:50 UTC (ejecución manual de la Lambda) con el histórico de las 00:00. No son 24 h exactas (D-022).
- Paso 4.7 — `sql/views/04_v_rolling_volatility_30d.sql`: `COUNT`, `AVG` y `STDDEV_SAMP` de `log_return` `OVER (PARTITION BY asset ORDER BY "date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)`; anualización con `sqrt(dim_asset.annualization_days)`; solo filas con `n_obs = 30`.
  - Resultado del 2026-10-20 (volatilidad anual): SOL 47,9 % · ETH 36,7 % · BTC 32,2 % · QQQ 17,0 % · VT 11,3 % · SPY 10,1 % · EUR/USD 5,1 % · EUR/GBP 3,0 %. El orden es coherente (cripto > tecnología > índice amplio > divisas).
  - Recuentos: 334 días por cripto (363 − 29), 225 por divisa (254 − 29) y 71 por ETF (100 − 29).
  - Comprobación a mano, SPY 2026-10-20: 30 rentabilidades, media 0,000134, varianza muestral (n − 1) 0,00004044 → desviación diaria **0,006359** × √252 = **0,1009** (igual que la vista).
  - Comparación completa con pandas (`rolling(30).std()`, ddof = 1): **1.665 de 1.665 filas, diferencia máxima 1,2e-16**.
  - Pendiente (criterio de cierre): explicación de Alberto de `LAG` y de `STDDEV_SAMP`/`AVG` `OVER` con marco `ROWS`. Las preguntas del 4.6 y del 4.7 se responderán en una ronda al cerrar la fase.
- Paso 4.8 — `sql/views/05_v_correlation_matrix.sql`: últimos 90 días; para CADA pareja, precios cruzados solo en las fechas comunes (*self-join* por fecha), `LAG` dentro de la pareja (`PARTITION BY asset_a, asset_b`) y `corr()`. Salen 64 parejas (diagonal 1, simétrica). Desplegada.
  - Resultado coherente dentro de cada clase: cripto entre sí 0,83-0,89; ETF entre sí 0,89-0,96 (SPY-VT 0,96); EUR/USD-EUR/GBP 0,36. Comparación con pandas por el mismo método: **64 de 64 parejas, diferencia máxima 5,6e-16, mismos `n_obs`**.
  - **Hallazgo:** cripto-bolsa salía ≈ 0 (BTC-SPY −0,03). Hipótesis: desfase horario. El precio cripto de la fecha D es de las 00:00 UTC de D (histórico) o de las ~06:00 UTC de D (foto diaria), así que su rentabilidad mide sobre todo el día D−1; el cierre de SPY de D es de las 20:00 UTC de D. Comprobación: correlacionando la cripto del día siguiente, BTC-SPY pasa de −0,03 a **0,33** y ETH-SPY de −0,13 a **0,26**. **Hipótesis confirmada.** El cálculo es correcto, pero la etiqueta `date` de cripto no significa lo mismo que la de bolsa.
  - **Corrección (opción A, aprobada por Alberto, D-024):** `silver.crypto_close_date()` = (instante − 12 h).date(), así que un precio cripto es del día cuyo cierre de las 00:00 UTC tiene más cerca. Tests actualizados y ampliados con los casos 00:00, 06:00 y 17:50 → `145 passed`. `build` + `apply` (`2 changed`, solo el código de las Lambdas) + `invoke` → `Calidad: 69 comprobaciones, 0 fallan`, `uploaded 4`. Gold cripto: 2025-10-22 → 2026-10-20.
  - Matriz corregida (mismo día): BTC-SPY **0,33**, BTC-QQQ 0,35, BTC-VT 0,37, ETH-SPY 0,26, SOL-SPY 0,34; dentro de cada clase, sin cambios. Desplazando la cripto un día ahora sale ≈ 0 (BTC −0,00, ETH −0,06): **ya no hay desfase**. Las 64 parejas siguen iguales que pandas (diferencia máxima 7,8e-16), y las rentabilidades y la volatilidad también.
- Paso 4.9 — `sql/views/06_v_monthly_summary.sql`: `first_value` / `last_value` `OVER (PARTITION BY asset, date_trunc('month', "date") ORDER BY "date" ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)`, `LEFT JOIN v_daily_returns`, y `GROUP BY` mes con `sessions`, apertura y cierre, mínimo y máximo, `monthly_return = exp(sum(log_return)) − 1`, volatilidad del mes, mejor y peor día, y `month_to_date`.
  - Comprobación a mano: BTC sep-2026 = 83.576,13 / 78.552,78 (cierre de agosto) − 1 = **0,0639** ✔️ · SPY sep-2026 = 762,63 / 767,05 − 1 = **−0,0058** ✔️ · EUR/USD sep-2026 = 1,1355 / 1,1596 − 1 = **−0,0208** ✔️. Sesiones: SPY sep = 21 (Labor Day) y EUR/USD oct = 14 (días hábiles hasta el 20).
  - Recuentos: crypto 39 meses (3 × 13) · equity 18 (3 × 6) · fx 26 (2 × 13). La suma de sesiones coincide con gold (1092/303/510).
  - Trampa demostrada en Athena: `last_value(price) OVER (ORDER BY "date")` sin marco devuelve el precio de cada fila (767,18; 771,35...); con `UNBOUNDED FOLLOWING` devuelve el cierre del mes (762,63) en todas.
  - Comparación con pandas (cierre del mes / cierre del mes anterior − 1): **75 de 75 meses comparables** (los 8 primeros meses no tienen mes anterior), diferencia máxima 6,7e-16; cierres idénticos (diferencia 0,0).
- Paso 4.10 — Bytes escaneados con `SELECT *` (el peor caso) de cada vista: dim_date 0 · dim_asset 833 · fact_daily_price 21.250 · v_daily_returns 21.580 · v_rolling_volatility_30d 21.778 · v_correlation_matrix 37.470 · v_monthly_summary 43.145 → **146.056 bytes en total (0,14 MB)**, con un máximo de 43 KB por consulta frente al límite de 100 MB del *workgroup*. **Criterio 2 cumplido.**
### Problemas encontrados
- Zip de Lambda sin dependencias: `build/deps` bloqueado por OneDrive y `rmtree(ignore_errors=True)` ocultó el fallo. Se detectó antes del `apply`; ahora se construye en una carpeta temporal y solo se sustituye un zip verificado (paso 4.2).
- `dim_date`: `sequence(date, date, interval)` → `timestamp(0)`, que Glue no admite en vistas; `sequence(date, date)` no existe en Athena v3. Se generan *timestamps* y se convierten a fecha en una subconsulta (paso 4.5).
- Correlación cripto-bolsa ≈ 0 por un **desfase horario** en la etiqueta `date` de cripto. Hipótesis confirmada desplazando un día y corregida en silver (D-024, paso 4.8).
- Detalles: un test con una marca de tiempo equivocada (error del test, no del código), un carácter `·` que la consola de Windows no mostraba y un *heredoc* de Bash que no llegó a ejecutarse.
- **Riesgos abiertos de esta fase:** (1) ~~criterio 3 pendiente~~ → cerrado el 2026-10-22; (2) cripto mezcla precios de las 00:00 UTC (histórico) y de las ~06:00 UTC (foto diaria) como "cierre" del día (D-022, D-024); (3) los precios de bolsa no están ajustados por dividendos (D-012); (4) borrar un `.sql` de `sql/views/` no borra la vista (D-023); (5) `terraform apply` necesita el venv activado por el `local-exec` de las vistas; (6) quedan carpetas bloqueadas e inofensivas en `build/deps`.

### Qué ha aprendido Alberto
- Athena y su modelo de coste (bytes escaneados), los *workgroups* con límite y la ubicación forzada de resultados, y el ciclo de vida de S3 para los resultados.
- Glue Data Catalog y tablas externas (*schema-on-read*), *partition projection* frente a *crawlers*, *partition pruning* y la poda de columnas de Parquet (y sus límites: la columna `price` domina).
- Modelado en estrella: tabla de hechos, dimensiones, granularidad, clave natural frente a subrogada e integridad referencial como regla de calidad.
- Vistas SQL desplegadas como código (`terraform_data` + `local-exec`, *tainted*).
- Funciones ventana: `LAG`, ventanas móviles con `ROWS BETWEEN`, `first_value`/`last_value` y la trampa del marco por defecto; rentabilidad simple frente a logarítmica, volatilidad anualizada y correlación de Pearson con fechas alineadas.
- Validar resultados con criterio (no solo que "el SQL funciona"): comprobaciones a mano, comparación fila a fila con pandas y detección de un desfase temporal en los datos.
- **Ronda de funciones ventana (criterio 3, 2026-10-22), con casos nuevos:**
  - P1 (`LAG` con y sin `PARTITION BY`): Alberto pidió la respuesta. Se le explicó (colas separadas del supermercado) y la variante (BTC del lunes → domingo, 1 día frente a 3 de SPY) llegó correcta, pero pegada de otra fuente.
  - P2 (marco `ROWS` recortado y `n_obs = 30`): primero pegada de otra fuente; después respondida por él → "5 filas" y "no sería comparable ni fiable". Correcta.
  - P3 (anualizar y `STDDEV_SAMP`): respuesta pulida, comprobada con una variante que no se podía copiar (activo de 4 días por semana) → "sqrt(208)" y "n − 1 porque es una muestra". Correcta.
  - P4 (trampa de `last_value`): correcta, y la comprobación con `first_value` (principio del marco fijo y final móvil) también.
  - P5 (fechas alineadas en la correlación): correcta (1 día frente a 3; los movimientos de fin de semana de BTC quedan sin pareja).
  - **Valoración honesta:** las cinco ideas están entendidas (P3 y P4, comprobadas con variantes propias). La P1 se resolvió con ayuda. Para repasar antes de una entrevista: explicar `LAG` + `PARTITION BY` en voz alta, sin mirar.

### Cómo contarlo en una entrevista
"Puse SQL encima del data lake con Athena y el Glue Data Catalog: tablas externas sobre Parquet con *partition projection*, sin *crawlers*, y un *workgroup* que corta cualquier consulta de más de 100 MB. Diseñé un modelo en estrella con una dimensión de activos, una de fechas generada y una tabla de hechos, y cuatro vistas analíticas con funciones ventana: rentabilidades con `LAG`, volatilidad móvil anualizada, matriz de correlaciones y resumen mensual. Validé cada vista a mano y fila a fila contra pandas. Al revisar la matriz vi que cripto y bolsa salían incorreladas, sospeché un desfase horario en las fechas, lo confirmé desplazando una serie un día y lo corregí en la capa silver para que todo lo que consume gold heredara el arreglo. La consulta más cara lee 43 KB."

### Pregunta típica de entrevista
**P:** ¿Qué diferencia hay entre una función ventana y un `GROUP BY`?
**R:** `GROUP BY` junta las filas de cada grupo en una sola: de 1.905 precios diarios saco 8 filas, una por activo. Una función ventana calcula sobre un grupo de filas pero **no las junta**: cada fila conserva su detalle y gana una columna nueva, como el precio del día anterior con `LAG` o la volatilidad de las 30 sesiones anteriores con `STDDEV_SAMP OVER (ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)`. `PARTITION BY` decide qué filas forman cada ventana (las del mismo activo), `ORDER BY` su orden y el marco qué parte se mira. Hay que tener cuidado con el marco por defecto: con `ORDER BY` solo llega hasta la fila actual, y por eso `last_value` necesita `UNBOUNDED FOLLOWING`.

## Fase 5 · Infraestructura como código completa
**Criterios de aceptación:**
- [x] `terraform plan` dice "No changes" — pasos 5.2 a 5.7 (también tras importar y refactorizar)
- [x] El README explica cómo desplegar desde cero — paso 5.8 (revisado contra el código, **no** ejecutado en una cuenta vacía)
- [x] Nada se ha creado a mano en la consola sin estar en Terraform — inventario del paso 5.8 (SNS y Budgets importados en el 5.5 y el 5.6)

### Pasos completados
- Plan aprobado por Alberto (2026-10-22): 5.1 inventario · 5.2 deuda técnica (cambio falso del scheduler y venv de las vistas) · 5.3 bucket del *state* (`infra/bootstrap/`) · 5.4 *backend* S3 con `use_lockfile` (sin DynamoDB: su bloqueo está obsoleto según la documentación de HashiCorp) · 5.5 importar SNS · 5.6 importar el presupuesto · 5.7 módulos con `moved` · 5.8 README y nuevo inventario · 5.9 cierre (incluida la ronda de funciones ventana aplazada de la Fase 4).
- Paso 5.1 — Inventario de solo lectura (ejecutado por Claude con permiso de Alberto; cuenta y email ocultos en la salida):
  - `terraform state list` → 29 recursos gestionados + 9 `data`. Todos existen en AWS (`get-resources` por etiqueta, más `list-roles`, `list-schedules`, `get-tables` y `list-work-groups`, porque la API de etiquetas no ve IAM, Scheduler ni las tablas de Glue). El *workgroup* `primary` es de AWS.
  - **Fuera de Terraform:** el tema `marketpulse-alertas` (etiqueta `project`, sin `managed_by`, `DisplayName = MarketPulse`, sin KMS), su política con **2 sentencias** (`__default_statement_ID`, que deja publicar a CloudWatch, y `PermitirBudgetsPublicar`), la suscripción por email confirmada y el presupuesto `marketpulse-mensual` (5 USD, mensual, `UnblendedCost`, sin etiquetas). La CLI lee Budgets sin problemas: la SCP de región no lo bloquea.
  - **Hallazgo 1 — falta la alerta del 100 %:** `describe-notifications-for-budget` y la consola ("Alertas (2)") muestran solo el 50 % y el 80 % reales, las dos hacia SNS. `describe-subscribers-for-notification` del 100 % devuelve el tema (un resto inconsistente de la API). Se recreará con Terraform en el 5.6, con un cambio visible en el *plan*.
  - **Hallazgo 2 — el presupuesto no tiene filtros:** en la respuesta en bruto de `describe-budget` no aparecen ni `FilterExpression`, ni `CostFilters` ni `CostTypes`, y la consola dice "Filtros incluidos: Ninguno". No se cumple lo que dice D-005 ("excluye créditos"). Se decide en el 5.6, tras consultar la documentación del recurso.
  - Esperado: al importar, el *plan* mostrará cambios de etiquetas (`default_tags` añade `managed_by` y `project`).
- Paso 5.2 — Deuda técnica (solo código y `plan`, sin cambios en AWS):
  - **Cambio falso del scheduler, reproducido y corregido.** Antes: con un cambio temporal en la descripción de una Lambda, `plan` → `data.aws_iam_policy_document.scheduler will be read during apply (depends on a resource or a module with changes pending)` y `aws_iam_role_policy.scheduler` con `policy -> (known after apply)` → `2 to change`. Arreglo en `scheduler.tf`: el ARN se construye con `local.region`, `local.account_id` y `local.lambda_functions` en vez de leer `aws_lambda_function.this[*].arn`. Después: `fmt -check` y `validate` correctos · `plan` → `No changes` (el JSON de la política es idéntico) · con el mismo cambio temporal → solo `aws_lambda_function.this["transform"]`, `1 to change`. El cambio temporal se deshizo con `git checkout -- lambda.tf`.
  - **Venv de las vistas:** sin el venv, `python` es el Python 3.13 del sistema y falla con `ModuleNotFoundError: No module named 'marketpulse'`. El fallo es seguro (el `terraform_data` queda *tainted* y el siguiente `apply` lo repite, como en el paso 4.5). Decisión: no cambiar el código y documentarlo en el README (paso 5.8).
- Paso 5.3 — `infra/bootstrap/` (`versions.tf`, `main.tf`, `outputs.tf` y copia del *lock file* para usar el mismo proveedor 6.69.1), con *state* local y `TF_DATA_DIR` propio (`C:\Users\deben\.terraform-data\marketpulse-bootstrap`). Bucket `marketpulse-tfstate-<sufijo>` con `prevent_destroy`, versionado, bloqueo de acceso público, SSE-S3, `BucketOwnerEnforced`, "solo HTTPS" y ciclo de vida (versiones no actuales a 90 días, marcadores de borrado huérfanos, *multipart* a 1 día). `plan` → `7 to add, 0 to change, 0 to destroy`; `terraform apply tfplan` ejecutado por Alberto → `7 added` (el ciclo de vida tardó 57 s: el proveedor espera a que S3 propague la configuración).
  - Evidencia (solo lectura): `get-bucket-versioning` → `Enabled` · `get-public-access-block` → 4 × `True` · `get-bucket-encryption` → `AES256` · `get-bucket-ownership-controls` → `BucketOwnerEnforced` · `get-bucket-lifecycle-configuration` → la regla con `NoncurrentDays 90`, `ExpiredObjectDeleteMarker true` y `DaysAfterInitiation 1` · etiquetas `project`, `managed_by` y `stack=bootstrap` · `aws s3 ls` por HTTPS → vacío y sin error · por `http://` → `AccessDenied ... explicit deny in a resource-based policy` · segundo `plan` → `No changes`.
- Paso 5.4 — *Backend* S3 (D-025): bloque `backend "s3"` en `infra/versions.tf` (`key`, `region`, `encrypt`, `use_lockfile = true`), `infra/backend.hcl` (ignorado) y `backend.hcl.example`. Copia de seguridad previa del *state* local (*serial* 69) en el *scratchpad* de la sesión. `terraform init -migrate-state -backend-config="backend.hcl"` ejecutado por Alberto: `local` → `s3`, respuesta `yes`.
  - Evidencia: `list-object-versions` → `marketpulse/terraform.tfstate` (90.857 bytes) y un `.tflock` ya borrado (marcador de borrado) · *backend* en uso → `"type": "s3"` · `terraform state list` → 38 entradas (29 recursos + 9 `data`) · recursos y *outputs* del *state* remoto idénticos a los del local (comparados como JSON); el remoto empieza en *serial* 1 con otro *lineage* · `infra/terraform.tfstate` queda con 0 bytes y el antiguo pasa a `.backup`.
  - **Prueba del candado:** dos `plan` a la vez. El segundo, con `-lock-timeout=0s` → `Error acquiring the state lock`, `PutObject ... StatusCode: 412 ... PreconditionFailed`, con `Lock Info` (ID, ruta, `OperationTypePlan`, quién y cuándo), código 1. El primero → `No changes`, código 0. Al terminar, el `.tflock` queda borrado.
  - Limpieza (con permiso de Alberto): borrados `infra/terraform.tfstate` (0 bytes), `infra/terraform.tfstate.backup` (*serial* 69) e `infra/tfplan` (de la Fase 4, desactualizado). Después, `plan` → `No changes`: Terraform ya solo usa el *state* de S3.
- Paso 5.5 — Importación de SNS con bloques `import` (no con `terraform import`, para ver el *plan* antes). `sns.tf`: tema (`display_name`, sin KMS, sin `policy` dentro), política con las **dos** sentencias copiadas tal cual (`version = "2008-10-17"`, `policy_id = "__default_policy_ID"`) y suscripción por email con `var.alert_email` (`sensitive`, valor en `terraform.tfvars` ignorado, escrito leyéndolo de AWS sin mostrarlo; plantilla `terraform.tfvars.example`). `imports.tf` temporal, con los ID construidos con región y cuenta. El `data "aws_sns_topic"` desaparece, y `iam.tf`, `lambda.tf` y `monitoring.tf` usan el recurso.
  - Primer *plan*: `5 to change`, tres de ellos falsos (las políticas de `ingest`, `transform` y del tema en *known after apply* porque el tema tenía pendiente la etiqueta `managed_by`). Mismo arreglo que en el 5.2: `local.alertas_topic_arn` construido de antemano. *Plan* final: `3 to import, 0 to add, 2 to change, 0 to destroy` (etiqueta `managed_by` en el tema; `confirmation_timeout_in_minutes` y `endpoint_auto_confirms` solo en el *state*; `endpoint` pasa a sensible, "The value is unchanged"). La política se importa **sin cambios**.
  - `terraform apply tfplan` ejecutado por Alberto. Evidencia: `state list` → `aws_sns_topic.alertas`, `aws_sns_topic_policy.alertas` y `aws_sns_topic_subscription.email` (sin el `data`) · `get-topic-attributes` → `2008-10-17`, `__default_policy_ID`, sentencias `__default_statement_ID` y `PermitirBudgetsPublicar` · etiquetas `managed_by` y `project` · la suscripción conserva su ARN (no se recreó; no llegó un correo de confirmación nuevo) · las 2 alarmas siguen apuntando al tema, en `OK` · `plan` → `No changes`.
  - Incidencia: mi primera comprobación coincidió con el `apply` de Alberto. El `state list` aún mostraba el `data` y el `plan` falló con `Error acquiring the state lock`. El historial de versiones del bucket lo aclaró (candado de 12:11:22 a 12:11:26 UTC y *state* nuevo a las 12:11:26), y al repetir todo cuadró. **El candado protegió el *state* en un caso real.**
- Paso 5.6 — Importación del presupuesto y **corrección de su deriva** (hallazgos del 5.1). `budgets.tf`: `COST`, `"5.0"` `USD`, `MONTHLY`, `metrics = ["UnblendedCost"]`, `billing_view_arn` (la vista principal), `filter_expression { not { dimensions { RECORD_TYPE = ["Credit"] } } }` (con `metrics` no se puede usar `cost_types`, según la documentación del proveedor 6.69.1) y `dynamic "notification"` con 50/80/100 % `ACTUAL` hacia `aws_sns_topic.alertas`. Bloque `import` con `id = "<cuenta>:marketpulse-mensual"`.
  - Primer *plan*: proponía `billing_view_arn -> null` (no esperado) → se declara en el código. *Plan* final: `1 to import, 1 to change, 0 to destroy` (etiquetas, filtro y alerta del 100 %).
  - Primer `apply` (Alberto): importación, filtro y etiquetas aplicados; **error** en la alerta del 100 %: `CreateNotification ... CreationLimitExceededException: one notification can only have 1 subscribers with type of SNS`. Causa probable: el destinatario huérfano visto en el 5.1. Después del error, la API ya no devolvía ese destinatario (AWS parece haberlo limpiado al deshacer la creación; no se puede confirmar). Nuevo *plan* → solo `+ notification 100 %`, `1 to change`. Segundo `apply` (Alberto) → `1 changed`.
  - Evidencia: `describe-notifications-for-budget` → **3 alertas** (50, 80 y 100 %, `ACTUAL`, `OK`), cada una con el tema SNS como único destinatario · `describe-budget` → `FilterExpression` `Not RECORD_TYPE = Credit` · **gasto real del mes: de 0,00 a 0,009 USD** al quitar los créditos (los créditos tapaban el gasto) · etiquetas `managed_by` y `project`.
  - Limpieza (acordada con Alberto): `imports.tf` y `tfplan` borrados. `fmt -check`, `validate` y `plan` → `No changes`.
- Paso 5.7 — Módulos (D-026): `git mv` de los ficheros a `infra/modules/{storage,compute,analytics,monitoring}` (Git los ve como renombrados), cada módulo con `variables.tf`, `outputs.tf` y `versions.tf` (solo el `source` del proveedor; la versión la fija el raíz). El raíz queda en `main.tf` (cuenta, región y las 4 llamadas), `outputs.tf` (mismos nombres que antes) y `moved.tf` (26 bloques). El ciclo de vida de `athena-results/` pasa a `storage` (S3 admite una sola configuración de ciclo de vida por bucket). Los valores que cruzan módulos (ARN del tema, nombres de las Lambdas) son locales construidos, conocidos antes del `apply`. `lambda_zip_path` y `project_root` usan `path.root`, así que las rutas son idénticas y el `terraform_data` de las vistas no se recrea.
  - Evidencia: `init` → `analytics`, `storage`, `monitoring` y `compute` registrados · `fmt -recursive -check` y `validate` correctos · `plan` → **33 `has moved to`** y `0 to add, 0 to change, 0 to destroy`.
  - Primer `apply` de Alberto: no escribió nada (el *state* seguía en *serial* 4, sin direcciones `module.`, y no había ningún candado entre las 12:20 y las 13:02 UTC en el bucket: falló antes de coger el candado). Hipótesis: PowerShell sin `$env:TF_DATA_DIR`. Además, Claude borró ese `tfplan` sin que se hubiera aplicado, así que se regeneró (idéntico). Segundo `apply` con las variables puestas → `0 added, 0 changed, 0 destroyed`.
  - Evidencia final: `state list` → 42 entradas (solo `data.aws_caller_identity` y `data.aws_region` en la raíz; `module.compute` 21, `module.storage` 7, `module.monitoring` 7 y `module.analytics` 5) · *state* en S3 → *serial* 5, escrito a las 13:03:30 UTC · `plan` → **`No changes`**, ya sin ningún *moved* pendiente · `terraform output` → los mismos valores de siempre. `tfplan` borrado.
- Paso 5.8 — README "Desplegar desde cero" (requisitos, venv y `.env`, credenciales y `TF_DATA_DIR`, *bootstrap*, `backend.hcl` y `terraform.tfvars`, `build_lambda.py`, `init -backend-config` + `plan` + `apply`, pasos fuera de Terraform a propósito (confirmar el email de SNS, escribir las claves en SSM, `MARKETPULSE_BUCKET` en `.env`), primera ejecución y cómo desmontarlo).
  - Revisado contra el código: `.env.example` (faltaba crear `.env`), el `backfill` necesita `MARKETPULSE_BUCKET`, `out.json` no estaba ignorado (→ `$env:TEMP`), y `common/athena.py` solo necesita credenciales. La expresión de PowerShell que lee las claves de `.env` se probó en seco: longitudes 27 y 16, iguales a las de SSM (paso 3.5), sin mostrar los valores.
  - **No probado de verdad:** no se ha desplegado en una cuenta vacía (solo hay una cuenta). Es una revisión del orden y de los comandos contra el código, no una ejecución.
  - **Inventario final (solo lectura):** 13 recursos con `project=marketpulse` en la API de etiquetas, **todos con `managed_by=terraform`** (12 de `infra/` y el bucket del *state* con `stack=bootstrap`). Por servicio: 3 roles de IAM, 2 programaciones, 2 tablas + 6 vistas de Glue, 1 presupuesto, 1 tema, 2 buckets, 2 alarmas, 2 grupos de logs, 2 parámetros, 2 Lambdas y el *workgroup* (`primary` es de AWS). Todo aparece en el *state* de `infra/` (26 bloques de recurso) o en el de `infra/bootstrap/` (7). Fuera de Terraform, **a propósito**: los valores de las claves en SSM (D-021), la confirmación del email de SNS y los datos de S3. Las vistas las gestiona el `terraform_data` (D-023).
### Problemas encontrados
- El inventario de la Fase 0 no coincidía con la realidad: la alerta del 100 % y el filtro de créditos no existen (paso 5.1). Lección: una evidencia de consola en el momento de crear algo no garantiza que siga así; el código y el *plan* sí lo vigilan.
- Cambios falsos *known after apply* (pasos 5.2 y 5.5): un `data` que lee un recurso con cambios pendientes se resuelve en el `apply`. Solución: construir los ARN con datos ya conocidos.
- La alerta del 100 % falló con `CreationLimitExceededException` (un solo destinatario SNS por alerta) por un resto huérfano de la API de Budgets. El segundo `apply` funcionó (paso 5.6).
- Comprobaciones que coincidieron con un `apply` de Alberto: el candado del *state* bloqueó el `plan` (paso 5.5). Un `apply` sin `$env:TF_DATA_DIR` no llegó a S3 (paso 5.7). Claude borró un `tfplan` sin aplicar; se regeneró.
- **Riesgos abiertos de esta fase:** (1) el despliegue desde cero está revisado, pero no ejecutado en una cuenta vacía; (2) heredados: venv activado para las vistas (documentado en el README), carpetas bloqueadas en `build/deps` y la SCP que deniega `iam:*Provider*` (Fase 6); (3) el *state* del *bootstrap* es local (si se pierde, se recupera con un `import` del bucket).
### Qué ha aprendido Alberto
- Que IaC no es solo crear: inventariar lo que existe, detectar la deriva (`plan` solo ve lo que está en el *state*) y traer lo manual con bloques `import`, corrigiendo de paso lo que se había desviado (el filtro de créditos y la alerta del 100 %).
- *State* remoto: el problema del huevo y la gallina (*bootstrap*), el versionado como copia de seguridad, el bloqueo nativo de S3 con `use_lockfile` (y por qué DynamoDB ya no hace falta), la configuración parcial del *backend* y `init -migrate-state`.
- Leer un *plan* con criterio: distinguir un cambio real de uno falso (*known after apply*), parar ante un cambio inesperado (`billing_view_arn -> null`) y saber que un `apply` puede quedarse a medias sin romper nada.
- Módulos: variables, *outputs*, direcciones de recursos y `moved` para refactorizar sin destruir (33 recursos movidos y 0 cambios).
- Detalles de seguridad: secretos y datos personales fuera del código (`terraform.tfvars` ignorado, `sensitive`, ARN construidos sin el número de cuenta) y la sentencia por defecto del tema SNS, sin la cual las alarmas se quedarían mudas.
### Cómo contarlo en una entrevista
"Llevé toda la infraestructura del proyecto a Terraform sin parar el servicio. Primero hice un inventario y encontré dos cosas creadas a mano (el tema de alertas y el presupuesto) y una deriva peligrosa: el presupuesto contaba los créditos, así que sus alertas nunca habrían saltado. Las importé con bloques `import`, revisando cada *plan* para que solo cambiara lo que yo quería, y al corregir el filtro el gasto real pasó de 0 a 0,009 USD. Moví el *state* a un bucket versionado con bloqueo nativo de S3 y reorganicé el código en cuatro módulos con bloques `moved`: 33 recursos cambiaron de dirección sin que AWS se enterara. El resultado es un `terraform plan` sin cambios y un README para desplegarlo desde cero."
### Pregunta típica de entrevista
**P:** Tienes recursos creados a mano en la consola y quieres gestionarlos con Terraform. ¿Cómo lo haces sin romper nada?
**R:** Primero un inventario, porque `terraform plan` no ve lo que nunca estuvo en el *state*. Después escribo el código que describe el recurso tal y como existe y añado un bloque `import` con su ID. A diferencia del comando `terraform import`, el bloque pasa por un `plan`, así que veo antes si mi código difiere de la realidad. Busco `0 to destroy` y que los únicos cambios sean los que quiero, como etiquetas o una corrección consciente. Un ejemplo: al importar una política de SNS tuve que copiar también la sentencia por defecto, porque si no, el *plan* la habría borrado y las alarmas de CloudWatch habrían dejado de avisar sin dar error. Cuando el *plan* sale limpio, aplico, compruebo que el siguiente *plan* dice `No changes` y quito los bloques `import`.

## Fase 6 · CI/CD con GitHub Actions
**Criterios de aceptación:**
- [x] Un pull request con un test roto falla en CI — PR #2, *job* de Python en rojo (paso 6.3)
- [ ] Un merge a `main` despliega sin ninguna clave de AWS guardada en GitHub

### Pasos completados
- Plan aprobado por Alberto (2026-10-22), **enfoque A** (D-027): la SCP deniega `iam:*Provider*` (también `list-open-id-connect-providers`), así que no hay OIDC. CI en GitHub Actions y despliegue con CodeBuild + CodeConnections. Pasos: 6.1 precios y documentación · 6.2 revisión de secretos y primer `push` · 6.3 CI y PR con un test roto · 6.4 conexión con GitHub · 6.5 rol de despliegue · 6.6 CodeBuild y `buildspec` con guardia ante *destroy* · 6.7 prueba de extremo a extremo · 6.8 cierre.
- Paso 6.1 — Precios y documentación oficiales, sin cambios: CodeBuild **0,00365 USD/min** en `arm1.small` en Estocolmo (Price List API) con 100 min/mes gratis que no caducan · imágenes AL2023 AArch64 `standard:3.0`/`4.0` con Python 3.13 · CodeConnections disponible en `eu-north-1`, sin cargo propio documentado · GitHub Actions 2.000 min/mes gratis en privados (sin método de pago se bloquea, no se cobra). Permisos que necesita el rol de CodeBuild para la conexión: `codeconnections:GetConnectionToken` y `GetConnection`. Decisión D-027.
- Paso 6.2 — Revisión de secretos en **todo** el historial (10 commits, 113 ficheros distintos), sin herramientas nuevas (`git log --all -p` + un script de Python que solo imprime "aparece/no aparece"):
  - Ficheros sensibles que hayan entrado alguna vez: **ninguno** (solo `.env.example`). Ni `.env`, `tfstate`, `tfvars`, `backend.hcl`, `tfplan`, `data/`, el PDF del informe ni zips.
  - Contenido: **no aparece** el número de cuenta, ningún email, claves de AWS (`AKIA`/`ASIA` o secretos de 40 caracteres), tokens de GitHub ni de Anthropic, claves privadas, el UUID de la suscripción, los nombres completos de los buckets, ARN de sesiones ni el **valor real** de ninguna clave de `.env`.
  - Controles positivos (para comprobar que el escáner funciona): `marketpulse-alertas` → 7 apariciones; `<ID-CUENTA>` → 1; `336392948345` (cuenta pública de AWS que publica la capa de pandas) → 4.
  - **Corrección:** el *push* ya existía. `origin/main` está en `e018f86` (Fase 2), con `update by push` en el *reflog*: Alberto subió las fases 0-2. La nota "todavía sin `git push`" de la Fase 0 estaba desactualizada. Quedan **7 commits** por subir (`3f4d56c` → `67f0eeb`). El repositorio sigue siendo **privado** (la API pública de GitHub responde 404).
  - Commit `e401b50` y `git push` (`e018f86..e401b50`), con permiso de Alberto.
- Paso 6.3 — `.github/workflows/ci.yml` (PR hacia `main` y *push* a `main`, `permissions: contents: read`, `concurrency`, `ubuntu-24.04`, `timeout-minutes: 10`). *Job* `python`: Python 3.13 con caché de pip, `pip install -e ".[dev]"`, `ruff check`, `ruff format --check` y `pytest`. *Job* `terraform`: Terraform 1.16.6, `fmt -check -recursive`, y `init -backend=false -lockfile=readonly` + `validate` en `infra/` e `infra/bootstrap/`. Acciones fijadas por SHA: `actions/checkout` v7.0.1, `actions/setup-python` **v7.0.0** (la v7.1.0 se publicó el mismo día y se descartó por prudencia) y `hashicorp/setup-terraform` v4.0.1, con `persist-credentials: false`.
  - En local, sin `.env` ni perfil de AWS: `145 passed`, ruff y formato correctos.
  - **PR #1** (`fase6/ci`): Python ✅ en 34 s; **Terraform ❌ en 18 s**: `validate` → *"the cached package … does not match any of the checksums recorded in the dependency lock file"*. Causa: el *lock file* solo tenía la huella `h1:` de `windows_amd64`, y con `-lockfile=readonly` Terraform no puede añadir la de Linux. Arreglo: `terraform providers lock -platform=windows_amd64 -platform=linux_amd64 -platform=linux_arm64` en las dos configuraciones (+2 líneas `h1:` cada una, misma versión 6.69.1, `plan` local → `No changes`). Commit `0f898ef` → los dos *jobs* ✅. Fusionado por Alberto con *merge commit* (`e708023`).
  - **PR #2** (`fase6/test-roto`, `assert wl.fx.base == "USD"` a propósito; en local `1 failed, 144 passed` y ruff correcto): **Python ❌ en 28 s** y Terraform ✅ en 26 s. **Criterio 1 cumplido.** El PR se cierra sin fusionar.
  - Protección de `main`: regla creada por Alberto (status checks `Python (ruff + pytest)` y `Terraform (fmt + validate)`), pero GitHub la marca **"Not enforced"**: *"won't be enforced on this private repository until you move to a GitHub Team or Enterprise organization account"*. No se paga nada: se aplicará sola cuando el repositorio sea público (Fase 8). Mitigación mientras tanto: el *buildspec* de CodeBuild repetirá ruff y pytest antes de desplegar (paso 6.6).
- Paso 6.4 — Módulo nuevo `infra/modules/cicd` (el despliegue es otra responsabilidad que el *pipeline* de datos de `compute`) con `aws_codeconnections_connection` "github" (`marketpulse-github`, `provider_type = "GitHub"`; no se usa `aws_codestarconnections_connection`, el nombre antiguo del servicio). Salidas: ARN y `github_connection_status`. `plan` → `1 to add`; `apply` de Alberto → conexión en `PENDING`.
  - *Handshake* hecho por Alberto en la consola (autorizar e instalar *AWS Connector for GitHub*). Evidencia: `aws codeconnections list-connections` → `marketpulse-github AVAILABLE`. El siguiente `plan` solo muestra *"Objects have changed outside of Terraform"* (`connection_status` de `PENDING` a `AVAILABLE`) y un cambio de *output*, sin cambios en AWS. Se guardará en el *state* con el próximo `apply`.
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
