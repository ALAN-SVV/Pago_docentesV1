# Pruebas del backend

Las pruebas están agrupadas por módulo:

- `pagos_docentes/`: validaciones de esquemas y colección Postman.
- `admisiones/`: autenticación y rutas del CRM.
- `vacaciones/`: cálculos, saldos, permisos, aprobaciones, históricos y autenticación.

Desde `backend/`, ejecuta todo con:

```powershell
python -m pytest tests -q
```

Para instrucciones y pendientes de Pagos a Docentes, consulta
`pagos_docentes/README.md`.
