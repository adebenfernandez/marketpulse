# Glosario de MarketPulse

Cada término tiene una explicación sencilla (con analogía) y otra técnica. Orden alfabético.
Se amplía en cada fase.

| Término | Explicación sencilla | Explicación técnica |
|---|---|---|
| `__main__.py` y `python -m` | La puerta principal de un paquete | `python -m paquete` ejecuta el fichero `__main__.py` de ese paquete. Así se lanza un programa por su nombre de módulo, sin escribir rutas de ficheros |
| `.gitignore` | La lista de "esto no se fotografía" para Git | Fichero de patrones con los ficheros que Git no rastrea. No protege lo que ya se añadió antes |
| API REST | La ventanilla de un servicio: pides por una dirección y te dan una respuesta | Interfaz sobre HTTP: cada recurso tiene una URL y se pide con un verbo (`GET` = leer). La respuesta suele ser JSON |
| ARN (Amazon Resource Name) | La dirección postal completa de un recurso en AWS | Identificador único con el formato `arn:aws:<servicio>:<región>:<cuenta>:<recurso>`. Los servicios globales dejan la región vacía (`budgets::`) |
| Arquitectura bronze / silver / gold | Sin tocar / limpio / listo para analizar | Arquitectura *medallion*: capas de datos por nivel de calidad |
| Athena | Hacer SQL directamente sobre ficheros | Motor SQL *serverless* (Trino) que consulta datos en S3, facturado por datos escaneados |
| AWS | Alquilar ordenadores y servicios de Amazon por internet | Proveedor de nube con servicios gestionados de cómputo, almacenamiento, bases de datos, etc. |
| AWS Budgets | El aviso del banco: "has gastado el 80 % de lo previsto" | Servicio que compara el coste real o previsto con un importe fijado y notifica al superar umbrales. Solo avisa, no detiene nada, y va con horas de retraso |
| AWS Builder ID | Tu perfil personal en AWS | Identidad individual con la que se entra en la "nueva experiencia" de AWS. Es la propietaria de los proyectos |
| AWS CLI | Manejar AWS escribiendo órdenes | Interfaz de línea de comandos de AWS: cada comando ejecuta una acción en el momento (estilo imperativo) |
| Cabecera HTTP (header) | El remite y las instrucciones escritas en el sobre, fuera de la carta | Pares nombre-valor que acompañan a una petición o respuesta (`x-cg-demo-api-key`, `Retry-After`). Es el sitio recomendado para las claves: la URL acaba en logs e historiales |
| Capitalización de mercado | Lo que costaría comprar todas las monedas que existen | Precio × unidades en circulación. Mide el tamaño de un activo |
| CI/CD | Robots que prueban y despliegan cada cambio | Integración y despliegue continuos automatizados |
| CLI (Command Line Interface) | Manejar un programa escribiendo órdenes en lugar de con clics | Interfaz de texto que se puede automatizar en scripts |
| CloudWatch | La caja negra del sistema | Servicio de logs, métricas y alarmas |
| Código de estado HTTP | El semáforo de la respuesta | Número que acompaña a cada respuesta: 2xx bien · 4xx error del cliente (400 mal formada, 401/403 sin permiso, 404 no existe, 429 demasiadas peticiones) · 5xx error del servidor |
| Código de salida (exit code) | El pulgar arriba o abajo que un programa enseña al terminar | Número que un proceso devuelve al sistema operativo: 0 = éxito, cualquier otro = fallo. Lambda, GitHub Actions o un script lo leen para saber si algo fue mal (`$LASTEXITCODE` en PowerShell) |
| Condición (Condition) | La letra pequeña: "puedes entrar, pero solo si…" | Bloque de una política que añade restricciones, como `aws:SourceAccount` o `aws:SourceArn` |
| Confused deputy | Engañar a un ayudante de confianza para que actúe por ti | Ataque en el que un servicio con permisos actúa sobre recursos ajenos. Se evita con condiciones de cuenta u origen |
| Credenciales temporales | Una entrada de concierto válida solo para hoy | Clave de acceso, secreto y *session token* que caducan. Con `aws login` duran 12 h |
| Créditos | Saldo regalado | Descuento que AWS aplica a la factura (100 USD en el plan gratuito). Se excluyen del presupuesto para ver el coste real |
| Cuenta raíz (root user) | La llave maestra del edificio | Identidad con acceso total a la cuenta, que IAM no puede limitar. En la nueva experiencia no se usa |
| Data lake | Un gran almacén de datos en bruto y procesados | Repositorio central de datos en ficheros, normalmente sobre almacenamiento de objetos |
| Dataclass | Una ficha con casillas fijas y con nombre | Clase de Python generada con `@dataclass`; con `frozen=True` es inmutable. Da atributos con nombre en lugar de claves de diccionario |
| Declarativo vs. imperativo | Entregar el plano de la casa vs. dar instrucciones paso a paso | Declarativo: describes el estado final (Terraform). Imperativo: ordenas cada acción (AWS CLI) |
| Dependencia | Una pieza que compras hecha en vez de fabricarla | Paquete externo que necesita el proyecto, declarado en `pyproject.toml` (`requests`, `PyYAML`...) |
| Endpoint | Una ventanilla concreta del servicio | URL de una API que ofrece un recurso concreto (`/v2/rates` = tipos de cambio) |
| Entorno virtual (venv) | Una caja aislada con las librerías de este proyecto | Directorio con su propio intérprete de Python y sus paquetes |
| Escritura atómica | Cambiar un cuadro sin que nadie vea la pared vacía | Escribir en un fichero temporal y renombrarlo encima del final (`os.replace`). Quien lea ve el fichero viejo completo o el nuevo completo, nunca uno a medias |
| Espera exponencial (backoff) | Si el teléfono comunica, llamar a los 1, 2, 4, 8 minutos | Reintentar tras esperas que se duplican, para no saturar un servicio que ya va mal. Se combina con un tope y, si existe, con la cabecera `Retry-After` |
| Etiqueta (tag) | Una pegatina con el nombre del proyecto | Par clave-valor asociado a un recurso. Sirve para buscar, filtrar costes y controlar permisos (`project=marketpulse`) |
| ETL / ELT | Extraer, transformar y cargar datos | Patrones de integración de datos según dónde se transforma |
| Evaluación (evals) | El examen de la IA | Conjunto de casos con respuesta esperada para medir la calidad del sistema |
| EventBridge Scheduler | Un despertador para tu código | Servicio que lanza objetivos según expresiones *cron* o *rate* |
| Fallo parcial | De cinco recados, cuatro hechos y uno pendiente | Cuando una tarea con varias partes falla solo en algunas: se guarda lo que salió bien y se informa de lo que falló (`PartialIngestError`), en vez de perderlo todo o callarlo |
| Fixture (pytest) | Preparar la mesa antes de cada comida | Función marcada con `@pytest.fixture` que prepara algo que los tests piden por su nombre como parámetro (`tmp_path`, `caplog`, `monkeypatch` y las nuestras) |
| Función ventana | Un cálculo que mira filas vecinas | `OVER (PARTITION BY ... ORDER BY ...)`: medias móviles, `LAG`, rankings |
| GitHub Actions | El servicio de robots de GitHub | Plataforma de automatización mediante *workflows* YAML |
| Glue Data Catalog | El índice de la biblioteca | Metastore con las definiciones de tablas sobre ficheros en S3 |
| Guardarraíl | Las barreras de una carretera | Controles que limitan lo que el agente puede hacer |
| IAM | El sistema de llaves y permisos | Servicio de identidades y políticas que controla quién puede hacer qué sobre qué recurso |
| Idempotencia | Hacerlo dos veces da el mismo resultado | Operación cuya repetición no cambia el estado final |
| Instalación editable (`pip install -e`) | Usar el código tal cual está, sin reinstalar | Instala el paquete enlazando a `src/`: los cambios se notan al momento |
| Inyección de dependencias | Pasarle a una máquina la pieza que debe usar, en vez de que la fabrique dentro | Recibir colaboradores (sesión HTTP, función `sleep`) como parámetros. Permite cambiarlos por falsos en los tests |
| Inyección de prompts | Engañar a la IA con instrucciones escondidas | Ataque en el que una entrada intenta anular las instrucciones del sistema |
| JSON | El idioma común de las APIs | Formato de texto para datos (objetos `{}`, listas `[]`, textos, números, `true`/`false`, `null`). En Python se convierte en dict/list |
| Lambda | Código que se ejecuta solo cuando hace falta | Cómputo *serverless* por eventos, facturado por milisegundo |
| Linter | Un corrector ortográfico para código | Herramienta que detecta errores y problemas de estilo sin ejecutar el código (ruff) |
| Logging | El cuaderno de bitácora del programa | Registro de mensajes con nivel (`DEBUG`, `INFO`, `WARNING`, `ERROR`) mediante el módulo `logging`. En AWS acaba en CloudWatch Logs. Nunca debe contener secretos |
| Marca de tiempo UNIX (epoch) | Un cronómetro que empezó el 1/1/1970 | Segundos transcurridos desde el 1 de enero de 1970 a las 00:00 UTC (`1792509891`). Siempre está en UTC |
| MFA | Un segundo código además de la contraseña | Autenticación multifactor. TOTP: código de 6 dígitos que cambia cada 30 s |
| Mínimo privilegio | Dar solo las llaves necesarias | Conceder únicamente las acciones y recursos imprescindibles |
| Mock | Un actor que hace de doble en los ensayos | Objeto falso que imita a uno real (por ejemplo, una sesión HTTP) y devuelve respuestas preparadas. Permite probar sin llamar a internet (`unittest.mock`) |
| Modelo en estrella | Una tabla central de hechos rodeada de tablas descriptivas | Diseño dimensional: tabla de hechos con métricas y dimensiones con atributos |
| Nueva experiencia de AWS | Una versión simplificada de AWS con todo preconfigurado | Modalidad de alta (*Sign up for AWS (new)*): proyectos, Builder ID, región fija y SCP gestionadas por AWS |
| OHLCV | La ficha diaria de un valor en bolsa | Open, High, Low, Close, Volume: precio de apertura, máximo, mínimo, cierre y volumen negociado en una sesión |
| OIDC | Un pase temporal en vez de una llave permanente | Federación de identidad: GitHub obtiene credenciales temporales de AWS sin claves guardadas |
| Orquestador | El director de orquesta: no toca, decide quién toca y cuándo | Código que coordina varias tareas (aquí, las tres fuentes), recoge sus resultados y decide el resultado global |
| Parquet | Un formato de tabla comprimido y rápido de leer | Formato columnar con esquema y compresión; ideal para analítica |
| Partición | Separar los datos en carpetas por fecha | Organización por clave (`dt=2026-10-19`) que permite leer solo lo necesario |
| Particionado estilo Hive | Carpetas con etiqueta `nombre=valor` | Convención de rutas `clave=valor/` (`source=frankfurter/dt=2026-10-20/`). Athena y Glue la reconocen y leen solo las carpetas que pide la consulta |
| Path traversal | Colarse en otra habitación con `../` | Ataque que usa `..` o barras en un nombre para escribir o leer fuera de la carpeta prevista. Se evita validando los nombres con una lista de caracteres permitidos |
| Perfil (profile) | Una tarjeta guardada con nombre | Bloque con nombre en `~/.aws/config` con la región y la forma de obtener credenciales. Se elige con `--profile` |
| Plan gratuito (Free plan) | Una prueba de AWS con saldo regalado | Plan sin cobros con créditos durante 6 meses. Al terminar hay que pasar al plan de pago o la cuenta se cierra |
| Política (policy) | La lista de puertas que abre una tarjeta | Documento JSON que permite o deniega acciones (`servicio:acción`) sobre recursos |
| Política de recurso | La lista de invitados pegada en la puerta de una sala | Política asociada a un recurso (tema SNS, bucket S3) que dice qué *principals* pueden usarlo |
| Principal | Quién llama a la puerta | Entidad que hace una petición: usuario, rol o servicio de AWS (`budgets.amazonaws.com`) |
| Proyecto (nueva experiencia) | Tu espacio de trabajo en AWS | Contenedor con una cuenta de AWS y los ajustes para compartirla con el equipo |
| `pyproject.toml` | La ficha técnica del proyecto | Fichero estándar de configuración de proyectos Python (PEP 621) y de sus herramientas |
| pytest | El examinador que comprueba que el código hace lo que dice | Framework de tests de Python. Ejecuta las funciones `test_*` |
| Región | La ciudad donde están los ordenadores que usas | Ubicación geográfica con varios centros de datos. Este proyecto usa `eu-north-1` (Estocolmo) |
| Rol de IAM | Una tarjeta de acceso temporal que se presta | Identidad sin contraseña cuyas credenciales temporales asume un servicio o usuario (`assumed-role/...`) |
| ruff | Corrector y formateador de código muy rápido | *Linter* y formateador de Python configurado en `pyproject.toml` |
| S3 | Un disco duro infinito en la nube | Almacenamiento de objetos; datos en *buckets* identificados por clave |
| SCP (Service Control Policy) | Una norma del edificio por encima de tu tarjeta | Política de AWS Organizations que fija los permisos máximos. Un `Deny` en una SCP gana a cualquier permiso de IAM |
| Serverless | Sin preocuparte de servidores | Modelo en el que el proveedor gestiona la infraestructura y escala automáticamente |
| SNS (Simple Notification Service) | Una emisora de radio con canales | Servicio *pub/sub*: se publica en un tema y se entrega a cada suscripción |
| State (Terraform) | La memoria de lo que ya está construido | Fichero que mapea la configuración con los recursos reales. No se sube a Git |
| STS (Security Token Service) | La taquilla que emite entradas temporales | Servicio que genera credenciales temporales. `get-caller-identity` responde "¿quién soy?" |
| Suscripción (SNS) | Apuntarse a escuchar un canal | Destino (email, SQS, Lambda…) que recibe una copia de cada mensaje. El email exige confirmación |
| Tema (SNS topic) | El canal de la emisora | Recurso de SNS donde se publican los mensajes. Estándar (admite email) o FIFO |
| Terraform | El plano de la casa que construye la casa | Herramienta de infraestructura como código declarativa |
| Text-to-SQL | Pasar una pregunta en español a una consulta SQL | Generación de SQL con un LLM a partir del lenguaje natural y del esquema |
| Throttling (limitar el ritmo) | Dejar pasar a la gente de una en una en la puerta | Espaciar las peticiones a propósito para no superar el límite por segundo/minuto de una API. Es preventivo: evita el error en vez de reintentarlo |
| Timeout | Colgar si nadie contesta en X segundos | Tiempo máximo de espera de una operación. Sin él, una petición puede quedarse colgada indefinidamente |
| Tipo de cambio de referencia (BCE) | El precio oficial del euro que publica el BCE cada día laborable | Tipo indicativo publicado hacia las 16:00 CET en días hábiles. En fines de semana y festivos no hay publicación nueva: la API devuelve la del último día hábil |
| Umbral (threshold) | La línea que hace saltar la alarma | Porcentaje del importe del presupuesto que dispara una notificación (50/80/100 %) |
| Usuario IAM | Un empleado con su propia tarjeta | Identidad con credenciales a largo plazo. En la nueva experiencia solo sirve para acceso por programa |
| UTC | La hora oficial del mundo, sin horario de verano | Tiempo universal coordinado. Se usa en datos y servidores para que "hoy" sea igual en cualquier país; España es UTC+1 en invierno y UTC+2 en verano |
| Variable de entorno | Una nota pegada en la puerta del programa | Valor con nombre que el sistema operativo le pasa al proceso (`COINGECKO_API_KEY`). Permite dar secretos y configuración sin escribirlos en el código; en local se cargan desde `.env` |
| Versión de una API (v1, v2) | La edición de un manual: la nueva puede cambiar el formato | Prefijo en la URL que permite al proveedor cambiar el formato sin romper a los clientes antiguos. Hay que fijar una versión y vigilar cuándo se declara obsoleta |
| Volatilidad | Cuánto se mueve un precio | Desviación típica de las rentabilidades, a menudo anualizada |
| winget | La tienda de apps de Windows desde la terminal | Gestor de paquetes oficial de Microsoft |
| YAML | Una lista de la compra con sangría | Formato de texto para configuración basado en la indentación. Se lee con `yaml.safe_load`, que solo crea tipos básicos (nunca `yaml.load`, que puede construir objetos arbitrarios) |
