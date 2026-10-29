-- ============================================================
-- 1. CORE INSTITUCIONAL
-- ============================================================

CREATE SCHEMA core;


-- PERSONAS
CREATE TABLE core.personas (
    id_persona BIGSERIAL PRIMARY KEY,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    apellidos VARCHAR(100),
    correo VARCHAR(150),
    telefono VARCHAR(20),
    fecha_nacimiento DATE,
    direccion TEXT,
    estado BOOLEAN
);


-- USUARIOS
CREATE TABLE core.usuarios (
    id_usuario BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES core.personas(id_persona),
    nombre_usuario VARCHAR(100),
    correo_institucional VARCHAR(150),
    contrasena_hash TEXT,
    estado BOOLEAN,
    fecha_creacion TIMESTAMP
);


-- ROLES
CREATE TABLE core.roles (
    id_rol BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    descripcion TEXT,
    estado BOOLEAN
);


-- PERMISOS
CREATE TABLE core.permisos (
    id_permiso BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    descripcion TEXT,
    accion VARCHAR(100),
    estado BOOLEAN
);


-- MODULOS
CREATE TABLE core.modulos (
    id_modulo BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    descripcion TEXT,
    estado BOOLEAN
);


-- DEPARTAMENTOS / UNIDADES
CREATE TABLE core.unidades (
    id_unidad BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(150),
    descripcion TEXT,
    estado BOOLEAN
);


-- ESTUDIANTES
CREATE TABLE core.estudiantes (
    id_estudiante BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES core.personas(id_persona),
    codigo_estudiante VARCHAR(50),
    estado BOOLEAN
);


-- EMPLEADOS
CREATE TABLE core.empleados (
    id_empleado BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES core.personas(id_persona),
    id_unidad BIGINT REFERENCES core.unidades(id_unidad),
    codigo_empleado VARCHAR(50),
    cargo VARCHAR(100),
    fecha_ingreso DATE,
    estado BOOLEAN
);


-- CATALOGOS ACADEMICOS
CREATE TABLE core.catalogos_academicos (
    id_catalogo BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(100),
    codigo VARCHAR(50),
    nombre VARCHAR(150),
    descripcion TEXT,
    estado BOOLEAN
);


-- AUDITORIA
CREATE TABLE core.auditoria (
    id_auditoria BIGSERIAL PRIMARY KEY,
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    modulo VARCHAR(100),
    accion VARCHAR(100),
    tabla_afectada VARCHAR(100),
    id_registro BIGINT,
    fecha_hora TIMESTAMP,
    direccion_ip VARCHAR(50)
);

-- ============================================================
-- TABLA INTERMEDIA USUARIO - ROL
-- CORE INSTITUCIONAL
-- ============================================================

CREATE TABLE core.usuario_rol (
    id_usuario_rol BIGSERIAL PRIMARY KEY,
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    id_rol BIGINT REFERENCES core.roles(id_rol),
    fecha_asignacion TIMESTAMP,
    estado BOOLEAN
);

-- ============================================================
-- 2. ADMISION
-- ============================================================

CREATE SCHEMA admision;


-- CRM
CREATE TABLE admision.crm (
    id_crm BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES core.personas(id_persona),
    id_responsable BIGINT REFERENCES core.empleados(id_empleado),
    origen VARCHAR(100),
    estado VARCHAR(50),
    fecha_registro TIMESTAMP,
    observacion TEXT
);


-- ASPIRANTES
CREATE TABLE admision.aspirantes (
    id_aspirante BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES core.personas(id_persona),
    id_crm BIGINT REFERENCES admision.crm(id_crm),
    carrera_interes VARCHAR(150),
    periodo_interes VARCHAR(100),
    estado VARCHAR(50),
    fecha_registro TIMESTAMP
);


-- EXPEDIENTES
CREATE TABLE admision.expedientes (
    id_expediente BIGSERIAL PRIMARY KEY,
    id_aspirante BIGINT REFERENCES admision.aspirantes(id_aspirante),
    codigo_expediente VARCHAR(50),
    fecha_apertura DATE,
    estado VARCHAR(50),
    observacion TEXT
);


