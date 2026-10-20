# PROGRESS.md — MarketPulse

**Fase actual:** Fase 1 terminada (2026-10-20)
**Siguiente paso:** Fase 2 · Transformación y data lake en S3 (nueva sesión)

Leyenda: ⬜ pendiente · 🟡 en curso · ✅ terminada

| Fase | Nombre | Estado |
|------|--------|--------|
| 0 | Preparación y seguridad | ✅ |
| 1 | Ingesta en local | ✅ |
| 2 | Transformación y data lake en S3 | ⬜ |
| 3 | Automatización con Lambda y EventBridge | ⬜ |
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
- **Riesgos abiertos:** (1) comprobar que Terraform lee las credenciales de `aws login` (primer `terraform plan`, Fase 2); (2) comprobar que el OIDC de GitHub Actions funciona con las SCP de los proyectos (Fase 6); (3) el plan gratuito termina hacia abril de 2027.

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

- **Riesgos abiertos de esta fase:** (1) crear la clave Demo de CoinGecko antes de la Fase 3 (en Lambda las IP son compartidas); (2) fijar el texto de atribución de CoinGecko y la cita del BCE (Fase 8); (3) los precios de Alpha Vantage no están ajustados por dividendos (Fase 4).

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
- [ ] El bucket tiene acceso público bloqueado y cifrado
- [ ] Existen las tres capas en S3
- [ ] Las comprobaciones de calidad pasan, y fallan con un dato erróneo a propósito en un test

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

## Fase 3 · Automatización con Lambda y EventBridge
**Criterios de aceptación:**
- [ ] Una ejecución manual de la Lambda escribe datos nuevos en S3
- [ ] Los logs se ven en CloudWatch
- [ ] La ejecución programada del día siguiente ha funcionado
- [ ] La política de IAM no usa `*` en recursos

### Pasos completados
### Problemas encontrados
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
