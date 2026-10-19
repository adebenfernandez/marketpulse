# PROGRESS.md — MarketPulse

**Fase actual:** Fase 0 terminada (2026-10-20)
**Siguiente paso:** Fase 1 · Ingesta en local (nueva sesión)

Leyenda: ⬜ pendiente · 🟡 en curso · ✅ terminada

| Fase | Nombre | Estado |
|------|--------|--------|
| 0 | Preparación y seguridad | ✅ |
| 1 | Ingesta en local | ⬜ |
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
- [ ] `python -m marketpulse.ingest` genera ficheros para todas las fuentes
- [ ] Ejecutarlo dos veces el mismo día no duplica datos
- [ ] `pytest` pasa
- [ ] `ruff check` sin errores

### Pasos completados
### Problemas encontrados
### Qué ha aprendido Alberto
### Cómo contarlo en una entrevista
### Pregunta típica de entrevista

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