-- PAGOS
CREATE TABLE admision.pagos (
    id_pago BIGSERIAL PRIMARY KEY,
    id_expediente BIGINT REFERENCES admision.expedientes(id_expediente),
    concepto VARCHAR(150),
    monto NUMERIC(12,2),
    fecha_pago DATE,
    estado VARCHAR(50),
    observacion TEXT
);


-- DOCUMENTOS
CREATE TABLE admision.documentos (
    id_documento BIGSERIAL PRIMARY KEY,
    id_expediente BIGINT REFERENCES admision.expedientes(id_expediente),
    tipo_documento VARCHAR(100),
    nombre_archivo VARCHAR(255),
    ruta_archivo TEXT,
    fecha_carga TIMESTAMP,
    estado VARCHAR(50),
    observacion TEXT
);


-- MATRICULA
CREATE TABLE admision.matricula (
    id_matricula BIGSERIAL PRIMARY KEY,
    id_expediente BIGINT REFERENCES admision.expedientes(id_expediente),
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    codigo_matricula VARCHAR(50),
    fecha_matricula DATE,
    estado VARCHAR(50)
);



-- ============================================================
-- 3. MENTORIA
-- ============================================================

CREATE SCHEMA mentoria;


-- INCIDENCIAS
CREATE TABLE mentoria.incidencias (
    id_incidencia BIGSERIAL PRIMARY KEY,
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    id_responsable BIGINT REFERENCES core.empleados(id_empleado),
    asunto VARCHAR(200),
    descripcion TEXT,
    prioridad VARCHAR(50),
    estado VARCHAR(50),
    fecha_registro TIMESTAMP,
    fecha_cierre TIMESTAMP
);


-- SEGUIMIENTO
CREATE TABLE mentoria.seguimiento (
    id_seguimiento BIGSERIAL PRIMARY KEY,
    id_incidencia BIGINT REFERENCES mentoria.incidencias(id_incidencia),
    id_responsable BIGINT REFERENCES core.empleados(id_empleado),
    fecha TIMESTAMP,
    accion_realizada TEXT,
    resultado TEXT,
    proxima_accion TEXT
);


-- DERIVACIONES
CREATE TABLE mentoria.derivaciones (
    id_derivacion BIGSERIAL PRIMARY KEY,
    id_incidencia BIGINT REFERENCES mentoria.incidencias(id_incidencia),
    id_unidad BIGINT REFERENCES core.unidades(id_unidad),
    fecha_derivacion TIMESTAMP,
    motivo TEXT,
    observacion TEXT,
    estado VARCHAR(50)
);


-- FAQ
CREATE TABLE mentoria.faq (
    id_faq BIGSERIAL PRIMARY KEY,
    pregunta TEXT,
    respuesta TEXT,
    categoria VARCHAR(100),
    estado BOOLEAN
);



-- ============================================================
-- 4. CALIDAD
-- ============================================================

CREATE SCHEMA calidad;


-- AREAS
CREATE TABLE calidad.areas (
    id_area BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(150),
    descripcion TEXT,
    estado BOOLEAN
);


-- INDICADORES
CREATE TABLE calidad.indicadores (
    id_indicador BIGSERIAL PRIMARY KEY,
    id_area BIGINT REFERENCES calidad.areas(id_area),
    codigo VARCHAR(50),
    criterio VARCHAR(200),
    subcriterio VARCHAR(200),
    indicador TEXT,
    estado BOOLEAN
);


-- EVIDENCIAS
CREATE TABLE calidad.evidencias (
    id_evidencia BIGSERIAL PRIMARY KEY,
    id_indicador BIGINT REFERENCES calidad.indicadores(id_indicador),
    id_responsable BIGINT REFERENCES core.empleados(id_empleado),
    nombre_archivo VARCHAR(255),
    ruta_archivo TEXT,
    fecha_carga TIMESTAMP,
    estado VARCHAR(50)
);


