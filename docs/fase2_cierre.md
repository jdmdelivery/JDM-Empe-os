# Cierre Fase 2 — JDM Empeños

## Resultado

**Fase 2 completada.** Clientes, persona que entrega, evidencias, firmas, categorías, artículos y búsqueda global operativos.

## Archivos principales creados/modificados

- Modelos: `customer.py`, `deliverer.py`, `item.py`, `evidence.py`
- Blueprints: `customers/`, `deliverers/`, `items/`
- Servicios: `file_storage.py`, `numbering.py`, `search_service.py`, `category_seed.py`
- Formularios, plantillas, `static/js/capture.js`
- Rutas app: `/uploads/<path>`, `/search`
- Pruebas: `tests/test_phase2_customers_items.py`
- Migración Alembic Fase 2

## Rutas implementadas

| Ruta | Descripción |
|------|-------------|
| `/customers` | Listado y búsqueda de clientes |
| `/customers/create` | Alta con fotos/firma |
| `/customers/<id>` | Perfil y galería |
| `/customers/<id>/edit` | Edición |
| `/deliverers` | Persona que entrega |
| `/deliverers/create` | Alta con evidencia obligatoria |
| `/deliverers/<id>` | Detalle y galería |
| `/items` | Artículos |
| `/items/create` | Alta con fotos y control de duplicados |
| `/items/<id>` | Detalle y galería |
| `/items/categories` | Categorías |
| `/search` | Buscador global |
| `/uploads/<path>` | Archivos seguros (login requerido) |

## Tablas creadas

- `customers`, `customer_documents`, `customer_references`
- `deliverers`, `deliverer_documents`, `deliverer_signatures`
- `item_categories`, `items`, `item_images`, `item_evaluations`
- `evidence_files`, `operation_signatures`, `operation_exceptions`

## Pruebas

```text
pytest → 18 passed
```

## Funciones pendientes (Fase 3+)

- Evaluación avanzada + empeños + % manual + PDF/QR (Fase 3)
- Pagos, renovaciones, vencimientos (Fase 4)
- Compras, ventas, inventario completo (Fase 5)

## Riesgos / notas

- Imágenes en disco (`uploads/`), metadatos + hash SHA-256 en BD
- Cédula/serie/IMEI duplicados requieren autorización + auditoría
- Fotos obligatorias en deliverer; excepción solo admin con motivo
- Declaración de procedencia legítima guardada con IP y firma
