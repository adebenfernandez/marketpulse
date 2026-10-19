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