-- REVISIONES
CREATE TABLE calidad.revisiones (
    id_revision BIGSERIAL PRIMARY KEY,
    id_evidencia BIGINT REFERENCES calidad.evidencias(id_evidencia),
    id_revisor BIGINT REFERENCES core.empleados(id_empleado),
    fecha_revision TIMESTAMP,
    resultado VARCHAR(50),
    observacion TEXT
);



-- ============================================================
-- 5. PPP
-- ============================================================

CREATE SCHEMA ppp;


-- EMPRESAS
CREATE TABLE ppp.empresas (
    id_empresa BIGSERIAL PRIMARY KEY,
    ruc VARCHAR(20),
    razon_social VARCHAR(200),
    sector VARCHAR(100),
    direccion TEXT,
    contacto VARCHAR(150),
    telefono VARCHAR(20),
    correo VARCHAR(150),
    estado BOOLEAN
);


-- CONVENIOS
CREATE TABLE ppp.convenios (
    id_convenio BIGSERIAL PRIMARY KEY,
    id_empresa BIGINT REFERENCES ppp.empresas(id_empresa),
    numero_convenio VARCHAR(50),
    tipo VARCHAR(100),
    fecha_inicio DATE,
    fecha_fin DATE,
    estado VARCHAR(50)
);


-- CONVOCATORIAS
CREATE TABLE ppp.convocatorias (
    id_convocatoria BIGSERIAL PRIMARY KEY,
    id_empresa BIGINT REFERENCES ppp.empresas(id_empresa),
    titulo VARCHAR(200),
    descripcion TEXT,
    numero_cupos INTEGER,
    fecha_inicio DATE,
    fecha_fin DATE,
    estado VARCHAR(50)
);


-- POSTULACIONES
CREATE TABLE ppp.postulaciones (
    id_postulacion BIGSERIAL PRIMARY KEY,
    id_convocatoria BIGINT REFERENCES ppp.convocatorias(id_convocatoria),
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    fecha_postulacion TIMESTAMP,
    estado VARCHAR(50),
    observacion TEXT
);


-- PRACTICAS
CREATE TABLE ppp.practicas (
    id_practica BIGSERIAL PRIMARY KEY,
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    id_empresa BIGINT REFERENCES ppp.empresas(id_empresa),
    id_convenio BIGINT REFERENCES ppp.convenios(id_convenio),
    id_tutor BIGINT REFERENCES core.empleados(id_empleado),
    fecha_inicio DATE,
    fecha_fin DATE,
    horas_planificadas INTEGER,
    horas_ejecutadas INTEGER,
    estado VARCHAR(50)
);


-- TUTORIAS
CREATE TABLE ppp.tutorias (
    id_tutoria BIGSERIAL PRIMARY KEY,
    id_practica BIGINT REFERENCES ppp.practicas(id_practica),
    id_tutor BIGINT REFERENCES core.empleados(id_empleado),
    fecha TIMESTAMP,
    descripcion TEXT,
    hallazgos TEXT,
    porcentaje_avance NUMERIC(5,2)
);



-- ============================================================
-- 6. VINCULACION
-- ============================================================

CREATE SCHEMA vinculacion;


-- ORGANIZACIONES
CREATE TABLE vinculacion.organizaciones (
    id_organizacion BIGSERIAL PRIMARY KEY,
    ruc VARCHAR(20),
    nombre VARCHAR(200),
    direccion TEXT,
    contacto VARCHAR(150),
    telefono VARCHAR(20),
    correo VARCHAR(150),
    estado BOOLEAN
);


-- PROYECTOS
CREATE TABLE vinculacion.proyectos (
    id_proyecto BIGSERIAL PRIMARY KEY,
    id_organizacion BIGINT REFERENCES vinculacion.organizaciones(id_organizacion),
    nombre VARCHAR(200),
    descripcion TEXT,
    fecha_inicio DATE,
    fecha_fin DATE,
    estado VARCHAR(50)
);


