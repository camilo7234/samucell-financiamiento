-- devices: instalaciones de la app en equipos financiados, credenciales,
-- comandos remotos (lock/unlock/sync) y matriz de compatibilidad.
-- Sin GPS, sin ubicacion, sin comando wipe.

create table public.device_installations (
  id                      uuid primary key default gen_random_uuid(),
  store_id                uuid not null references public.stores (id) on delete restrict,
  inventory_item_id       uuid not null unique references public.inventory_items (id) on delete restrict,
  sale_id                 uuid not null references public.sales (id) on delete restrict,
  customer_id             uuid not null references public.customers (id) on delete restrict,
  installation_identifier text not null unique,
  app_version             text,
  android_version         text,
  manufacturer            text,
  model                   text,
  device_owner_status     text not null default 'pending_provisioning'
                           check (device_owner_status in
                           ('pending_provisioning', 'authorized', 'failed')),
  lock_task_status        text not null default 'untested'
                           check (lock_task_status in
                           ('untested', 'supported', 'partial', 'unsupported')),
  device_status           text not null default 'pending_provisioning'
                           check (device_status in
                           ('pending_provisioning', 'active', 'offline',
                            'blocked', 'unblocked', 'incompatible', 'retired')),
  last_seen_at            timestamptz,
  last_command_at         timestamptz,
  fcm_token_encrypted     text,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

create index device_installations_store_idx   on public.device_installations (store_id, device_status);
create index device_installations_sale_idx    on public.device_installations (sale_id);
create index device_installations_customer_idx on public.device_installations (customer_id);
create index device_installations_status_idx  on public.device_installations (device_status);
create index device_installations_last_seen_idx on public.device_installations (last_seen_at desc);

-- Credenciales rotables por instalacion. El hash nunca guarda el secreto.
create table public.device_credentials (
  id                      uuid primary key default gen_random_uuid(),
  device_installation_id  uuid not null references public.device_installations (id) on delete cascade,
  secret_hash             text not null,
  issued_at               timestamptz not null default now(),
  expires_at              timestamptz not null,
  revoked_at              timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

create index device_credentials_installation_idx on public.device_credentials (device_installation_id);
create index device_credentials_expires_idx      on public.device_credentials (expires_at);

-- Comandos remotos. Idempotentes y con expiracion.
-- Tipos permitidos: lock, unlock, sync. wipe y enable_gps estan prohibidos.
create table public.device_commands (
  id                      uuid primary key default gen_random_uuid(),
  device_installation_id  uuid not null references public.device_installations (id) on delete restrict,
  command_type            text not null check (command_type in ('lock', 'unlock', 'sync')),
  requested_by            uuid references public.profiles (id),
  reason                  text not null,
  previous_status         text,
  status                  text not null default 'pending'
                           check (status in
                           ('pending', 'sent', 'received', 'executed', 'failed', 'expired')),
  idempotency_key         text not null unique,
  issued_at               timestamptz not null default now(),
  expires_at              timestamptz not null,
  received_at             timestamptz,
  executed_at             timestamptz,
  error_code              text,
  result_metadata         jsonb,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

create index device_commands_installation_idx on public.device_commands (device_installation_id, issued_at desc);
create index device_commands_status_idx       on public.device_commands (status, expires_at);
create index device_commands_type_idx         on public.device_commands (command_type);

-- Matriz de compatibilidad por modelo de equipo
create table public.device_compatibility_matrix (
  id                   uuid primary key default gen_random_uuid(),
  manufacturer         text not null,
  model                text not null,
  android_version      text not null,
  security_patch       text,
  provisioning_method  text not null check (provisioning_method in
                        ('adb', 'qr', 'zero_touch', 'other')),
  device_owner_result  text not null check (device_owner_result in
                        ('yes', 'no', 'partial', 'untested')),
  lock_task_result     text not null check (lock_task_result in
                        ('yes', 'no', 'partial', 'untested')),
  uninstall_protected  text not null check (uninstall_protected in
                        ('yes', 'no', 'partial', 'untested')),
  reboot_result        text not null check (reboot_result in
                        ('ok', 'failed', 'untested')),
  fcm_result           text not null check (fcm_result in
                        ('ok', 'failed', 'untested')),
  polling_result       text not null check (polling_result in
                        ('ok', 'failed', 'untested')),
  factory_reset_result text not null check (factory_reset_result in
                        ('protected', 'vulnerable', 'untested')),
  observations         text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (manufacturer, model, android_version, provisioning_method)
);

-- Triggers updated_at
create trigger device_installations_set_updated_at before update on public.device_installations
  for each row execute function public.set_updated_at();
create trigger device_credentials_set_updated_at before update on public.device_credentials
  for each row execute function public.set_updated_at();
create trigger device_commands_set_updated_at before update on public.device_commands
  for each row execute function public.set_updated_at();
create trigger device_compatibility_matrix_set_updated_at before update on public.device_compatibility_matrix
  for each row execute function public.set_updated_at();

-- Seguridad por defecto
alter table public.device_installations        enable row level security;
alter table public.device_credentials          enable row level security;
alter table public.device_commands             enable row level security;
alter table public.device_compatibility_matrix enable row level security;

revoke all on table public.device_installations, public.device_credentials,
                    public.device_commands, public.device_compatibility_matrix
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;