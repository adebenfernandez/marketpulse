# Glosario de MarketPulse

Cada término tiene una explicación sencilla (con analogía) y otra técnica. Orden alfabético.
Se amplía en cada fase.

| Término | Explicación sencilla | Explicación técnica |
|---|---|---|
| `.gitignore` | La lista de "esto no se fotografía" para Git | Fichero de patrones con los ficheros que Git no rastrea. No protege lo que ya se añadió antes |
| Arquitectura bronze / silver / gold | Sin tocar / limpio / listo para analizar | Arquitectura *medallion*: capas de datos por nivel de calidad |
| ARN (Amazon Resource Name) | La dirección postal completa de un recurso en AWS | Identificador único con el formato `arn:aws:<servicio>:<región>:<cuenta>:<recurso>`. Los servicios globales dejan la región vacía (`budgets::`) |
| Athena | Hacer SQL directamente sobre ficheros | Motor SQL *serverless* (Trino) que consulta datos en S3, facturado por datos escaneados |
| AWS | Alquilar ordenadores y servicios de Amazon por internet | Proveedor de nube con servicios gestionados de cómputo, almacenamiento, bases de datos, etc. |
| AWS Budgets | El aviso del banco: "has gastado el 80 % de lo previsto" | Servicio que compara el coste real o previsto con un importe fijado y notifica al superar umbrales. Solo avisa, no detiene nada, y va con horas de retraso |
| AWS Builder ID | Tu perfil personal en AWS | Identidad individual con la que se entra en la "nueva experiencia" de AWS. Es la propietaria de los proyectos |
| AWS CLI | Manejar AWS escribiendo órdenes | Interfaz de línea de comandos de AWS: cada comando ejecuta una acción en el momento (estilo imperativo) |
| CI/CD | Robots que prueban y despliegan cada cambio | Integración y despliegue continuos automatizados |
| CLI (Command Line Interface) | Manejar un programa escribiendo órdenes en lugar de con clics | Interfaz de texto que se puede automatizar en scripts |
| CloudWatch | La caja negra del sistema | Servicio de logs, métricas y alarmas |
| Condición (Condition) | La letra pequeña: "puedes entrar, pero solo si…" | Bloque de una política que añade restricciones, como `aws:SourceAccount` o `aws:SourceArn` |
| Confused deputy | Engañar a un ayudante de confianza para que actúe por ti | Ataque en el que un servicio con permisos actúa sobre recursos ajenos. Se evita con condiciones de cuenta u origen |
| Créditos | Saldo regalado | Descuento que AWS aplica a la factura (100 USD en el plan gratuito). Se excluyen del presupuesto para ver el coste real |
| Credenciales temporales | Una entrada de concierto válida solo para hoy | Clave de acceso, secreto y *session token* que caducan. Con `aws login` duran 12 h |
| Cuenta raíz (root user) | La llave maestra del edificio | Identidad con acceso total a la cuenta, que IAM no puede limitar. En la nueva experiencia no se usa |
| Data lake | Un gran almacén de datos en bruto y procesados | Repositorio central de datos en ficheros, normalmente sobre almacenamiento de objetos |
| Declarativo vs. imperativo | Entregar el plano de la casa vs. dar instrucciones paso a paso | Declarativo: describes el estado final (Terraform). Imperativo: ordenas cada acción (AWS CLI) |
| Entorno virtual (venv) | Una caja aislada con las librerías de este proyecto | Directorio con su propio intérprete de Python y sus paquetes |
| Etiqueta (tag) | Una pegatina con el nombre del proyecto | Par clave-valor asociado a un recurso. Sirve para buscar, filtrar costes y controlar permisos (`project=marketpulse`) |
| ETL / ELT | Extraer, transformar y cargar datos | Patrones de integración de datos según dónde se transforma |
| EventBridge Scheduler | Un despertador para tu código | Servicio que lanza objetivos según expresiones *cron* o *rate* |
| Evaluación (evals) | El examen de la IA | Conjunto de casos con respuesta esperada para medir la calidad del sistema |
| Función ventana | Un cálculo que mira filas vecinas | `OVER (PARTITION BY ... ORDER BY ...)`: medias móviles, `LAG`, rankings |
| GitHub Actions | El servicio de robots de GitHub | Plataforma de automatización mediante *workflows* YAML |
| Glue Data Catalog | El índice de la biblioteca | Metastore con las definiciones de tablas sobre ficheros en S3 |
| Guardarraíl | Las barreras de una carretera | Controles que limitan lo que el agente puede hacer |
| IAM | El sistema de llaves y permisos | Servicio de identidades y políticas que controla quién puede hacer qué sobre qué recurso |
| Idempotencia | Hacerlo dos veces da el mismo resultado | Operación cuya repetición no cambia el estado final |
| Instalación editable (`pip install -e`) | Usar el código tal cual está, sin reinstalar | Instala el paquete enlazando a `src/`: los cambios se notan al momento |
| Inyección de prompts | Engañar a la IA con instrucciones escondidas | Ataque en el que una entrada intenta anular las instrucciones del sistema |
| Lambda | Código que se ejecuta solo cuando hace falta | Cómputo *serverless* por eventos, facturado por milisegundo |
| Linter | Un corrector ortográfico para código | Herramienta que detecta errores y problemas de estilo sin ejecutar el código (ruff) |
| MFA | Un segundo código además de la contraseña | Autenticación multifactor. TOTP: código de 6 dígitos que cambia cada 30 s |
| Mínimo privilegio | Dar solo las llaves necesarias | Conceder únicamente las acciones y recursos imprescindibles |
| Modelo en estrella | Una tabla central de hechos rodeada de tablas descriptivas | Diseño dimensional: tabla de hechos con métricas y dimensiones con atributos |
| Nueva experiencia de AWS | Una versión simplificada de AWS con todo preconfigurado | Modalidad de alta (*Sign up for AWS (new)*): proyectos, Builder ID, región fija y SCP gestionadas por AWS |
| OIDC | Un pase temporal en vez de una llave permanente | Federación de identidad: GitHub obtiene credenciales temporales de AWS sin claves guardadas |
| Parquet | Un formato de tabla comprimido y rápido de leer | Formato columnar con esquema y compresión; ideal para analítica |
| Partición | Separar los datos en carpetas por fecha | Organización por clave (`dt=2026-10-19`) que permite leer solo lo necesario |
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
| Umbral (threshold) | La línea que hace saltar la alarma | Porcentaje del importe del presupuesto que dispara una notificación (50/80/100 %) |
| Usuario IAM | Un empleado con su propia tarjeta | Identidad con credenciales a largo plazo. En la nueva experiencia solo sirve para acceso por programa |
| Volatilidad | Cuánto se mueve un precio | Desviación típica de las rentabilidades, a menudo anualizada |
| winget | La tienda de apps de Windows desde la terminal | Gestor de paquetes oficial de Microsoft |
