# Esquema de Vacaciones

Estos scripts instalan o actualizan el esquema `vacaciones`. Antes de aplicarlos
en cualquier otra base, inspecciona el esquema destino, confirma en qué versión
está y respáldalo. No ejecutes la secuencia completa a ciegas.

El backend unificado ya es propietario del esquema `core`; no ejecutes scripts
de otro proyecto que creen o modifiquen tablas `core`.

## Estado de la base local (4 de noviembre de 2026)

En la instancia local `itq_conecta`, las cinco tablas iniciales de Vacaciones
coincidían con `02_vacaciones.sql` y no tenían filas. Se creó y verificó un
respaldo completo antes de ejecutar, en orden, `03_periodos_y_descuentos.sql`,
`04_reservas_y_aprobacion.sql`, `05_periodos_unicos.sql`,
`06_unificacion_desde_05.sql` y `07_apertura_historica.sql`. No se ejecutaron
scripts de Core.

Después de la actualización, las ocho tablas esperadas existen, sus columnas
coinciden con los modelos y las consultas de lectura probadas responden. Esta
nota describe solo la instancia local comprobada; otras instalaciones deben
inspeccionarse antes de elegir una secuencia.

## Instalación o actualización

- `02_vacaciones.sql` solo inicializa el esquema en una base que aún no tiene
  las tablas de Vacaciones. No es una migración y no debe repetirse sobre una
  instalación existente.
- Para una base que ya llegó a `05_periodos_unicos.sql`, el orden indicado por
  el proyecto de origen es `06_unificacion_desde_05.sql` y luego
  `07_apertura_historica.sql`.
- Si `06_unificacion_desde_05.sql` ya se aplicó, ejecuta `07_apertura_historica.sql`
  solo si aún no se aplicó.
- Si no sabes qué scripts se ejecutaron o la estructura difiere, detente y
  compara primero tablas, columnas y datos. No adivines una secuencia.

Todos los scripts deben revisarse y ejecutarse de manera controlada por la
persona responsable de la base de datos. No uses una base de producción para
pruebas. La aplicación requiere las tablas del esquema `vacaciones` descritas
en los modelos y servicios del módulo.
