-- alerts: alertas de mora y otros eventos, entregas de notificaciones
-- y conversaciones de WhatsApp. Sin GPS, sin IP, sin datos de ubicacion.

create table public.alerts (
  id                      uuid primary key default gen_random_uuid(),
  store_id                uuid not null references public.stores (id) on delete restrict,
  alert_type              text not null check (alert_type in
                           ('overdue_installment', 'upcoming_due',
                            'device_lock_pending', 'device_locked',
                            'device_unlocked', 'device_offline',
                            'warranty_expiring', 'system_error')),
  severity                text not null default 'info'
                           check (severity in ('info', 'warning', 'critical')),
  customer_id             uuid references public.customers (id) on delete set null,
  credit_plan_id          uuid references public.credit_plans (id) on delete set null,
  installment_id          uuid references public.installments (id) on delete set null,
  device_installation_id  uuid references public.device_installations (id) on delete set null,
  dedupe_key              text not null,
  status                  text not null default 'open'
                           check (status in ('open', 'resolved', 'dismissed')),
  resolved_at             timestamptz,
  resolved_by             uuid references public.profiles (id),
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  unique (dedupe_key, status)
);

create index alerts_store_status_idx   on public.alerts (store_id, status);
create index alerts_customer_idx       on public.alerts (customer_id, created_at desc);
create index alerts_installment_idx    on public.alerts (installment_id);
create index alerts_type_idx           on public.alerts (alert_type, created_at desc);
create index alerts_created_idx        on public.alerts (created_at desc);

-- Registro de cada intento de envio de una notificacion
create table public.notification_deliveries (
  id                   uuid primary key default gen_random_uuid(),
  store_id             uuid not null references public.stores (id) on delete restrict,
  alert_id             uuid references public.alerts (id) on delete set null,
  customer_id          uuid not null references public.customers (id) on delete restrict,
  channel              text not null check (channel in ('whatsapp', 'push', 'sms')),
  template             text not null,
  status               text not null default 'pending'
                        check (status in ('pending', 'sent', 'delivered',
                        'read', 'failed', 'skipped')),
  provider_message_id  text,
  error                text,
  sent_at              timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

create index notification_deliveries_alert_idx    on public.notification_deliveries (alert_id);
create index notification_deliveries_customer_idx on public.notification_deliveries (customer_id, created_at desc);
create index notification_deliveries_status_idx   on public.notification_deliveries (status);

-- Conversaciones de WhatsApp. El numero se asocia al cliente solo
-- despues de un mecanismo de verificacion, no por el numero alone.
create table public.whatsapp_conversations (
  id                  uuid primary key default gen_random_uuid(),
  store_id            uuid not null references public.stores (id) on delete restrict,
  customer_id         uuid not null references public.customers (id) on delete restrict,
  wa_phone            text not null,
  verification_status text not null default 'unverified'
                       check (verification_status in
                       ('unverified', 'verified', 'blocked')),
  last_message_at     timestamptz,
  handoff_to_human    boolean not null default false,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (store_id, wa_phone)
);

create index whatsapp_conversations_customer_idx on public.whatsapp_conversations (customer_id);
create index whatsapp_conversations_phone_idx    on public.whatsapp_conversations (wa_phone);

-- Triggers updated_at
create trigger alerts_set_updated_at before update on public.alerts
  for each row execute function public.set_updated_at();
create trigger notification_deliveries_set_updated_at before update on public.notification_deliveries
  for each row execute function public.set_updated_at();
create trigger whatsapp_conversations_set_updated_at before update on public.whatsapp_conversations
  for each row execute function public.set_updated_at();

-- Seguridad por defecto
alter table public.alerts                    enable row level security;
alter table public.notification_deliveries   enable row level security;
alter table public.whatsapp_conversations    enable row level security;

revoke all on table public.alerts, public.notification_deliveries,
                    public.whatsapp_conversations
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;