# Plan de Arquitectura — JDM Empeños

**Versión:** 1.0  
**Fecha:** 2026-07-22  
**Moneda predeterminada:** RD$ (Pesos Dominicanos)  
**Zona horaria:** America/Santo_Domingo  
**Idioma:** Español  

---

## 1. Visión del producto

JDM Empeños es un sistema profesional para administrar negocios de compra, venta y empeño de artículos. Está diseñado para operar con clientes reales, múltiples sucursales, roles diferenciados, evidencia fotográfica obligatoria, cálculos financieros precisos (`Decimal`), auditoría completa y despliegue en Windows (local / `.exe`) y Render (PostgreSQL).

### Principios de diseño

| Principio | Descripción |
|-----------|-------------|
| Modularidad | Blueprints, servicios, repositorios y modelos separados |
| Seguridad | CSRF, permisos en backend, rate limiting, sesiones seguras |
| Precisión financiera | Solo `Decimal`; nunca `float` para dinero |
| Inmutabilidad contractual | Contratos antiguos conservan snapshot de reglas |
| Evidencia | No hay empeño/compra sin identificación ni fotos (salvo excepción auditada) |
| No destrucción | Anulaciones = movimientos inversos; eliminación lógica |
| Multiplataforma | Responsive; SQLite en desarrollo; PostgreSQL en producción |

---

## 2. Arquitectura

```text
┌─────────────────────────────────────────────────────────────┐
│                     Cliente (navegador)                      │
│         HTML5 + Bootstrap 5 + JS (responsive)                │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────┐
│                    Flask Application                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐ │
│  │Blueprints│ │ Forms    │ │Validators│ │ Templates/Static│ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────────────┘ │
│       │            │            │                            │
│  ┌────▼────────────▼────────────▼────┐                      │
│  │            Services                │  ← lógica de negocio │
│  └────┬──────────────────────────────┘                      │
│  ┌────▼──────────────────────────────┐                      │
│  │          Repositories              │  ← acceso a datos    │
│  └────┬──────────────────────────────┘                      │
│  ┌────▼──────────────────────────────┐                      │
│  │     SQLAlchemy Models / ORM        │                      │
│  └────┬──────────────────────────────┘                      │
└───────┼─────────────────────────────────────────────────────┘
        │
┌───────▼──────────┐     ┌─────────────────┐
│ SQLite (dev)     │     │ PostgreSQL (prod)│
└──────────────────┘     └─────────────────┘
        │
┌───────▼──────────────────────────────┐
│ uploads/ (archivos, no base64 en BD) │
└──────────────────────────────────────┘
```

### Capas

1. **Presentación:** plantillas Jinja2, CSS/JS, formularios WTForms.
2. **Rutas (Blueprints):** orquestación HTTP, autorización.
3. **Servicios:** reglas de negocio, cálculos, transacciones.
4. **Repositorios:** consultas y persistencia.
5. **Modelos:** esquema ORM, relaciones, soft-delete.
6. **Utilidades:** dinero, fechas, archivos, QR, PDF, seguridad.

### Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.11+, Flask |
| ORM | SQLAlchemy + Flask-SQLAlchemy |
| Migraciones | Flask-Migrate / Alembic |
| Auth | Flask-Login + Werkzeug password hash |
| Forms | Flask-WTF / WTForms |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript |
| PDF | ReportLab / WeasyPrint (según fase) |
| QR | qrcode |
| BD desarrollo | SQLite |
| BD producción | PostgreSQL |
| Deploy | Render (`Procfile`, `render.yaml`) |
| Empaquetado | PyInstaller (Fase 8) |

---

## 3. Módulos

| Módulo | Blueprint | Fase | Responsabilidad |
|--------|-----------|------|-----------------|
| Auth | `auth` | 1 | Login, logout, sesión, bloqueo, recuperación |
| Dashboard | `dashboard` | 1 | KPIs, alertas, gráficos |
| Branches | `branches` | 1 | Sucursales |
| Users | `users` | 1 | Usuarios, roles, permisos |
| Settings | `settings` | 1 | Configuración del negocio |
| Audit | `audit` | 1/6 | Bitácora de auditoría |
| Customers | `customers` | 2 | Clientes |
| Deliverers | `deliverers` | 2 | Persona que entrega |
| Items | `items` | 2 | Artículos, categorías, fotos |
| Documents | `documents` | 2/3 | Evidencia, PDFs, QR |
| Pawn | `pawn` | 3 | Empeños, contratos, % manual |
| Payments | `payments` | 4 | Pagos, abonos, idempotencia |
| Renewals | `renewals` | 4 | Renovaciones |
| Purchases | `purchases` | 5 | Compras directas |
| Inventory | `inventory` | 5 | Inventario, transferencias |
| Sales | `sales` | 5 | Ventas, reservas, garantías |
| Cash | `cash` | 6 | Caja, arqueo |
| Expenses | `expenses` | 6 | Gastos e ingresos |
| Reports | `reports` | 6 | Reportes y exportaciones |
| Notifications | `notifications` | 7 | WhatsApp/SMS/Email (opt-in) |

