-- UNICA actualización desde SQL 05. No ejecutar los antiguos 06 y 07.
-- Servidor detenido. Conserva IDs, cantidades, decisiones y reservas existentes.
-- No crea tablas. Si falla, ejecutar ROLLBACK y revisar antes de reintentar.
BEGIN;
DO $$ BEGIN
    IF to_regclass('vacaciones.reservas_por_horas') IS NOT NULL
       OR to_regclass('vacaciones.descuentos_por_horas') IS NOT NULL
       OR to_regclass('vacaciones.ajustes') IS NOT NULL
       OR to_regclass('vacaciones.reintegros') IS NOT NULL THEN
        RAISE EXCEPTION 'Esta actualización parte de SQL 05. Se detectó el diseño anterior 06/07; no se modificó nada.';
    END IF;
END $$;
ALTER TABLE vacaciones.permisos
    ADD COLUMN IF NOT EXISTS total_minutos INTEGER,
    ADD COLUMN IF NOT EXISTS gestionado BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS observacion TEXT,
    ADD COLUMN IF NOT EXISTS fecha_registro TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fecha_cierre TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS id_aprobador BIGINT REFERENCES core.empleados(id_empleado) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS observacion_decision TEXT,
    ADD COLUMN IF NOT EXISTS minutos_restantes_antes INTEGER,
    ADD COLUMN IF NOT EXISTS minutos_restantes_despues INTEGER,
    ADD COLUMN IF NOT EXISTS dias_convertidos INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS uq_permisos_id_empleado
    ON vacaciones.permisos(id_permiso,id_empleado);
CREATE INDEX IF NOT EXISTS idx_permisos_empleado_fecha
    ON vacaciones.permisos(id_empleado,fecha,id_permiso);
CREATE INDEX IF NOT EXISTS idx_permisos_acumulacion
    ON vacaciones.permisos(id_empleado,estado) WHERE gestionado IS TRUE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.permisos'::regclass
                   AND conname='permiso_gestionado_coherente') THEN
        ALTER TABLE vacaciones.permisos ADD CONSTRAINT permiso_gestionado_coherente CHECK (
            NOT gestionado OR (
                id_empleado IS NOT NULL AND fecha IS NOT NULL
                AND hora_inicio IS NOT NULL AND hora_fin IS NOT NULL AND hora_fin > hora_inicio
                AND EXTRACT(SECOND FROM hora_inicio)=0 AND EXTRACT(SECOND FROM hora_fin)=0
                AND total_minutos IS NOT NULL AND total_minutos BETWEEN 1 AND 1439
                AND total_minutos=EXTRACT(EPOCH FROM (hora_fin-hora_inicio))/60
                AND total_horas IS NOT NULL AND total_horas=ROUND(total_minutos::NUMERIC/60,2)
                AND motivo IS NOT NULL AND length(trim(motivo))>0
                AND observacion IS NOT NULL AND observacion='Horas de permiso a cargo a vacaciones'
                AND fecha_registro IS NOT NULL AND estado IS NOT NULL
                AND estado IN ('PENDIENTE','APROBADO','RECHAZADO','CANCELADO','ANULADO')
                AND (
                    (estado='PENDIENTE' AND fecha_cierre IS NULL AND id_aprobador IS NULL
                     AND observacion_decision IS NULL)
                    OR (estado='CANCELADO' AND fecha_cierre IS NOT NULL AND id_aprobador IS NULL
                        AND observacion_decision IS NULL)
                    OR (estado IN ('APROBADO','RECHAZADO','ANULADO') AND fecha_cierre IS NOT NULL
                        AND id_aprobador IS NOT NULL AND observacion_decision IS NOT NULL
                        AND length(trim(observacion_decision))>0)
                )
                AND (
                    (estado IN ('APROBADO','ANULADO') AND minutos_restantes_antes IS NOT NULL
                     AND minutos_restantes_despues IS NOT NULL AND dias_convertidos IS NOT NULL
                     AND minutos_restantes_antes BETWEEN 0 AND 479
                     AND minutos_restantes_despues BETWEEN 0 AND 479
                     AND dias_convertidos BETWEEN 0 AND 3
                     AND minutos_restantes_antes+total_minutos=dias_convertidos*480+minutos_restantes_despues)
                    OR (estado NOT IN ('APROBADO','ANULADO') AND minutos_restantes_antes IS NULL
                        AND minutos_restantes_despues IS NULL AND dias_convertidos IS NULL)
                )
            )
        );
    END IF;
