# Base de datos de Admisiones

`001_crm_seguimiento.sql` es el script original del módulo CRM. Crea la tabla
`admision.crm_seguimiento` y requiere que ya existan `admision.crm` y
`core.empleados`.

La tabla se creó en la base local de desarrollo y se verificó. Antes de
ejecutarlo en otra base, comprueba que la tabla no exista; el SQL original no
incluye `IF NOT EXISTS`. Revisa también que las tablas referenciadas existan y
haz un respaldo antes de aplicar DDL.

El backend expone el módulo bajo `/api/v1/admision` y requiere un JWT válido.
Todavía falta autorización específica por rol y comprobar que el responsable
de cada operación corresponda al usuario autenticado.
