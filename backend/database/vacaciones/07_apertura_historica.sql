-- Ejecutar después de 06_unificacion_desde_05.sql. No crea tablas ni cambia saldos.
BEGIN;
ALTER TABLE vacaciones.saldos ADD COLUMN IF NOT EXISTS apertura_historica JSONB;
CREATE UNIQUE INDEX IF NOT EXISTS uq_apertura_empleado
ON vacaciones.saldos(id_empleado) WHERE apertura_historica IS NOT NULL;
COMMIT;