END;
$$;



-- Un solo historial para decisiones y correcciones.
ALTER TABLE vacaciones.aprobaciones
    ADD COLUMN IF NOT EXISTS id_empleado BIGINT,
    ADD COLUMN IF NOT EXISTS id_permiso BIGINT,
    ADD COLUMN IF NOT EXISTS tipo_intervencion VARCHAR(20) NOT NULL DEFAULT 'DECISION',
    ADD COLUMN IF NOT EXISTS id_solicitud_nueva BIGINT,
    ADD COLUMN IF NOT EXISTS id_permiso_nuevo BIGINT,
    ADD COLUMN IF NOT EXISTS antes JSONB,
    ADD COLUMN IF NOT EXISTS despues JSONB;
UPDATE vacaciones.aprobaciones a SET id_empleado=s.id_empleado
FROM vacaciones.solicitudes s
WHERE a.id_solicitud=s.id_solicitud AND a.id_empleado IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_aprobaciones_id_empleado
    ON vacaciones.aprobaciones(id_aprobacion,id_empleado);
CREATE UNIQUE INDEX IF NOT EXISTS uq_intervencion_solicitud
    ON vacaciones.aprobaciones(id_solicitud) WHERE tipo_intervencion IN ('REVERSO','CORRECCION');
CREATE UNIQUE INDEX IF NOT EXISTS uq_intervencion_permiso
    ON vacaciones.aprobaciones(id_permiso) WHERE tipo_intervencion IN ('REVERSO','CORRECCION');
CREATE UNIQUE INDEX IF NOT EXISTS uq_reemplazo_solicitud ON vacaciones.aprobaciones(id_solicitud_nueva);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reemplazo_permiso ON vacaciones.aprobaciones(id_permiso_nuevo);
CREATE INDEX IF NOT EXISTS idx_aprobaciones_empleado ON vacaciones.aprobaciones(id_empleado,id_aprobacion);
CREATE INDEX IF NOT EXISTS idx_aprobaciones_permiso ON vacaciones.aprobaciones(id_permiso);

-- Una sola relación entre documentos y períodos: consumo o devolución.
ALTER TABLE vacaciones.descuentos_por_periodo
    ALTER COLUMN id_solicitud DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS tipo_movimiento VARCHAR(20) NOT NULL DEFAULT 'DESCUENTO',
    ADD COLUMN IF NOT EXISTS id_permiso BIGINT,
    ADD COLUMN IF NOT EXISTS id_descuento_origen BIGINT,
    ADD COLUMN IF NOT EXISTS id_aprobacion BIGINT;
ALTER TABLE vacaciones.descuentos_por_periodo DROP CONSTRAINT IF EXISTS uq_descuento_solicitud_saldo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_consumo_solicitud_saldo ON vacaciones.descuentos_por_periodo(id_solicitud,id_saldo)
    WHERE tipo_movimiento='DESCUENTO';
CREATE UNIQUE INDEX IF NOT EXISTS uq_consumo_permiso_saldo ON vacaciones.descuentos_por_periodo(id_permiso,id_saldo)
    WHERE tipo_movimiento='DESCUENTO';
CREATE UNIQUE INDEX IF NOT EXISTS uq_devolucion_intervencion_origen ON vacaciones.descuentos_por_periodo(id_aprobacion,id_descuento_origen)
    WHERE tipo_movimiento='REINTEGRO';
CREATE UNIQUE INDEX IF NOT EXISTS uq_movimiento_origen ON vacaciones.descuentos_por_periodo(id_descuento,id_saldo,id_empleado);
CREATE INDEX IF NOT EXISTS idx_movimientos_empleado_tipo ON vacaciones.descuentos_por_periodo(id_empleado,tipo_movimiento);
CREATE INDEX IF NOT EXISTS idx_movimientos_origen ON vacaciones.descuentos_por_periodo(id_descuento_origen);