-- CONVENIOS
CREATE TABLE vinculacion.convenios (
    id_convenio BIGSERIAL PRIMARY KEY,
    id_organizacion BIGINT REFERENCES vinculacion.organizaciones(id_organizacion),
    numero_convenio VARCHAR(50),
    fecha_inicio DATE,
    fecha_fin DATE,
    estado VARCHAR(50)
);


-- PARTICIPANTES
CREATE TABLE vinculacion.participantes (
    id_participante BIGSERIAL PRIMARY KEY,
    id_proyecto BIGINT REFERENCES vinculacion.proyectos(id_proyecto),
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    fecha_ingreso DATE,
    horas_asignadas INTEGER,
    horas_cumplidas INTEGER,
    estado VARCHAR(50)
);


-- ACTIVIDADES
CREATE TABLE vinculacion.actividades (
    id_actividad BIGSERIAL PRIMARY KEY,
    id_proyecto BIGINT REFERENCES vinculacion.proyectos(id_proyecto),
    nombre VARCHAR(200),
    descripcion TEXT,
    meta TEXT,
    fecha_inicio DATE,
    fecha_fin DATE,
    estado VARCHAR(50)
);


-- SEGUIMIENTO
CREATE TABLE vinculacion.seguimiento (
    id_seguimiento BIGSERIAL PRIMARY KEY,
    id_proyecto BIGINT REFERENCES vinculacion.proyectos(id_proyecto),
    id_participante BIGINT REFERENCES vinculacion.participantes(id_participante),
    fecha TIMESTAMP,
    descripcion TEXT,
    hallazgos TEXT,
    porcentaje_avance NUMERIC(5,2)
);



-- ============================================================
-- 7. VACACIONES
-- ============================================================

CREATE SCHEMA vacaciones;


-- SALDOS
CREATE TABLE vacaciones.saldos (
    id_saldo BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT REFERENCES core.empleados(id_empleado),
    periodo VARCHAR(20),
    dias_asignados NUMERIC(6,2),
    dias_utilizados NUMERIC(6,2),
    dias_disponibles NUMERIC(6,2)
);


-- SOLICITUDES
CREATE TABLE vacaciones.solicitudes (
    id_solicitud BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT REFERENCES core.empleados(id_empleado),
    tipo VARCHAR(100),
    fecha_inicio DATE,
    fecha_fin DATE,
    dias_solicitados NUMERIC(6,2),
    horas_solicitadas NUMERIC(6,2),
    motivo TEXT,
    estado VARCHAR(50),
    fecha_solicitud TIMESTAMP
);


-- FERIADOS
CREATE TABLE vacaciones.feriados (
    id_feriado BIGSERIAL PRIMARY KEY,
    fecha DATE,
    descripcion VARCHAR(200),
    tipo VARCHAR(100),
    estado BOOLEAN
);


-- APROBACIONES
CREATE TABLE vacaciones.aprobaciones (
    id_aprobacion BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT REFERENCES vacaciones.solicitudes(id_solicitud),
    id_aprobador BIGINT REFERENCES core.empleados(id_empleado),
    fecha TIMESTAMP,
    decision VARCHAR(50),
    observacion TEXT
);


-- PERMISOS
CREATE TABLE vacaciones.permisos (
    id_permiso BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT REFERENCES core.empleados(id_empleado),
    fecha DATE,
    hora_inicio TIME,
    hora_fin TIME,
    total_horas NUMERIC(5,2),
    motivo TEXT,
    estado VARCHAR(50)
);



-- ============================================================
-- 8. GRADUACION
-- ============================================================

CREATE SCHEMA graduacion;


-- EVENTOS
CREATE TABLE graduacion.eventos (
    id_evento BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(200),
    fecha DATE,
    hora TIME,
    sede VARCHAR(150),
    jornada VARCHAR(100),
    aforo INTEGER,
    estado VARCHAR(50)
);


-- BUTACAS
CREATE TABLE graduacion.butacas (
    id_butaca BIGSERIAL PRIMARY KEY,
    id_evento BIGINT REFERENCES graduacion.eventos(id_evento),
    fila VARCHAR(20),
    numero INTEGER,
    estado VARCHAR(50)
);