---

## 4. Tablas (mínimas)

### Fase 1

- `roles`
- `permissions`
- `role_permissions`
- `branches`
- `users`
- `login_logs`
- `settings`
- `audit_logs`
- `backups` (estructura)

### Fase 2+

- `customers`, `customer_documents`, `customer_references`
- `deliverers`, `deliverer_documents`, `deliverer_signatures`
- `item_categories`, `items`, `item_images`, `evidence_files`
- `item_movements`, `item_evaluations`
- `pawn_contracts`, `pawn_contract_versions`
- `pawn_payments`, `pawn_payment_allocations`, `renewals`
- `interest_rules`, `fee_rules`, `penalties`
- `direct_purchases`
- `sales`, `sale_items`, `sale_payments`, `reservations`, `returns`, `warranties`
- `cash_registers`, `cash_sessions`, `cash_movements`
- `expenses`, `expense_categories`
- `transfers`, `notifications`, `document_templates`
- `attachments`, `operation_exceptions`, `operation_signatures`

### Relaciones clave (vista lógica)

```text
Branch 1──* User
Branch 1──* Customer
Role *──* Permission (role_permissions)
User *──1 Role
Customer 1──* Deliverer (por operación)
Customer 1──* PawnContract
Deliverer 1──* PawnContract / DirectPurchase
Item 1──* ItemImage / EvidenceFile
PawnContract 1──* PawnPayment / Renewal / PawnContractVersion
Sale *──* Item (sale_items)
CashSession 1──* CashMovement
User 1──* AuditLog / LoginLog
```

---

## 5. Rutas mínimas

| Ruta | Módulo | Fase |
|------|--------|------|
| `/` | redirect dashboard/login | 1 |
| `/login` | auth | 1 |
| `/logout` | auth | 1 |
| `/dashboard` | dashboard | 1 |
| `/branches` | branches | 1 |
| `/users` | users | 1 |
| `/settings` | settings | 1 |
| `/audit` | audit | 1 |
| `/healthz` | app | 1 |
| `/customers` | customers | 2 |
| `/deliverers` | deliverers | 2 |
| `/items` | items | 2 |
| `/pawn` | pawn | 3 |
| `/payments` | payments | 4 |
| `/renewals` | renewals | 4 |
| `/expired` | pawn/expired | 4 |
| `/purchases` | purchases | 5 |
| `/sales` | sales | 5 |
| `/inventory` | inventory | 5 |
| `/cash` | cash | 6 |
| `/expenses` | expenses | 6 |
| `/reports` | reports | 6 |

---

## 6. Roles y permisos

### Roles

| Rol | Código | Alcance |
|-----|--------|---------|
| Superadministrador | `superadmin` | Todas las sucursales |
| Administrador | `admin` | Su sucursal (+ autorizaciones) |
| Cajero / Empleado | `cashier` | Su sucursal, operaciones diarias |
| Auditor | `auditor` | Solo lectura |

### Matriz de permisos (extracto Fase 1)

| Permiso | superadmin | admin | cashier | auditor |
|---------|------------|-------|---------|---------|
| `branches.manage` | ✓ | | | |
| `users.manage` | ✓ | ✓ (sucursal) | | |
| `settings.manage` | ✓ | parcial | | |
| `dashboard.view` | ✓ | ✓ | ✓ | ✓ |
| `audit.view` | ✓ | ✓ | | ✓ |
| `reports.global` | ✓ | | | ✓ |

Los permisos se validan con decoradores/servicios en **backend**. Ocultar botones no es suficiente.

---

## 7. Flujos principales

### 7.1 Clientes

1. Buscar (evitar duplicados por cédula/documento).
2. Si existe duplicado → alerta + autorización admin.
3. Capturar datos + fotos documento + firma.
4. Asignar código único, sucursal y empleado.
5. Auditoría.

### 7.2 Persona que entrega

1. ¿Cliente entrega? Sí → vincular cliente. No → registrar deliverer.
2. Fotos obligatorias (persona, doc frente/reverso, sosteniendo artículo).
3. Declaración de procedencia + firma.
4. Relacionar con cliente, artículo, contrato/compra.

### 7.3 Fotografías

1. Captura cámara / galería.
2. Validar MIME, tamaño, nombre seguro.
3. Guardar archivo en `uploads/`, hash SHA-256.
4. Metadatos en BD (nunca base64).
5. Revisar checklist obligatorio antes de confirmar.
6. Excepción solo con admin + motivo + auditoría.

### 7.4 Empeños

1. Cliente + deliverer + artículo + evaluación.
2. % (global / sucursal / categoría / cliente / manual).
3. Snapshot de reglas en contrato.
4. Firma + declaración + fotos.
5. Número `EMP-YYYY-######`.
6. Movimiento de caja / inventario empeñado.

