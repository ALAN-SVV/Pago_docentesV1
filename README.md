# ITQ Conecta — Backend

Este repositorio reúne el backend que he ido desarrollando e integrando para
ITQ Conecta. Está hecho con FastAPI, SQLAlchemy asíncrono y PostgreSQL. Incluye
autenticación y los módulos institucionales de Core, Documentos, Graduación,
Admisiones (CRM), Pagos a Docentes y Vacaciones.

## Módulos y estado actual

| Módulo | Qué incluye | Qué falta o debo mejorar |
|---|---|---|
| Autenticación y Core | Usuarios, roles, permisos, catálogos y acceso con JWT. | Configurar `SECRET_KEY` en el entorno, probar el inicio de sesión completo y definir permisos por rol para cada operación. |
| Documentos | Rutas y modelos para documentos, archivos, versiones y revisiones. | Crear/verificar sus cuatro tablas en la base de desarrollo y probar el flujo completo de archivos y revisiones. |
| Graduación | Eventos, pases y validación por QR o cédula. | Alinear cuatro columnas que faltan en las tablas `graduacion.pases` y `graduacion.qr`, y volver a probar sus rutas con la base. |
| Admisiones (CRM) | Prospectos, responsables, seguimientos, cambios de estado y conversión a aspirantes. | Añadir permisos por rol y comprobar que el responsable de cada acción corresponda al usuario autenticado. |
| Pagos a Docentes | Registro, filtros, estados de pago, historial, resumen y alertas visibles en la API. | Cambiar el identificador de usuario temporal por JWT, añadir permisos por rol y probar las escrituras con usuarios y referencias reales. Los importes siguen siendo manuales. |
| Vacaciones | Solicitudes, saldos, aprobaciones, permisos, feriados e históricos. | Añadir permisos por rol y comprobar la relación entre el usuario autenticado, los empleados y las solicitudes. |
| Celery y correo | La aplicación Celery está preparada para ampliarse. | Implementar las tareas de alertas/correo y configurar y probar Redis; por ahora las tareas de negocio no están terminadas. |

Estos pendientes son parte del trabajo por completar; no significa que todas las
rutas estén listas para exponerse a usuarios finales.

## Ejecutar en Windows

Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
```

Configura `DATABASE_URL` y una `SECRET_KEY` propia en `backend\.env`. No
compartas ese archivo ni lo subas a GitHub. Después, inicia la API:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

La documentación interactiva queda en <http://localhost:8000/api/docs> y el
estado de la API en <http://localhost:8000/api/health>.

## Base de datos

Docker Compose usa `backend/database/pagos_docentes/init.sql` al crear un
volumen vacío. Ese archivo conserva una inicialización antigua del esquema
`financiera`; no prepara por sí solo todos los esquemas que necesita el backend.
Los SQL de Vacaciones son versiones específicas y no se deben ejecutar en
bloque sobre una base existente. Revisa las instrucciones de cada módulo y
compara primero la estructura de la base.

En la base de desarrollo que usé para revisar el backend, faltan las cuatro
tablas del esquema `docs` y cinco catálogos académicos de `core`. También faltan
dos columnas en `graduacion.pases` y dos en `graduacion.qr`. La tabla de
seguimientos de Admisiones sí se creó en esa base. Este estado describe esa
instalación local; revisa cualquier otra base por separado antes de aplicar
cambios.

## Pruebas

Desde `backend/`, ejecuta:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

La suite pasó 135 pruebas en la revisión local. También comprobé la carga de la
aplicación y el registro de 92 rutas en OpenAPI. Esto no sustituye pruebas de
escritura y de flujos completos contra una base de datos de prueba.

Para más detalle sobre la estructura y los pendientes, consulta
[backend/README.md](backend/README.md).