-- PASES
CREATE TABLE graduacion.pases (
    id_pase BIGSERIAL PRIMARY KEY,
    id_evento BIGINT REFERENCES graduacion.eventos(id_evento),
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    id_butaca BIGINT REFERENCES graduacion.butacas(id_butaca),
    tipo VARCHAR(100),
    fecha_emision TIMESTAMP,
    estado VARCHAR(50)
);


-- PAGOS
CREATE TABLE graduacion.pagos (
    id_pago BIGSERIAL PRIMARY KEY,
    id_estudiante BIGINT REFERENCES core.estudiantes(id_estudiante),
    id_evento BIGINT REFERENCES graduacion.eventos(id_evento),
    monto NUMERIC(12,2),
    fecha_pago DATE,
    comprobante TEXT,
    estado VARCHAR(50),
    observacion TEXT
);


-- QR
CREATE TABLE graduacion.qr (
    id_qr BIGSERIAL PRIMARY KEY,
    id_pase BIGINT REFERENCES graduacion.pases(id_pase),
    codigo VARCHAR(255),
    fecha_generacion TIMESTAMP,
    fecha_uso TIMESTAMP,
    utilizado BOOLEAN
);



-- ============================================================
-- 9. PORTAL
-- ============================================================

CREATE SCHEMA portal;


-- SERVICIOS
CREATE TABLE portal.servicios (
    id_servicio BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(150),
    descripcion TEXT,
    url TEXT,
    estado BOOLEAN
);


-- ACCESOS
CREATE TABLE portal.accesos (
    id_acceso BIGSERIAL PRIMARY KEY,
    id_servicio BIGINT REFERENCES portal.servicios(id_servicio),
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    fecha_acceso TIMESTAMP,
    estado VARCHAR(50)
);


-- INTEGRACIONES
CREATE TABLE portal.integraciones (
    id_integracion BIGSERIAL PRIMARY KEY,
    id_servicio BIGINT REFERENCES portal.servicios(id_servicio),
    nombre VARCHAR(150),
    tipo VARCHAR(100),
    endpoint TEXT,
    descripcion TEXT,
    estado BOOLEAN
);



-- ============================================================
-- 10. PAGOS DOCENTES  (versión mejorada)
-- Requerimientos: RF-PAG-01 a RF-PAG-06, RNF-PAG-01 y RNF-PAG-02
-- Usa (sin modificarlas) las tablas de core:
--   core.empleados, core.personas, core.catalogos_academicos, core.usuarios
-- Las carreras se registran en core.catalogos_academicos con tipo = 'CARRERA'
-- ============================================================

CREATE SCHEMA pagos_docentes;


-- DOCENTES: indica qué empleados son docentes
CREATE TABLE pagos_docentes.docentes (
    id_docente BIGSERIAL PRIMARY KEY,
    id_empleado BIGINT NOT NULL UNIQUE REFERENCES core.empleados(id_empleado),
    correo_notificacion VARCHAR(150),
    fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
    estado BOOLEAN NOT NULL DEFAULT TRUE
);


-- PERIODOS: PAO / periodos académicos (RF-PAG-03 filtra por periodo)
CREATE TABLE pagos_docentes.periodos (
    id_periodo BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    fecha_inicio DATE,
    fecha_fin DATE,
    estado BOOLEAN NOT NULL DEFAULT TRUE
);


-- MODULOS (RF-PAG-01): un registro por cada módulo/materia dictada por un docente
CREATE TABLE pagos_docentes.modulos (
    id_modulo BIGSERIAL PRIMARY KEY,
    id_docente BIGINT NOT NULL REFERENCES pagos_docentes.docentes(id_docente),
    id_periodo BIGINT NOT NULL REFERENCES pagos_docentes.periodos(id_periodo),
    id_carrera BIGINT NOT NULL REFERENCES core.catalogos_academicos(id_catalogo),
    codigo_eva VARCHAR(50),
    nombre_modulo VARCHAR(200) NOT NULL,
    paralelo VARCHAR(50),
    numero_modulo SMALLINT,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    listo_para_pago BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_listo_pago TIMESTAMP,
    estado VARCHAR(30) NOT NULL DEFAULT 'EN_CURSO'
        CHECK (estado IN ('EN_CURSO','LISTO_PAGO','APROBADO','PAGADO','ANULADO')),
    id_usuario_registro BIGINT REFERENCES core.usuarios(id_usuario),
    fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_modulo_fechas CHECK (fecha_fin >= fecha_inicio)
);


