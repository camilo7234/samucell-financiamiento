-- ============================================================
-- BLOQUE 1: encabezado
-- Permisos minimos del backend sobre public.customers.
-- Sin DELETE. UPDATE solo en columnas no identificatorias.
-- No toca customer_contacts ni otras tablas.
-- ============================================================

-- ============================================================
-- BLOQUE 2: privilegios de tabla y de columna
-- ============================================================
GRANT SELECT, INSERT ON public.customers TO samucell_backend;

GRANT UPDATE (full_name, phone, address, status, notes)
  ON public.customers TO samucell_backend;

-- ============================================================
-- BLOQUE 3: politicas RLS (una por operacion, idempotentes)
-- ============================================================
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'customers'
      AND policyname = 'customers_backend_select'
  ) THEN
    CREATE POLICY customers_backend_select ON public.customers
      FOR SELECT TO samucell_backend USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'customers'
      AND policyname = 'customers_backend_insert'
  ) THEN
    CREATE POLICY customers_backend_insert ON public.customers
      FOR INSERT TO samucell_backend WITH CHECK (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'customers'
      AND policyname = 'customers_backend_update'
  ) THEN
    CREATE POLICY customers_backend_update ON public.customers
      FOR UPDATE TO samucell_backend USING (true) WITH CHECK (true);
  END IF;
END
$$;