### 7.5 Compras

1. Identificar vendedor/deliverer + evidencia.
2. Precio negociado/pagado.
3. Número `COM-YYYY-######`.
4. Estado post-compra (revisión / venta / bloqueado).

### 7.6 Ventas

1. Solo artículos disponibles/autorizados.
2. Precio, descuento, impuesto, método de pago.
3. Factura + garantía opcional.
4. Actualizar inventario y caja.

### 7.7 Caja

1. Apertura con monto inicial (obligatoria salvo excepción).
2. Movimientos ligados a operaciones.
3. Cierre + arqueo + diferencia + firma/aprobación.

---

## 8. Reglas de porcentaje

Orden de resolución sugerido:

1. Manual por contrato (autorizado).
2. Porcentaje por cliente.
3. Porcentaje por categoría.
4. Porcentaje por sucursal.
5. Porcentaje global.

Límites por rol (configurables). Desviación del default exige motivo + autorizador + auditoría. Contratos antiguos **nunca** se recalculan al cambiar config.

---

## 9. Reglas de vencimiento

```text
Activo → Próximo a vencer → Vencido → Período de gracia
  → Pendiente de autorización → Autorizado para inventario
  → Disponible para venta
```

No hay paso automático a venta sin reglas + autorización registrada.

---

## 10. Seguridad

- CSRF (Flask-WTF)
- Contraseñas hasheadas (Werkzeug)
- Rate limiting en login
- Bloqueo por intentos fallidos
- Timeout por inactividad
- Headers de seguridad
- Validación de archivos e imágenes
- Soft-delete; sin borrado físico financiero
- Secretos solo en variables de entorno
- Permisos en cada endpoint sensible

---

## 11. Pruebas

| Área | Cobertura |
|------|-----------|
| Auth / roles | Login, bloqueo, permisos |
| % manual | Límites, snapshot |
| Interés / mora / cargos | Cálculos Decimal |
| Pagos | Parcial, total, idempotencia |
| Renovaciones / vencidos | Flujos de estado |
| Fotos / firmas / excepciones | Obligatoriedad |
| Series / IMEI | Duplicados |
| Caja / anulaciones | Integridad |
| Reportes | Totales |

Datos demo separados de producción (`seed_demo` vs `create_superadmin`).

---

## 12. Implementación por fases

### Fase 1 — Base (ACTUAL)

Estructura, config, BD, usuarios, roles, seguridad, sucursales, dashboard básico, `/healthz`, docs de instalación inicial.

### Fase 2 — Identidad y artículos

Clientes, deliverers, documentos, fotos, firmas, categorías, artículos, búsqueda.

### Fase 3 — Empeños

Evaluación, contratos, % manual, cálculos, PDF, QR.

### Fase 4 — Cobranza

Pagos, abonos, renovaciones, mora, vencimientos, autorizaciones.

### Fase 5 — Comercio

Compras, inventario, ventas, reservas, garantías, devoluciones.

### Fase 6 — Operaciones

Caja, gastos, reportes, auditoría avanzada.

### Fase 7 — Extensiones

Notificaciones, exportaciones, backups, optimización de imágenes.

### Fase 8 — Cierre

Pruebas completas, Render/PostgreSQL, empaquetado `.exe`.

### Criterio de avance

No avanzar de fase con errores críticos. Al cerrar cada fase se reporta: archivos, rutas, tablas, pruebas, pendientes, riesgos.

---

## 13. Entornos

| Entorno | BD | Uso |
|---------|----|-----|
| development | SQLite (`instance/jdm_empenos.db`) | Local Windows |
| testing | SQLite en memoria / archivo temp | Pytest |
| production | PostgreSQL (`DATABASE_URL`) | Render / servidor |

---

## 14. Convenciones

- Código y comentarios técnicos en español o inglés consistente; **UI 100% español**.
- Montos: `Numeric(14, 2)` / `Decimal`.
- Fechas: timezone-aware (`America/Santo_Domingo`).
- Numeración: `EMP-2026-000001`, `COM-2026-000001`, recibos/facturas similares.
- Archivos: nombre UUID + extensión segura; hash SHA-256.
- Soft-delete: `deleted_at`, `is_active` / `status`.

---

## 15. Checklist de reglas obligatorias

- [x] Arquitectura modular (no monolito)
- [ ] Sin botones muertos
- [ ] Sin pagos duplicados (idempotencia)
- [ ] Sin borrado físico financiero
- [ ] Sin `float` en dinero
- [ ] Sin imágenes base64 en BD
- [ ] Sin mezclar lógica financiera en HTML
- [ ] Snapshot de contratos
- [ ] Evidencia obligatoria
- [ ] Deliverer obligatorio
- [ ] Series/IMEI con autorización
- [ ] Anulaciones con motivo
- [ ] Auditoría de acciones importantes
- [ ] Transacciones y manejo de errores

*(Los ítems de negocio se completan en sus fases correspondientes.)*