-- CORREOS PROCESADOS (RF-PAG-02 y RNF-PAG-01)
-- Guarda cada correo leído del buzón académico y el log de fallas
CREATE TABLE pagos_docentes.correos_procesados (
    id_correo BIGSERIAL PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL UNIQUE,      -- identificador único del correo
    remitente VARCHAR(150),
    asunto VARCHAR(300),
    fecha_recepcion TIMESTAMP,
    fecha_procesamiento TIMESTAMP NOT NULL DEFAULT NOW(),
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE','PROCESADO','FALLIDO','REVISADO_MANUAL')),
    detalle_error TEXT,                           -- motivo de la falla
    id_modulo BIGINT REFERENCES pagos_docentes.modulos(id_modulo),
    id_usuario_revision BIGINT REFERENCES core.usuarios(id_usuario),
    fecha_revision TIMESTAMP
);


-- APROBACIONES (RF-PAG-02): aprobación del área académica para pago
CREATE TABLE pagos_docentes.aprobaciones (
    id_aprobacion BIGSERIAL PRIMARY KEY,
    id_modulo BIGINT NOT NULL UNIQUE REFERENCES pagos_docentes.modulos(id_modulo),
    fecha_aprobacion TIMESTAMP NOT NULL,
    origen VARCHAR(20) NOT NULL DEFAULT 'MANUAL'
        CHECK (origen IN ('CORREO','MANUAL')),
    id_correo BIGINT REFERENCES pagos_docentes.correos_procesados(id_correo),
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    estado VARCHAR(20) NOT NULL DEFAULT 'VIGENTE'
        CHECK (estado IN ('VIGENTE','ANULADA')),
    observacion TEXT
);


-- PAGOS (RF-PAG-06): registro de que el pago se realizó
CREATE TABLE pagos_docentes.pagos (
    id_pago BIGSERIAL PRIMARY KEY,
    id_modulo BIGINT NOT NULL UNIQUE REFERENCES pagos_docentes.modulos(id_modulo),
    monto NUMERIC(12,2),                          -- referencial, el sistema no lo calcula
    fecha_pago DATE,
    numero_factura VARCHAR(50),
    numero_comprobante VARCHAR(100),
    estado VARCHAR(20) NOT NULL DEFAULT 'POR_PAGAR'
        CHECK (estado IN ('POR_PAGAR','PAGADO')),
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    observacion TEXT,
    CONSTRAINT ck_pagado_con_fecha CHECK (estado <> 'PAGADO' OR fecha_pago IS NOT NULL)
);


-- CONFIGURACION DEL UMBRAL (RF-PAG-04)
CREATE TABLE pagos_docentes.configuracion_umbral (
    id_configuracion BIGSERIAL PRIMARY KEY,
    valor INTEGER NOT NULL CHECK (valor > 0),
    unidad VARCHAR(10) NOT NULL CHECK (unidad IN ('DIAS','MESES')),
    correo_notificacion VARCHAR(150),             -- a quién se envía la alerta
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    fecha_registro TIMESTAMP NOT NULL DEFAULT NOW()
);
-- Solo puede haber una configuración activa a la vez
CREATE UNIQUE INDEX uq_umbral_activo ON pagos_docentes.configuracion_umbral (activo) WHERE activo;


