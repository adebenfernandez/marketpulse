# Glosario de MarketPulse

Cada término tiene una explicación sencilla (con analogía) y otra técnica. Orden alfabético.
Se amplía en cada fase.

| Término | Explicación sencilla | Explicación técnica |
|---|---|---|
| `__main__.py` y `python -m` | La puerta principal de un paquete | `python -m paquete` ejecuta el fichero `__main__.py` de ese paquete. Así se lanza un programa por su nombre de módulo, sin escribir rutas de ficheros |
| `.gitignore` | La lista de "esto no se fotografía" para Git | Fichero de patrones con los ficheros que Git no rastrea. No protege lo que ya se añadió antes |
| ACL (S3) | Un post-it con permisos pegado a cada caja | Sistema antiguo de permisos por objeto en S3. Hoy se desactiva (`BucketOwnerEnforced`) y los permisos se controlan solo con políticas de IAM |
| API REST | La ventanilla de un servicio: pides por una dirección y te dan una respuesta | Interfaz sobre HTTP: cada recurso tiene una URL y se pide con un verbo (`GET` = leer). La respuesta suele ser JSON |
| ARN (Amazon Resource Name) | La dirección postal completa de un recurso en AWS | Identificador único con el formato `arn:aws:<servicio>:<región>:<cuenta>:<recurso>`. Los servicios globales dejan la región vacía (`budgets::`) |
| Arquitectura bronze / silver / gold | Sin tocar / limpio / listo para analizar | Arquitectura *medallion*: capas de datos por nivel de calidad |
| Athena | Hacer SQL directamente sobre ficheros | Motor SQL *serverless* (Trino) que consulta datos en S3, facturado por datos escaneados |
| AWS | Alquilar ordenadores y servicios de Amazon por internet | Proveedor de nube con servicios gestionados de cómputo, almacenamiento, bases de datos, etc. |
| AWS Budgets | El aviso del banco: "has gastado el 80 % de lo previsto" | Servicio que compara el coste real o previsto con un importe fijado y notifica al superar umbrales. Solo avisa, no detiene nada, y va con horas de retraso |
| AWS Builder ID | Tu perfil personal en AWS | Identidad individual con la que se entra en la "nueva experiencia" de AWS. Es la propietaria de los proyectos |
| AWS CLI | Manejar AWS escribiendo órdenes | Interfaz de línea de comandos de AWS: cada comando ejecuta una acción en el momento (estilo imperativo) |
| Bloqueo de acceso público (S3) | Cuatro cerrojos que impiden abrir el trastero a la calle | Ajuste del bucket (`block_public_acls`, `ignore_public_acls`, `block_public_policy`, `restrict_public_buckets`) que impide que se haga público aunque alguien lo intente por error |
| boto3 (SDK de AWS) | El mando a distancia de AWS para Python | Librería oficial para llamar a los servicios de AWS desde código (`client.put_object(...)`). Busca las credenciales igual que la AWS CLI |
| Bucket (S3) | El trastero | Contenedor de objetos en S3, con un nombre único en todo el mundo y en una región concreta |
| Cabecera HTTP (header) | El remite y las instrucciones escritas en el sobre, fuera de la carta | Pares nombre-valor que acompañan a una petición o respuesta (`x-cg-demo-api-key`, `Retry-After`). Es el sitio recomendado para las claves: la URL acaba en logs e historiales |
| Calidad de datos (data quality) | El control de calidad de una fábrica antes de que el producto salga | Reglas automáticas sobre los datos (nulos, duplicados, rangos, coherencia, frescura) que se ejecutan en cada carga y deciden si se publica |
| Capitalización de mercado | Lo que costaría comprar todas las monedas que existen | Precio × unidades en circulación. Mide el tamaño de un activo |
| CI/CD | Robots que prueban y despliegan cada cambio | Integración y despliegue continuos automatizados |
| Cifrado en tránsito (TLS / HTTPS) | Enviar la carta en un sobre cerrado en vez de en una postal | Los datos viajan cifrados entre el cliente y el servidor. En S3 se exige con una política que deniega las peticiones con `aws:SecureTransport = false` |
| CLI (Command Line Interface) | Manejar un programa escribiendo órdenes en lugar de con clics | Interfaz de texto que se puede automatizar en scripts |
| CloudWatch | La caja negra del sistema | Servicio de logs, métricas y alarmas |
| Código de estado HTTP | El semáforo de la respuesta | Número que acompaña a cada respuesta: 2xx bien · 4xx error del cliente (400 mal formada, 401/403 sin permiso, 404 no existe, 429 demasiadas peticiones) · 5xx error del servidor |
| Código de salida (exit code) | El pulgar arriba o abajo que un programa enseña al terminar | Número que un proceso devuelve al sistema operativo: 0 = éxito, cualquier otro = fallo. Lambda, GitHub Actions o un script lo leen para saber si algo fue mal (`$LASTEXITCODE` en PowerShell) |
| Compresión (Snappy) | Envasar al vacío | Parquet comprime cada columna; Snappy es el algoritmo por defecto: rápido, con compresión moderada. Nuestros 3 JSON de Alpha Vantage (54,7 KB) ocupan 14,7 KB en Parquet |
| Condición (Condition) | La letra pequeña: "puedes entrar, pero solo si…" | Bloque de una política que añade restricciones, como `aws:SourceAccount` o `aws:SourceArn` |
| Confused deputy | Engañar a un ayudante de confianza para que actúe por ti | Ataque en el que un servicio con permisos actúa sobre recursos ajenos. Se evita con condiciones de cuenta u origen |
| Credenciales temporales | Una entrada de concierto válida solo para hoy | Clave de acceso, secreto y *session token* que caducan. Con `aws login` duran 12 h |
| Créditos | Saldo regalado | Descuento que AWS aplica a la factura (100 USD en el plan gratuito). Se excluyen del presupuesto para ver el coste real |
| Cuenta raíz (root user) | La llave maestra del edificio | Identidad con acceso total a la cuenta, que IAM no puede limitar. En la nueva experiencia no se usa |
| Data lake | Un gran almacén de datos en bruto y procesados | Repositorio central de datos en ficheros, normalmente sobre almacenamiento de objetos |
| Data source (Terraform) | Consultar algo sin construirlo | Bloque `data "tipo" "nombre"` que lee o calcula información sin crear nada en AWS. `aws_iam_policy_document` genera el JSON de una política a partir de HCL |
| Dataclass | Una ficha con casillas fijas y con nombre | Clase de Python generada con `@dataclass`; con `frozen=True` es inmutable. Da atributos con nombre en lugar de claves de diccionario |
| DataFrame (pandas) | Una hoja de cálculo dentro de Python | Tabla en memoria con columnas con nombre y tipo. Se filtra, ordena y agrupa con código |
| Declarativo vs. imperativo | Entregar el plano de la casa vs. dar instrucciones paso a paso | Declarativo: describes el estado final (Terraform). Imperativo: ordenas cada acción (AWS CLI) |
| Deduplicar | Quitar las fotocopias repetidas de un archivo | Dejar una sola fila por clave (`date`, `symbol`...) eligiendo cuál se queda (aquí: la más reciente) |
| Dependencia | Una pieza que compras hecha en vez de fabricarla | Paquete externo que necesita el proyecto, declarado en `pyproject.toml` (`requests`, `PyYAML`...) |
| `depends_on` (Terraform) | "Primero los cimientos, luego las paredes", dicho en voz alta | Fuerza un orden entre recursos cuando Terraform no puede deducirlo de las referencias |
| Endpoint | Una ventanilla concreta del servicio | URL de una API que ofrece un recurso concreto (`/v2/rates` = tipos de cambio) |
| Entorno virtual (venv) | Una caja aislada con las librerías de este proyecto | Directorio con su propio intérprete de Python y sus paquetes |
| Escritura atómica | Cambiar un cuadro sin que nadie vea la pared vacía | Escribir en un fichero temporal y renombrarlo encima del final (`os.replace`). Quien lea ve el fichero viejo completo o el nuevo completo, nunca uno a medias |
| Espera exponencial (backoff) | Si el teléfono comunica, llamar a los 1, 2, 4, 8 minutos | Reintentar tras esperas que se duplican, para no saturar un servicio que ya va mal. Se combina con un tope y, si existe, con la cabecera `Retry-After` |
| Esquema de datos (schema) | El formulario con las casillas y qué se escribe en cada una | Lista de columnas con su tipo exacto (`date32`, `float64`, `int64`, `timestamp UTC`). Es el contrato de la tabla |
| ETag (S3) | El número de serie de cada caja del trastero | Etiqueta que S3 guarda de cada objeto. Para objetos subidos de una vez y con SSE-S3 es el MD5 del contenido, así que sirve para saber si un fichero ha cambiado |
| Etiqueta (tag) | Una pegatina con el nombre del proyecto | Par clave-valor asociado a un recurso. Sirve para buscar, filtrar costes y controlar permisos (`project=marketpulse`) |
| ETL / ELT | Extraer, transformar y cargar datos | Patrones de integración de datos según dónde se transforma |
| Evaluación (evals) | El examen de la IA | Conjunto de casos con respuesta esperada para medir la calidad del sistema |
| EventBridge Scheduler | Un despertador para tu código | Servicio que lanza objetivos según expresiones *cron* o *rate* |
| Fail fast | Parar la cadena de montaje al ver la primera pieza defectuosa | Detectar el error lo antes posible y detenerse, en lugar de seguir y propagarlo. Aquí: si una regla da ERROR, no se escribe ni silver ni gold |
| Fake (doble de prueba) | Un simulador de vuelo en vez de un avión | Implementación sencilla y funcional de una dependencia (aquí, un S3 en memoria) para los tests. A diferencia de un mock, se comporta de verdad: guarda y lista objetos |
| Fallo parcial | De cinco recados, cuatro hechos y uno pendiente | Cuando una tarea con varias partes falla solo en algunas: se guarda lo que salió bien y se informa de lo que falló (`PartialIngestError`), en vez de perderlo todo o callarlo |
| Falso positivo | La alarma de incendios que salta al tostar pan | Un control que avisa de un problema que no existe. Si son frecuentes, la gente deja de hacer caso a las alertas |
| Fixture (pytest) | Preparar la mesa antes de cada comida | Función marcada con `@pytest.fixture` que prepara algo que los tests piden por su nombre como parámetro (`tmp_path`, `caplog`, `monkeypatch` y las nuestras) |
| Formato columnar | Guardar la agenda por columnas (todos los nombres juntos, todos los teléfonos juntos) | Los valores de cada columna se almacenan juntos: leer 2 de 10 columnas solo lee esas 2, y datos parecidos se comprimen mucho mejor. Es lo contrario que CSV o JSON (por filas) |
| Formato largo / ancho (tabla) | Una lista de la compra (una línea por producto) frente a una cuadrícula con un producto por columna | Largo: una fila por (fecha, activo) y una columna `price`. Ancho: una columna por activo (`btc_price`, `spy_price`...). El largo admite activos nuevos sin cambiar el esquema y es el que mejor encaja con SQL |
| Frescura (freshness) | La fecha de caducidad al revés: cuánto hace que se hizo | Antigüedad del último dato. Si supera un umbral, la carga lleva tiempo fallando aunque nadie lo haya notado |
| Función ventana | Un cálculo que mira filas vecinas | `OVER (PARTITION BY ... ORDER BY ...)`: medias móviles, `LAG`, rankings |
| GB-mes | Pagar el trastero por espacio y por tiempo | Unidad de facturación del almacenamiento: 1 GB guardado durante un mes entero. 1 GB 15 días = 0,5 GB-mes |
| GitHub Actions | El servicio de robots de GitHub | Plataforma de automatización mediante *workflows* YAML |
| Glue Data Catalog | El índice de la biblioteca | Metastore con las definiciones de tablas sobre ficheros en S3 |
| Grafo de dependencias (Terraform) | La lista de "esto antes que aquello" de una obra | Terraform deduce el orden de creación a partir de las referencias entre recursos (`aws_s3_bucket.datalake.id`). Lo que no depende entre sí lo crea en paralelo |
| Guardarraíl | Las barreras de una carretera | Controles que limitan lo que el agente puede hacer |
| Huella / hash (MD5) | La huella dactilar de un fichero | Resumen de tamaño fijo calculado a partir del contenido: si cambia un solo byte, cambia la huella. MD5 sirve para detectar cambios, pero no para seguridad |
| IAM | El sistema de llaves y permisos | Servicio de identidades y políticas que controla quién puede hacer qué sobre qué recurso |
| Idempotencia | Hacerlo dos veces da el mismo resultado | Operación cuya repetición no cambia el estado final |
| Instalación editable (`pip install -e`) | Usar el código tal cual está, sin reinstalar | Instala el paquete enlazando a `src/`: los cambios se notan al momento |
| Inyección de dependencias | Pasarle a una máquina la pieza que debe usar, en vez de que la fabrique dentro | Recibir colaboradores (sesión HTTP, función `sleep`) como parámetros. Permite cambiarlos por falsos en los tests |
| Inyección de prompts | Engañar a la IA con instrucciones escondidas | Ataque en el que una entrada intenta anular las instrucciones del sistema |
| JSON | El idioma común de las APIs | Formato de texto para datos (objetos `{}`, listas `[]`, textos, números, `true`/`false`, `null`). En Python se convierte en dict/list |
| Lambda | Código que se ejecuta solo cuando hace falta | Cómputo *serverless* por eventos, facturado por milisegundo |
| Linaje de datos (lineage) | La etiqueta de "origen" de un alimento | Saber de dónde viene cada dato. Aquí, la columna `ingest_date` dice de qué partición bronze salió cada fila |
| Linter | Un corrector ortográfico para código | Herramienta que detecta errores y problemas de estilo sin ejecutar el código (ruff) |
| Lock file (`.terraform.lock.hcl`) | El tique que dice qué versión exacta compraste | Fichero que `terraform init` crea con la versión exacta y las huellas de cada proveedor. Se sube a Git para que todos usen la misma |
| Logging | El cuaderno de bitácora del programa | Registro de mensajes con nivel (`DEBUG`, `INFO`, `WARNING`, `ERROR`) mediante el módulo `logging`. En AWS acaba en CloudWatch Logs. Nunca debe contener secretos |
| Marca de tiempo UNIX (epoch) | Un cronómetro que empezó el 1/1/1970 | Segundos transcurridos desde el 1 de enero de 1970 a las 00:00 UTC (`1792509891`). Siempre está en UTC |
| MFA | Un segundo código además de la contraseña | Autenticación multifactor. TOTP: código de 6 dígitos que cambia cada 30 s |
| Mínimo privilegio | Dar solo las llaves necesarias | Conceder únicamente las acciones y recursos imprescindibles |
| Mock | Un actor que hace de doble en los ensayos | Objeto falso que imita a uno real (por ejemplo, una sesión HTTP) y devuelve respuestas preparadas. Permite probar sin llamar a internet (`unittest.mock`) |
| Modelo en estrella | Una tabla central de hechos rodeada de tablas descriptivas | Diseño dimensional: tabla de hechos con métricas y dimensiones con atributos |
| Nueva experiencia de AWS | Una versión simplificada de AWS con todo preconfigurado | Modalidad de alta (*Sign up for AWS (new)*): proyectos, Builder ID, región fija y SCP gestionadas por AWS |
| Objeto y prefijo (S3) | La caja y la etiqueta de la estantería | Un objeto es un fichero en S3 con su clave (`bronze/source=x/dt=y/a.json`). S3 no tiene carpetas de verdad: el prefijo es el principio de la clave, y la consola lo muestra como si fueran carpetas |
| OHLCV | La ficha diaria de un valor en bolsa | Open, High, Low, Close, Volume: precio de apertura, máximo, mínimo, cierre y volumen negociado en una sesión |
| OIDC | Un pase temporal en vez de una llave permanente | Federación de identidad: GitHub obtiene credenciales temporales de AWS sin claves guardadas |
| Orquestador | El director de orquesta: no toca, decide quién toca y cuándo | Código que coordina varias tareas (aquí, las tres fuentes), recoge sus resultados y decide el resultado global |
| Paginación (API) | Leer un listín página a página | Las API devuelven las listas largas por trozos (S3: 1.000 objetos por respuesta). El paginador de boto3 pide las páginas siguientes solo |
| Parquet | Un formato de tabla comprimido y rápido de leer | Formato columnar con esquema y compresión; ideal para analítica |
| Partición | Separar los datos en carpetas por fecha | Organización por clave (`dt=2026-10-19`) que permite leer solo lo necesario |
| Particionado estilo Hive | Carpetas con etiqueta `nombre=valor` | Convención de rutas `clave=valor/` (`source=frankfurter/dt=2026-10-20/`). Athena y Glue la reconocen y leen solo las carpetas que pide la consulta |
| Path traversal | Colarse en otra habitación con `../` | Ataque que usa `..` o barras en un nombre para escribir o leer fuera de la carpeta prevista. Se evita validando los nombres con una lista de caracteres permitidos |
| Perfil (profile) | Una tarjeta guardada con nombre | Bloque con nombre en `~/.aws/config` con la región y la forma de obtener credenciales. Se elige con `--profile` |
| Petición PUT / GET (S3) | Dejar o sacar una caja del trastero | Cada operación sobre S3 se cobra aparte: PUT/COPY/POST/LIST (escribir, listar) son más caras que GET (leer) |
| Plan gratuito (Free plan) | Una prueba de AWS con saldo regalado | Plan sin cobros con créditos durante 6 meses. Al terminar hay que pasar al plan de pago o la cuenta se cierra |
| Política (policy) | La lista de puertas que abre una tarjeta | Documento JSON que permite o deniega acciones (`servicio:acción`) sobre recursos |
| Política de recurso | La lista de invitados pegada en la puerta de una sala | Política asociada a un recurso (tema SNS, bucket S3) que dice qué *principals* pueden usarlo |
| Principal | Quién llama a la puerta | Entidad que hace una petición: usuario, rol o servicio de AWS (`budgets.amazonaws.com`) |
| Problema de los ficheros pequeños | Mil sobres con una hoja cada uno | Muchos ficheros diminutos hacen lentas y caras las consultas (Athena abre cada uno). Por eso silver se particiona por año y no por día |
| Provider (Terraform) | El traductor entre Terraform y un servicio | Plugin que sabe crear, leer, cambiar y borrar los recursos de un servicio (`hashicorp/aws`). Se descarga con `terraform init` |
| Proyecto (nueva experiencia) | Tu espacio de trabajo en AWS | Contenedor con una cuenta de AWS y los ajustes para compartirla con el equipo |
| `pyproject.toml` | La ficha técnica del proyecto | Fichero estándar de configuración de proyectos Python (PEP 621) y de sus herramientas |
| pytest | El examinador que comprueba que el código hace lo que dice | Framework de tests de Python. Ejecuta las funciones `test_*` |
| Reconstrucción completa (full refresh) | Volver a montar el puzle entero cada vez | Recalcular la tabla desde todo el origen en cada ejecución. Simple e idempotente; deja de compensar con volúmenes grandes (la alternativa es la carga incremental) |
| Recurso (Terraform) | Cada pieza del plano | Bloque `resource "tipo" "nombre"` que describe una pieza de infraestructura (un bucket, su cifrado...). Se referencia como `tipo.nombre.atributo` |
| Región | La ciudad donde están los ordenadores que usas | Ubicación geográfica con varios centros de datos. Este proyecto usa `eu-north-1` (Estocolmo) |
| Rol de IAM | Una tarjeta de acceso temporal que se presta | Identidad sin contraseña cuyas credenciales temporales asume un servicio o usuario (`assumed-role/...`) |
| ruff | Corrector y formateador de código muy rápido | *Linter* y formateador de Python configurado en `pyproject.toml` |
| S3 | Un disco duro infinito en la nube | Almacenamiento de objetos; datos en *buckets* identificados por clave |
| SCP (Service Control Policy) | Una norma del edificio por encima de tu tarjeta | Política de AWS Organizations que fija los permisos máximos. Un `Deny` en una SCP gana a cualquier permiso de IAM |
| Serverless | Sin preocuparte de servidores | Modelo en el que el proveedor gestiona la infraestructura y escala automáticamente |
| Severidad: error / aviso | Una multa frente a una advertencia del profesor | ERROR: el dato es inaceptable y se para. WARNING (aviso): es sospechoso pero puede ser real (un salto del 30 %); se registra y se sigue |
| snake_case | nombres_en_minúsculas_con_guiones_bajos | Convención de nombres de columnas (`change_24h_pct`). Evita espacios, mayúsculas y comillas en SQL |
| SNS (Simple Notification Service) | Una emisora de radio con canales | Servicio *pub/sub*: se publica en un tema y se entrega a cada suscripción |
| SSE-C | Que cada visitante traiga su propio candado | Cifrado con una clave que el cliente envía en cada petición. AWS lo bloquea por defecto en los buckets nuevos porque se ha usado en ataques de ransomware |
| SSE-S3 (cifrado en reposo) | Una caja fuerte de la que S3 guarda la llave | Cifrado del lado del servidor con claves gestionadas por S3 (AES-256), sin coste extra. SSE-KMS usa claves de KMS y cobra por clave y por petición |
| State (Terraform) | La memoria de lo que ya está construido | Fichero que mapea la configuración con los recursos reales. No se sube a Git |
| STS (Security Token Service) | La taquilla que emite entradas temporales | Servicio que genera credenciales temporales. `get-caller-identity` responde "¿quién soy?" |
| Suscripción (SNS) | Apuntarse a escuchar un canal | Destino (email, SQS, Lambda…) que recibe una copia de cada mensaje. El email exige confirmación |
| Tema (SNS topic) | El canal de la emisora | Recurso de SNS donde se publican los mensajes. Estándar (admite email) o FIFO |
| Terraform | El plano de la casa que construye la casa | Herramienta de infraestructura como código declarativa |
| `terraform plan` / `terraform apply` | El presupuesto del fontanero / hacer la obra | `plan` compara el código con lo que existe y muestra qué haría, sin tocar nada. `apply` lo ejecuta. Con `plan -out=tfplan` y luego `apply tfplan` se aplica exactamente lo revisado |
| Test de regresión | Un candado para que un error ya arreglado no vuelva | Test que reproduce un bug concreto que ya se corrigió, para que, si alguien lo reintroduce, falle |
| Text-to-SQL | Pasar una pregunta en español a una consulta SQL | Generación de SQL con un LLM a partir del lenguaje natural y del esquema |
| `TF_DATA_DIR` | Guardar las herramientas en otro cuarto | Variable de entorno que cambia dónde guarda Terraform su carpeta de trabajo (`.terraform/`, con los proveedores descargados: ~800 MB el de AWS) |
| Throttling (limitar el ritmo) | Dejar pasar a la gente de una en una en la puerta | Espaciar las peticiones a propósito para no superar el límite por segundo/minuto de una API. Es preventivo: evita el error en vez de reintentarlo |
| Timeout | Colgar si nadie contesta en X segundos | Tiempo máximo de espera de una operación. Sin él, una petición puede quedarse colgada indefinidamente |
| Tipo de cambio de referencia (BCE) | El precio oficial del euro que publica el BCE cada día laborable | Tipo indicativo publicado hacia las 16:00 CET en días hábiles. En fines de semana y festivos no hay publicación nueva: la API devuelve la del último día hábil |
| Transferencia de datos (data transfer) | El peaje por sacar cosas del almacén | Lo que se cobra por mover datos: entrar desde internet es gratis; salir a internet se cobra por GB (con 100 GB/mes gratis en total en AWS) |
| Umbral (threshold) | La línea que hace saltar la alarma | Porcentaje del importe del presupuesto que dispara una notificación (50/80/100 %) |
| Usuario IAM | Un empleado con su propia tarjeta | Identidad con credenciales a largo plazo. En la nueva experiencia solo sirve para acceso por programa |
| UTC | La hora oficial del mundo, sin horario de verano | Tiempo universal coordinado. Se usa en datos y servidores para que "hoy" sea igual en cualquier país; España es UTC+1 en invierno y UTC+2 en verano |
| Variable de entorno | Una nota pegada en la puerta del programa | Valor con nombre que el sistema operativo le pasa al proceso (`COINGECKO_API_KEY`). Permite dar secretos y configuración sin escribirlos en el código; en local se cargan desde `.env` |
| Versión de una API (v1, v2) | La edición de un manual: la nueva puede cambiar el formato | Prefijo en la URL que permite al proveedor cambiar el formato sin romper a los clientes antiguos. Hay que fijar una versión y vigilar cuándo se declara obsoleta |
| Volatilidad | Cuánto se mueve un precio | Desviación típica de las rentabilidades, a menudo anualizada |
| winget | La tienda de apps de Windows desde la terminal | Gestor de paquetes oficial de Microsoft |
| YAML | Una lista de la compra con sangría | Formato de texto para configuración basado en la indentación. Se lee con `yaml.safe_load`, que solo crea tipos básicos (nunca `yaml.load`, que puede construir objetos arbitrarios) |
