# Cierre Fases 3–6 — Operaciones

## Fase 3 — Empeños
- Contratos con capital, % (manual con autorización por rol), interés Decimal
- Snapshot/versión al crear (`pawn_contract_versions`)
- PDF + QR (`document_service`)
- Estados y vencimiento

## Fase 4 — Pagos y renovaciones
- Pagos con asignación mora → cargos → interés → capital
- Idempotencia por `idempotency_key`
- Renovaciones y actualización de vencidos
- Rutas: `/pawn`, `/payments`, `/renewals`, `/expired`

## Fase 5 — Comercio
- Compras directas, inventario, ventas, reservas/devoluciones/garantías (modelos + flujos base)
- Rutas: `/purchases`, `/inventory`, `/sales`

## Fase 6 — Caja, gastos, reportes
- Apertura/cierre de caja y movimientos
- Gastos por categoría
- Reportes + export CSV/XLSX
- Rutas: `/cash`, `/expenses`, `/reports`

## Migración
`06eeae71d3c0_fase3_a_6_operaciones.py`
