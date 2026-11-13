-- 1. Reconciliación de parámetros de cobranza y avisos.
--    Refleja la cronología aprobada el 12 de noviembre de 2026:
--    D-5 y D-1 recordatorios previos; D+1 y D+6 avisos de mora;
--    elegibilidad manual de bloqueo desde D+15; gracia 0.
--    No habilita bloqueo ni crea scheduler.

-- 2. Ajustes a claves existentes: solo si el valor actual difiere.
--    version sube a 2 en el primer cambio real; reejecutar no la vuelve a subir.

UPDATE public.system_settings
SET value = '2'::jsonb,
    version = 2,
    updated_at = now()
WHERE key = 'collections.min_notices_before_lock'
  AND value <> '2'::jsonb;

UPDATE public.system_settings
SET value = '5'::jsonb,
    version = 2,
    updated_at = now()
WHERE key = 'collections.min_days_between_notices'
  AND value <> '5'::jsonb;

UPDATE public.system_settings
SET value = '0'::jsonb,
    version = 2,
    updated_at = now()
WHERE key = 'collections.grace_days'
  AND value <> '0'::jsonb;

-- 3. Claves nuevas para la cronología aprobada.
--    ON CONFLICT DO NOTHING: si ya existieran, no las sobrescribe.

INSERT INTO public.system_settings
  (key, value, description, version)
VALUES
  ('collections.pre_due_notice_offsets',
   '[5, 1]'::jsonb,
   'Dias antes del vencimiento para recordatorios previos: D-5 y D-1',
   1),
  ('collections.first_overdue_notice_offset_days',
   '1'::jsonb,
   'Dia de mora para el primer aviso: D+1',
   1),
  ('collections.second_overdue_notice_offset_days',
   '6'::jsonb,
   'Dia de mora para el segundo aviso: D+6',
   1),
  ('collections.lock_eligibility_days',
   '15'::jsonb,
   'Dias de mora desde los cuales se habilita la evaluacion manual de bloqueo',
   1)
ON CONFLICT (key) DO NOTHING;