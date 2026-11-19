-- Migracion: permisos minimos del backend para el modulo de creditos.
-- Crea venta, items, plan de credito, cuotas, reserva de inventario,
-- movimiento de inventario y lectura de configuracion financiera.
-- No concede DELETE ni permisos de administracion sobre system_settings.

-- 1) Ventas
GRANT SELECT, INSERT ON public.sales TO samucell_backend;
GRANT UPDATE (
  sale_status,
  payment_status,
  confirmed_at,
  confirmed_by,
  cancelled_at,
  cancelled_by,
  cancel_reason,
  updated_at
) ON public.sales TO samucell_backend;

-- 2) Items de venta
GRANT SELECT, INSERT ON public.sale_items TO samucell_backend;
GRANT UPDATE (
  sale_status,
  updated_at
) ON public.sale_items TO samucell_backend;

-- 3) Planes de credito
GRANT SELECT, INSERT ON public.credit_plans TO samucell_backend;
GRANT UPDATE (
  status,
  updated_at
) ON public.credit_plans TO samucell_backend;

-- 4) Cuotas
GRANT SELECT, INSERT ON public.installments TO samucell_backend;
GRANT UPDATE (
  paid_amount,
  status,
  paid_at,
  updated_at
) ON public.installments TO samucell_backend;

-- 5) Sucursales, inventario y configuracion
GRANT SELECT ON public.stores TO samucell_backend;

GRANT SELECT ON public.inventory_items TO samucell_backend;
GRANT UPDATE (
  status,
  updated_at
) ON public.inventory_items TO samucell_backend;

GRANT SELECT ON public.system_settings TO samucell_backend;

-- 6) Movimientos de inventario: trazabilidad de la reserva
GRANT SELECT, INSERT ON public.inventory_movements TO samucell_backend;

-- 7) Vistas financieras de solo lectura
GRANT SELECT ON public.v_credit_balance TO samucell_backend;
GRANT SELECT ON public.v_overdue_installments TO samucell_backend;

-- 8) Permiso sobre la secuencia real utilizada por sales.sale_number
DO $$
DECLARE
  sale_number_sequence text;
BEGIN
  sale_number_sequence := pg_get_serial_sequence('public.sales', 'sale_number');

  IF sale_number_sequence IS NOT NULL THEN
    EXECUTE format(
      'GRANT USAGE, SELECT ON SEQUENCE %s TO samucell_backend',
      sale_number_sequence
    );
  END IF;
END
$$;

-- 9) Politicas RLS para ventas
CREATE POLICY sales_backend_select
  ON public.sales
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY sales_backend_insert
  ON public.sales
  FOR INSERT
  TO samucell_backend
  WITH CHECK (true);

CREATE POLICY sales_backend_update
  ON public.sales
  FOR UPDATE
  TO samucell_backend
  USING (true)
  WITH CHECK (true);

-- 10) Politicas RLS para items de venta
CREATE POLICY sale_items_backend_select
  ON public.sale_items
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY sale_items_backend_insert
  ON public.sale_items
  FOR INSERT
  TO samucell_backend
  WITH CHECK (true);

CREATE POLICY sale_items_backend_update
  ON public.sale_items
  FOR UPDATE
  TO samucell_backend
  USING (true)
  WITH CHECK (true);

-- 11) Politicas RLS para planes de credito
CREATE POLICY credit_plans_backend_select
  ON public.credit_plans
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY credit_plans_backend_insert
  ON public.credit_plans
  FOR INSERT
  TO samucell_backend
  WITH CHECK (true);

CREATE POLICY credit_plans_backend_update
  ON public.credit_plans
  FOR UPDATE
  TO samucell_backend
  USING (true)
  WITH CHECK (true);

-- 12) Politicas RLS para cuotas
CREATE POLICY installments_backend_select
  ON public.installments
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY installments_backend_insert
  ON public.installments
  FOR INSERT
  TO samucell_backend
  WITH CHECK (true);

CREATE POLICY installments_backend_update
  ON public.installments
  FOR UPDATE
  TO samucell_backend
  USING (true)
  WITH CHECK (true);

-- 13) Politicas RLS para sucursales e inventario
CREATE POLICY stores_backend_select
  ON public.stores
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY inventory_items_backend_select
  ON public.inventory_items
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY inventory_items_backend_update
  ON public.inventory_items
  FOR UPDATE
  TO samucell_backend
  USING (true)
  WITH CHECK (true);

-- 14) Politica RLS para configuracion: solo lectura
CREATE POLICY system_settings_backend_select
  ON public.system_settings
  FOR SELECT
  TO samucell_backend
  USING (true);

-- 15) Politicas RLS para movimientos de inventario
CREATE POLICY inventory_movements_backend_select
  ON public.inventory_movements
  FOR SELECT
  TO samucell_backend
  USING (true);

CREATE POLICY inventory_movements_backend_insert
  ON public.inventory_movements
  FOR INSERT
  TO samucell_backend
  WITH CHECK (true);