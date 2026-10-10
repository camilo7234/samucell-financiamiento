-- core_security: base del sistema Samucell.
-- Crea sucursales, perfiles, parametros, auditoria inmutable y seguridad por defecto.
-- Sin GPS, sin IP, sin datos de ubicacion. Todas las tablas con RLS activado.

-- Funcion generica para mantener updated_at
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Sucursales
create table public.stores (
  id          uuid primary key default gen_random_uuid(),
  code        text not null unique check (code ~ '^[A-Z0-9-]{3,30}$'),
  name        text not null,
  address     text,
  phone       text,
  is_active   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

insert into public.stores (code, name, address)
values ('SAMUCELL-IPI', 'Samucell Ipiales', 'Ipiales, Nariño, Colombia');

-- Perfiles de usuarios administrativos (vinculados a Supabase Auth)
create table public.profiles (
  id          uuid primary key references auth.users (id) on delete restrict,
  full_name   text not null,
  role        text not null check (role in ('admin', 'operator')),
  is_active   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Acceso de cada usuario a cada sucursal
create table public.profile_stores (
  profile_id  uuid not null references public.profiles (id) on delete cascade,
  store_id    uuid not null references public.stores (id) on delete restrict,
  created_at  timestamptz not null default now(),
  primary key (profile_id, store_id)
);
create index profile_stores_store_id_idx on public.profile_stores (store_id);

-- Parametros del sistema (nunca valores fijos en el codigo)
create table public.system_settings (
  id           uuid primary key default gen_random_uuid(),
  key          text not null unique
               check (key ~ '^[a-z0-9_]+(\.[a-z0-9_]+)+$' and key !~ '^gps\.'),
  value        jsonb not null,
  description  text not null,
  version      integer not null default 1,
  updated_by   uuid references public.profiles (id),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- Auditoria: solo insercion, sin IP
create table public.audit_logs (
  id             bigint generated always as identity primary key,
  actor_user_id  uuid,
  action         text not null,
  entity_type    text not null,
  entity_id      text,
  store_id       uuid references public.stores (id),
  before_data    jsonb,
  after_data     jsonb,
  user_agent     text,
  created_at     timestamptz not null default now()
);
create index audit_logs_entity_idx  on public.audit_logs (entity_type, entity_id);
create index audit_logs_actor_idx   on public.audit_logs (actor_user_id, created_at desc);
create index audit_logs_created_idx on public.audit_logs (created_at desc);
create index audit_logs_action_idx  on public.audit_logs (action);

create or replace function public.audit_logs_block_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'audit_logs es de solo insercion';
end;
$$;

create trigger audit_logs_no_update_delete
  before update or delete on public.audit_logs
  for each row execute function public.audit_logs_block_mutation();

create trigger audit_logs_no_truncate
  before truncate on public.audit_logs
  for each statement execute function public.audit_logs_block_mutation();

-- Triggers updated_at
create trigger stores_set_updated_at before update on public.stores
  for each row execute function public.set_updated_at();
create trigger profiles_set_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();
create trigger system_settings_set_updated_at before update on public.system_settings
  for each row execute function public.set_updated_at();

-- Seguridad por defecto: RLS activado y sin acceso para anon/authenticated.
-- Solo el backend (rol de servicio / conexion directa) accede a los datos.
alter table public.stores          enable row level security;
alter table public.profiles        enable row level security;
alter table public.profile_stores  enable row level security;
alter table public.system_settings enable row level security;
alter table public.audit_logs      enable row level security;

revoke all on table public.stores, public.profiles, public.profile_stores,
                    public.system_settings, public.audit_logs
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;

alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;

-- Parametros iniciales (valores provisionales; el abogado valida los legales)
insert into public.system_settings (key, value, description) values
  ('app.timezone',                       '"America/Bogota"'::jsonb, 'Zona horaria operativa'),
  ('feature.device_lock_enabled',        'false'::jsonb,            'Interruptor del bloqueo remoto. Apagado hasta validacion legal'),
  ('collections.min_notices_before_lock','3'::jsonb,                'Avisos minimos antes de bloquear (provisional)'),
  ('collections.min_days_between_notices','7'::jsonb,               'Dias minimos entre avisos de cobranza (Ley 2300)'),
  ('collections.max_contacts_per_day',   '1'::jsonb,                'Maximo de contactos de cobranza por dia (Ley 2300)'),
  ('collections.allowed_hours',
     '{"mon_fri":["07:00","19:00"],"sat":["08:00","15:00"],"sun_holidays":false}'::jsonb,
     'Horario permitido de contacto de cobranza (Ley 2300)'),
  ('collections.allow_reference_contacts','false'::jsonb,           'Prohibido contactar referencias personales para cobrar'),
  ('collections.grace_days',             'null'::jsonb,             'Dias de gracia tras mora. Lo define el abogado'),
  ('credit.usury_rate_ea',               'null'::jsonb,             'Tasa de usura vigente (E.A.). Actualizar cada mes'),
  ('privacy.habeas_data_channel',        'null'::jsonb,             'Canal de atencion de habeas data'),
  ('privacy.privacy_notice_url',         'null'::jsonb,             'URL del aviso de privacidad');