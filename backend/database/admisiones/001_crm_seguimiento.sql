-- Tabla de seguimiento de interacciones del CRM (RF-CRM-03)
-- Propuesta del documento de requerimientos de Admisiones, seccion 7.3

CREATE TABLE admision.crm_seguimiento (
    id_seguimiento BIGSERIAL PRIMARY KEY,
    id_crm BIGINT REFERENCES admision.crm(id_crm),
    id_responsable BIGINT REFERENCES core.empleados(id_empleado),
    tipo_contacto VARCHAR(50),
    descripcion TEXT,
    resultado VARCHAR(100),
    proxima_accion TEXT,
    fecha_proxima_accion DATE,
    fecha_registro TIMESTAMP
);
