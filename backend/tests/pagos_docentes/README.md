# Pruebas de Pagos a Docentes

## Importar

En Postman importa estos dos archivos:

- `postman/PagoDocentes.postman_collection.json`
- `postman/PagoDocentes.local.postman_environment.json`

Selecciona el entorno **ITQ Conecta - Pagos docentes (local)**. Inicia el
backend local y ejecuta la carpeta **Smoke tests - solo lectura**. La colección
usa `http://127.0.0.1:8000` por defecto; si el servidor usa otro host o puerto,
cambia `baseUrl` en el entorno.

La colección prueba:

- Resumen, alertas, configuración y lookups.
- Listado paginado y contrato básico de las respuestas.
- Errores esperados para paginación, mes y estado inválidos.
- Control de acceso con bearer inválido (falla conocida: actualmente responde
  200 en vez de 401/403, hasta que el router use JWT).
- Historial inexistente y rechazo 422 de un alta con body incompleto.
- Tiempo de respuesta menor a 3 segundos en las consultas principales.

La solicitud de alta envía un body inválido. Debe detenerse en la validación
422 antes de llegar al servicio y no crea datos.

## Alcance y seguridad actual

Las solicitudes de lectura de pagos están disponibles actualmente sin JWT. Las
escrituras usan un `id_usuario` recibido en query, no la identidad validada por
el backend. Esto es un pendiente importante y significa que el módulo no debe
exponerse a usuarios reales hasta integrar JWT central y permisos por rol.

La colección no incluye cambios de estado exitosos (crear, marcar listo,
aprobar o pagar), porque esas llamadas escriben en PostgreSQL y el backend
apunta a la configuración indicada en `backend/.env`. No las ejecutes contra
la base de trabajo/producción. Para probar el flujo completo, prepara primero
una base desechable de pruebas con sus referencias (docente, período, carrera
y usuario), configura el backend para usar únicamente esa base y respalda o
elimina su contenido al finalizar.

En la revisión local se enviaron solicitudes HTTP de solo lectura y de
validación negativa al backend que estaba corriendo: resumen, alertas,
configuración, lookups, lista filtrada, parámetros inválidos y body incompleto.
De las 11 solicitudes comprobadas, 10 dieron el resultado esperado. La prueba
de bearer inválido es la única que falla: el GET devuelve 200 en vez de 401/403.
El historial inexistente devolvió 404 y la creación inválida devolvió 422; se
comparó el total de pagos antes y después y no cambió.

Estas solicitudes se ejecutaron directamente contra el backend local, no desde
la aplicación Postman/Newman. El JSON de la colección y el entorno, además de
la sintaxis de sus scripts JavaScript, se validaron localmente. Importa los
archivos y ejecuta la colección en Postman para guardar el reporte de esa
herramienta. Las pruebas Postman no sustituyen autorización ni pruebas de
concurrencia.

## Pruebas automatizadas

`test_pagos_docentes_schemas.py` valida contratos Pydantic: IDs positivos,
fechas, estados iniciales, montos, umbrales, unidades y correo. Desde `backend/`:

```powershell
python -m pytest tests/pagos_docentes/test_pagos_docentes_schemas.py -q
```

## Pendientes para recordar

- Integrar JWT en todas las rutas de Pagos a Docentes y rechazar tokens inválidos.
- Tomar el usuario autenticado del JWT en lugar de confiar en `id_usuario` enviado
  por el cliente; aplicar permisos por rol.
- Ejecutar la colección en Postman/Newman y guardar el reporte.
- Probar las escrituras y transiciones de estado en una base desechable aislada,
  nunca en la base de trabajo o producción.
- Ejecutar las pruebas Python con un intérprete/entorno virtual autorizado.
