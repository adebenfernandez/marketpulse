# Costes reales de MarketPulse

Medidos el **2026-10-25** (mes en curso: del 1 al 25 de octubre de 2026). Criterio de éxito del
proyecto: **coste real del mes por debajo de 2 €**.

## Resumen

| Concepto | Octubre 2026 (hasta el día 25) | Fuente |
|---|---|---|
| AWS | **0,033 USD** | AWS Budgets, coste sin combinar y **sin contar créditos** |
| API de Claude (Haiku 5.5) | **≈ 0,049 USD** | Registros de auditoría del agente (`logs/`) |
| **Total** | **≈ 0,08 USD ≈ 0,07 €** | Al tipo de referencia del BCE del 23-10-2026 (1 EUR = 1,1193 USD) |

**Criterio cumplido:** 0,07 € frente al límite de 2 € (un 3,5 %). Y eso incluye todo el
desarrollo de las fases 2 a 8, no solo el funcionamiento diario.

Los créditos del plan gratuito no se han tocado en la práctica: quedan **139,97 USD**
(`aws freetier get-account-plan-state`), y el plan termina el 2027-04-19.

## Cómo se ha medido

Solo con llamadas de lectura **gratuitas**:
- `aws budgets describe-budgets`: el gasto del mes según el presupuesto `marketpulse-mensual`.
  Excluye los créditos (D-005), así que es lo que se pagaría sin ellos.
- `aws freetier get-account-plan-state` y `get-free-tier-usage`: los créditos que quedan. La
  segunda devuelve una lista vacía: ningún servicio se acerca a los límites de su capa gratuita.
- Métricas de CloudWatch (`Invocations`, `Duration`, `BucketSizeBytes`, `IncomingBytes`), el
  historial de consultas del *workgroup* de Athena y la duración de los *builds* de CodeBuild.
- Para la API de Claude, la suma de `usage.cost_usd` en `logs/agent_audit.jsonl` y
  `logs/evals_audit.jsonl`. El coste se calcula llamada a llamada con las tarifas oficiales (D-031).

**No se ha usado la API de Cost Explorer**: cobra **0,01 USD por petición** (página oficial de
precios), un tercio de lo que cuesta el proyecto en un mes.

## Uso real por servicio (octubre, hasta el día 25)

La última columna es el coste **si no existiera ninguna capa gratuita**, calculado con los precios
de `eu-north-1` consultados en cada fase (PROGRESS.md, pasos 2.1, 3.1, 4.x y 6.1).

| Servicio | Uso medido | Precio | Sin capa gratuita |
|---|---|---|---|
| Lambda | 18 invocaciones; 68 GB-s de ejecución (más los arranques en frío) | 0,0000133334 USD/GB-s (arm64) | < 0,002 USD |
| S3 | Data lake de 1,8 MB (356 objetos) y *state* de 4,0 MB (163 objetos, con sus versiones) | 0,023 USD/GB-mes, más las peticiones | < 0,01 USD |
| Athena | 190 consultas (179 correctas, 11 fallidas) y 3,2 MB escaneados | 5 USD/TB | ≤ 0,0095 USD, aunque cada consulta se cobrara como 10 MB |
| CloudWatch Logs | 0,42 MB ingeridos (3 grupos, con 14 días de retención) | 0,54 USD/GB | 0,0002 USD |
| Alarmas de CloudWatch | 2 alarmas | 0,10 USD/alarma-mes (10 gratis) | 0,20 USD |
| CodeBuild | 16 *builds*, 16,1 minutos | 0,00365 USD/min en `arm1.small` (100 min/mes gratis) | 0,06 USD |
| Glue Data Catalog, SSM, SNS y KMS | Unas pocas peticiones al día; en el catálogo, 1 base, 2 tablas y 6 vistas | Por debajo de sus capas gratuitas | ≈ 0 USD |

**Lo que no se puede saber sin pagar:** el desglose **oficial** de los 0,033 USD por servicio.
Por el uso medido, lo más probable es que salgan de las peticiones a S3 (escrituras de Athena,
del *state* de Terraform y de las Lambdas) y de Athena, porque las alarmas y CodeBuild están dentro
de su capa gratuita. Se puede confirmar sin coste en la consola, en *Billing → Bills*.

## Proyección de un mes normal (sin desarrollo)

| Concepto | Estimación mensual |
|---|---|
| Lambda (30 ingestas + 30 transformaciones, unos 9 GB-s al día) | ≈ 0,004 USD |
| S3 (unos 10 MB y unos miles de peticiones) | < 0,01 USD |
| Athena (unas 100 consultas del dashboard y del agente) | ≤ 0,005 USD |
| CloudWatch Logs | < 0,001 USD |
| Alarmas y CodeBuild | 0 USD dentro de la capa gratuita (0,20 + 0,04 USD sin ella) |
| API de Claude (unas 100 preguntas a ~0,0015 USD) | ≈ 0,15 USD |
| **Total** | **≈ 0,17 USD/mes (≈ 0,15 €)**, y ≈ 0,41 USD sin ninguna capa gratuita |

Incluso en el peor caso, el proyecto queda **unas 5 veces por debajo** del límite de 2 €.

## API de Claude

| Uso | Preguntas | Llamadas al modelo | Coste |
|---|---|---|---|
| Pruebas del agente (paso 7.7) | 4 | 10 | 0,0030 USD |
| Evaluación: 3 pasadas de 15 preguntas y 6 ataques (paso 7.8) | 63 | 195 | 0,0423 USD |
| Prueba con Docker (paso 7.9) | 2 | — | ≈ 0,002 USD (sin registro: se perdió al parar el contenedor) |
| Dashboard (paso 8.4) | 2 | 6 | 0,0019 USD |
| **Total** | **71** | | **≈ 0,049 USD** |

- Modelo económico (Haiku 5.5) para todo, y caché del *system prompt* y de las herramientas: en
  total, el 77 % de los tokens de entrada se han leído de caché (513.600 de 667.185).
- Una pregunta cuesta entre 0,0004 USD (un ataque rechazado en una sola llamada) y 0,0016 USD (una
  pregunta con 5 llamadas). Una evaluación completa cuesta unos 0,015 USD.
- La cifra oficial está en la consola de Anthropic (*Usage*). La de los registros puede diferir en
  céntimos de céntimo por redondeos.

## Qué mantiene el coste bajo

- **Sin nada encendido por horas:** Lambda, Athena y CodeBuild solo cobran mientras trabajan
  (prohibidos EC2, RDS, NAT Gateway…).
- **Parquet y particiones:** Athena escanea KB en vez de MB.
- **Límites:** el *workgroup* corta las consultas de más de 100 MB, los resultados de Athena se
  borran a los 7 días y los logs a los 14.
- **Arm64 (Graviton)** en Lambda (un 20 % más barato) y en CodeBuild.
- **Presupuesto de 5 USD** con avisos al 50, 80 y 100 % por SNS. Recordatorio: **Budgets avisa,
  pero no corta el gasto**.
- **Modelo económico, caché y registro de tokens** en la API de Claude.