-- ALERTAS (RF-PAG-05): panel + correo
CREATE TABLE pagos_docentes.alertas (
    id_alerta BIGSERIAL PRIMARY KEY,
    id_modulo BIGINT NOT NULL REFERENCES pagos_docentes.modulos(id_modulo),
    id_configuracion BIGINT REFERENCES pagos_docentes.configuracion_umbral(id_configuracion),
    fecha_alerta TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo VARCHAR(30) NOT NULL DEFAULT 'PAGO_ATRASADO'
        CHECK (tipo IN ('PAGO_ATRASADO')),
    dias_atraso INTEGER,
    mensaje TEXT,
    correo_enviado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_envio_correo TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVA'
        CHECK (estado IN ('ACTIVA','RESUELTA')),
    fecha_resolucion TIMESTAMP
);
-- Evita duplicar alertas activas para el mismo módulo
CREATE UNIQUE INDEX uq_alerta_activa ON pagos_docentes.alertas (id_modulo) WHERE estado = 'ACTIVA';


-- HISTORIAL (RF-PAG-06)
CREATE TABLE pagos_docentes.historial (
    id_historial BIGSERIAL PRIMARY KEY,
    id_modulo BIGINT NOT NULL REFERENCES pagos_docentes.modulos(id_modulo),
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50) NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT NOW(),
    id_usuario BIGINT REFERENCES core.usuarios(id_usuario),
    observacion TEXT
);


-- ÍNDICES para que los filtros por periodo, mes y carrera sean rápidos (RNF-PAG-02)
CREATE INDEX ix_modulos_docente ON pagos_docentes.modulos (id_docente);
CREATE INDEX ix_modulos_periodo ON pagos_docentes.modulos (id_periodo);
CREATE INDEX ix_modulos_carrera ON pagos_docentes.modulos (id_carrera);
CREATE INDEX ix_aprobaciones_fecha ON pagos_docentes.aprobaciones (fecha_aprobacion);
CREATE INDEX ix_pagos_estado ON pagos_docentes.pagos (estado);
CREATE INDEX ix_historial_modulo ON pagos_docentes.historial (id_modulo);
CREATE INDEX ix_correos_estado ON pagos_docentes.correos_procesados (estado);


-- VISTA (RF-PAG-03 y RF-PAG-06): estado de pago por docente y módulo
CREATE VIEW pagos_docentes.v_estado_pagos AS
SELECT m.id_modulo,
       d.id_docente,
       p.apellidos || ' ' || p.nombres                       AS docente,
       m.codigo_eva,
       c.nombre                                               AS carrera,
       pe.nombre                                              AS periodo,
       m.nombre_modulo,
       m.fecha_inicio,
       m.fecha_fin,
       a.fecha_aprobacion,
       DATE_TRUNC('month', a.fecha_aprobacion)::date          AS mes_aprobacion,
       pg.fecha_pago,
       CASE WHEN pg.estado = 'PAGADO' THEN 'PAGADO'
            WHEN a.id_aprobacion IS NOT NULL THEN 'POR_PAGAR'
            ELSE 'SIN_APROBACION' END                         AS estado_pago,
       CASE WHEN a.id_aprobacion IS NULL THEN NULL
            ELSE COALESCE(pg.fecha_pago, CURRENT_DATE) - a.fecha_aprobacion::date
       END                                                    AS dias_transcurridos
FROM pagos_docentes.modulos m
JOIN pagos_docentes.docentes d       ON d.id_docente = m.id_docente
JOIN core.empleados e                ON e.id_empleado = d.id_empleado
JOIN core.personas p                 ON p.id_persona = e.id_persona
JOIN pagos_docentes.periodos pe      ON pe.id_periodo = m.id_periodo
JOIN core.catalogos_academicos c     ON c.id_catalogo = m.id_carrera
LEFT JOIN pagos_docentes.aprobaciones a
       ON a.id_modulo = m.id_modulo AND a.estado = 'VIGENTE'
LEFT JOIN pagos_docentes.pagos pg    ON pg.id_modulo = m.id_modulo;


-- DATO INICIAL: umbral por defecto (el área financiera lo puede cambiar)
INSERT INTO pagos_docentes.configuracion_umbral (valor, unidad) VALUES (30, 'DIAS');