-- Una sola tabla de reservas, con ámbito VACACIONES o HORAS.
ALTER TABLE vacaciones.reservas_por_periodo
    ALTER COLUMN id_solicitud DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS ambito VARCHAR(20) NOT NULL DEFAULT 'VACACIONES',
    ADD COLUMN IF NOT EXISTS id_permiso_cambio BIGINT,
    ADD COLUMN IF NOT EXISTS id_permiso_cierre BIGINT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_comun_horas ON vacaciones.reservas_por_periodo(id_empleado,id_saldo)
    WHERE ambito='HORAS' AND estado='ACTIVA';
CREATE INDEX IF NOT EXISTS idx_reservas_cambio_permiso ON vacaciones.reservas_por_periodo(id_permiso_cambio);
CREATE INDEX IF NOT EXISTS idx_reservas_cierre_permiso ON vacaciones.reservas_por_periodo(id_permiso_cierre);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='fk_aprobacion_id_empleado') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT fk_aprobacion_id_empleado FOREIGN KEY (id_empleado) REFERENCES core.empleados(id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='fk_aprobacion_id_permiso') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT fk_aprobacion_id_permiso FOREIGN KEY (id_permiso,id_empleado) REFERENCES vacaciones.permisos(id_permiso,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='fk_aprobacion_id_solicitud') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT fk_aprobacion_id_solicitud FOREIGN KEY (id_solicitud,id_empleado) REFERENCES vacaciones.solicitudes(id_solicitud,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='fk_aprobacion_id_solicitud_nueva') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT fk_aprobacion_id_solicitud_nueva FOREIGN KEY (id_solicitud_nueva,id_empleado) REFERENCES vacaciones.solicitudes(id_solicitud,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='fk_aprobacion_id_permiso_nuevo') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT fk_aprobacion_id_permiso_nuevo FOREIGN KEY (id_permiso_nuevo,id_empleado) REFERENCES vacaciones.permisos(id_permiso,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='aprobacion_tipo_intervencion') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT aprobacion_tipo_intervencion CHECK (tipo_intervencion IN ('DECISION','REVERSO','CORRECCION'));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='aprobacion_documento_unico') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT aprobacion_documento_unico CHECK (NOT (id_solicitud IS NOT NULL AND id_permiso IS NOT NULL));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.aprobaciones'::regclass AND conname='intervencion_coherente') THEN
        ALTER TABLE vacaciones.aprobaciones ADD CONSTRAINT intervencion_coherente CHECK (
    (tipo_intervencion='DECISION' AND id_solicitud_nueva IS NULL AND id_permiso_nuevo IS NULL)
    OR (tipo_intervencion IN ('REVERSO','CORRECCION')
        AND id_empleado IS NOT NULL AND id_aprobador IS NOT NULL AND fecha IS NOT NULL
        AND observacion IS NOT NULL AND length(trim(observacion))>0
        AND antes IS NOT NULL AND despues IS NOT NULL
        AND (id_solicitud IS NOT NULL OR id_permiso IS NOT NULL)
        AND decision IS NOT NULL
        AND ((tipo_intervencion='REVERSO' AND decision='ANULADA' AND id_solicitud_nueva IS NULL AND id_permiso_nuevo IS NULL)
          OR (tipo_intervencion='CORRECCION' AND decision='CORREGIDA' AND (
            (id_solicitud IS NOT NULL AND id_solicitud_nueva IS NOT NULL AND id_solicitud<>id_solicitud_nueva AND id_permiso_nuevo IS NULL)
             OR (id_permiso IS NOT NULL AND id_permiso_nuevo IS NOT NULL AND id_permiso<>id_permiso_nuevo AND id_solicitud_nueva IS NULL)))))
);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.descuentos_por_periodo'::regclass AND conname='fk_movimiento_permiso') THEN
        ALTER TABLE vacaciones.descuentos_por_periodo ADD CONSTRAINT fk_movimiento_permiso FOREIGN KEY (id_permiso,id_empleado) REFERENCES vacaciones.permisos(id_permiso,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.descuentos_por_periodo'::regclass AND conname='fk_movimiento_intervencion') THEN
        ALTER TABLE vacaciones.descuentos_por_periodo ADD CONSTRAINT fk_movimiento_intervencion FOREIGN KEY (id_aprobacion,id_empleado) REFERENCES vacaciones.aprobaciones(id_aprobacion,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.descuentos_por_periodo'::regclass AND conname='fk_movimiento_origen') THEN
        ALTER TABLE vacaciones.descuentos_por_periodo ADD CONSTRAINT fk_movimiento_origen FOREIGN KEY (id_descuento_origen,id_saldo,id_empleado) REFERENCES vacaciones.descuentos_por_periodo(id_descuento,id_saldo,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.descuentos_por_periodo'::regclass AND conname='movimiento_documento_unico') THEN
        ALTER TABLE vacaciones.descuentos_por_periodo ADD CONSTRAINT movimiento_documento_unico CHECK (
    (id_solicitud IS NOT NULL AND id_permiso IS NULL) OR (id_solicitud IS NULL AND id_permiso IS NOT NULL));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.descuentos_por_periodo'::regclass AND conname='movimiento_tipo_origen') THEN
        ALTER TABLE vacaciones.descuentos_por_periodo ADD CONSTRAINT movimiento_tipo_origen CHECK (
    (tipo_movimiento='DESCUENTO' AND id_descuento_origen IS NULL AND id_aprobacion IS NULL)
    OR (tipo_movimiento='REINTEGRO' AND id_descuento_origen IS NOT NULL
        AND id_descuento_origen<>id_descuento AND id_aprobacion IS NOT NULL));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.reservas_por_periodo'::regclass AND conname='fk_reserva_id_permiso_cambio') THEN
        ALTER TABLE vacaciones.reservas_por_periodo ADD CONSTRAINT fk_reserva_id_permiso_cambio FOREIGN KEY (id_permiso_cambio,id_empleado) REFERENCES vacaciones.permisos(id_permiso,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.reservas_por_periodo'::regclass AND conname='fk_reserva_id_permiso_cierre') THEN
        ALTER TABLE vacaciones.reservas_por_periodo ADD CONSTRAINT fk_reserva_id_permiso_cierre FOREIGN KEY (id_permiso_cierre,id_empleado) REFERENCES vacaciones.permisos(id_permiso,id_empleado) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='vacaciones.reservas_por_periodo'::regclass AND conname='reserva_ambito_coherente') THEN
        ALTER TABLE vacaciones.reservas_por_periodo ADD CONSTRAINT reserva_ambito_coherente CHECK (
    (ambito='VACACIONES' AND id_solicitud IS NOT NULL AND id_permiso_cambio IS NULL AND id_permiso_cierre IS NULL)
    OR (ambito='HORAS' AND id_solicitud IS NULL AND id_permiso_cambio IS NOT NULL
        AND ((estado='ACTIVA' AND id_permiso_cierre IS NULL) OR (estado='LIBERADA' AND id_permiso_cierre IS NOT NULL))));
    END IF;
END $$;

CREATE OR REPLACE FUNCTION vacaciones.validar_origen_reintegro() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE origen vacaciones.descuentos_por_periodo%ROWTYPE;
BEGIN
    IF NEW.tipo_movimiento='REINTEGRO' THEN
        SELECT * INTO origen FROM vacaciones.descuentos_por_periodo WHERE id_descuento=NEW.id_descuento_origen;
        IF NOT FOUND OR origen.tipo_movimiento<>'DESCUENTO'
           OR origen.id_solicitud IS DISTINCT FROM NEW.id_solicitud
           OR origen.id_permiso IS DISTINCT FROM NEW.id_permiso
           OR origen.es_anticipo IS DISTINCT FROM NEW.es_anticipo THEN
            RAISE EXCEPTION 'El reintegro debe referenciar el consumo original y su documento' USING ERRCODE='23514';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM vacaciones.aprobaciones WHERE id_aprobacion=NEW.id_aprobacion
                       AND tipo_intervencion IN ('REVERSO','CORRECCION')) THEN
            RAISE EXCEPTION 'El reintegro requiere una intervención de ajuste' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS comprobar_origen_reintegro ON vacaciones.descuentos_por_periodo;
CREATE TRIGGER comprobar_origen_reintegro BEFORE INSERT OR UPDATE ON vacaciones.descuentos_por_periodo
    FOR EACH ROW EXECUTE FUNCTION vacaciones.validar_origen_reintegro();
COMMIT;
