-- 1. Plantillas fijas para avisos de mora, aviso previo al bloqueo
--    y confirmación de bloqueo. Refleja la especificación aprobada
--    el 12 de noviembre de 2026.
--    No habilita bloqueo ni crea scheduler.

-- 2. Plantilla del aviso de mora (D+1 y D+6).
--    Incluye la advertencia de bloqueo obligatoria.

INSERT INTO public.system_settings
  (key, value, description, version)
VALUES
  ('collections.notice_overdue_template',
   to_jsonb('Hola {nombre_cliente}, tu cuota {numero_cuota} del crédito {id_credito} venció el {fecha_vencimiento} y presenta un saldo pendiente de {monto_pendiente}.

Si no realizas el pago, tu celular podrá ser bloqueado conforme a lo acordado en tu contrato.

Puedes pagar por transferencia a la llave {llave_pago} o en efectivo en nuestra sucursal.

Si ya realizaste el pago, ignora este mensaje.'::text),
   'Plantilla fija del aviso de mora (D+1 y D+6), con advertencia de bloqueo',
   1),

-- 3. Plantilla del aviso previo al bloqueo manual (solo desde D+15).
  ('collections.notice_pre_lock_template',
   to_jsonb('Hola {nombre_cliente}, debido a la mora en tu crédito {id_credito}, tu celular será bloqueado en la próxima hora.

Para evitar el bloqueo, realiza el pago de {monto_pendiente} antes de {hora_limite}.

Si ya realizaste el pago, contáctanos de inmediato.'::text),
   'Plantilla fija del aviso previo al bloqueo manual, enviada desde D+15',
   1),

-- 4. Plantilla de confirmación de bloqueo al cliente.
  ('collections.notice_locked_confirmation_template',
   to_jsonb('Hola {nombre_cliente}, tu celular asociado al crédito {id_credito} ha sido bloqueado por mora.

Para desbloquearlo, realiza el pago de {monto_pendiente} y contáctanos.'::text),
   'Plantilla fija de confirmación de bloqueo al cliente',
   1)
ON CONFLICT (key) DO NOTHING;