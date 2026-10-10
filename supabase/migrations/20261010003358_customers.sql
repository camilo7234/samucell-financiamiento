-- customers: clientes, contactos, versiones de terminos y consentimientos.
-- Reglas: minimizacion de datos, consentimiento informado y prohibicion de
-- contactar referencias personales para cobranza (Ley 2300 de 2023).
-- Sin GPS, sin IP, sin datos de ubicacion.

create table public.customers (
  id              uuid primary key default gen_random_uuid(),
  full_name       text not null,
  document_type   text not null check (document_type in ('CC', 'CE', 'NIT', 'PAS')),
  document_number text not null,
  phone           text not null,
  address         text,
  status          text not null default 'active'
                  check (status in ('active', 'inactive', 'blocked')),
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (document_type, document_number)
);

create index customers_phone_idx on public.customers (phone);
create index customers_full_name_idx on public.customers (lower(full_name));

-- Contactos: solo para identificar al cliente, nunca para cobranza.
create table public.customer_contacts (
  id            uuid primary key default gen_random_uuid(),
  customer_id   uuid not null references public.customers (id) on delete cascade,
  contact_type  text not null check (contact_type in ('reference', 'alternate')),
  full_name     text not null,
  phone         text not null,
  relationship  text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index customer_contacts_customer_idx on public.customer_contacts (customer_id);

-- Versiones de documentos legales (terminos, aviso de privacidad, contrato)
create table public.terms_versions (
  id               uuid primary key default gen_random_uuid(),
  code             text not null,
  version          text not null,
  title            text not null,
  document_file_id uuid,
  published_at     timestamptz not null default now(),
  is_current       boolean not null default false,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (code, version)
);

create index terms_versions_current_idx on public.terms_versions (code, is_current);

-- Consentimientos del cliente. Sin tipo 'gps'.
create table public.customer_consents (
  id                uuid primary key default gen_random_uuid(),
  customer_id       uuid not null references public.customers (id) on delete restrict,
  sale_id           uuid,
  terms_version_id  uuid references public.terms_versions (id) on delete restrict,
  purpose           text not null check (purpose in
                      ('terms', 'privacy', 'data_processing', 'device_lock',
                       'collection_channel')),
  accepted_at       timestamptz not null default now(),
  channel           text not null check (channel in ('paper', 'digital', 'whatsapp')),
  evidence_file_id  uuid,
  revoked_at        timestamptz,
  revoked_reason    text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index customer_consents_customer_idx on public.customer_consents (customer_id);
create index customer_consents_purpose_idx  on public.customer_consents (purpose, accepted_at desc);

-- Un consentimiento activo por cliente, finalidad y version de documento
create unique index customer_consents_active_unique
  on public.customer_consents (customer_id, purpose, terms_version_id)
  where revoked_at is null;

-- Triggers updated_at
create trigger customers_set_updated_at before update on public.customers
  for each row execute function public.set_updated_at();
create trigger customer_contacts_set_updated_at before update on public.customer_contacts
  for each row execute function public.set_updated_at();
create trigger terms_versions_set_updated_at before update on public.terms_versions
  for each row execute function public.set_updated_at();
create trigger customer_consents_set_updated_at before update on public.customer_consents
  for each row execute function public.set_updated_at();

-- Seguridad por defecto
alter table public.customers         enable row level security;
alter table public.customer_contacts enable row level security;
alter table public.terms_versions    enable row level security;
alter table public.customer_consents enable row level security;

revoke all on table public.customers, public.customer_contacts,
                    public.terms_versions, public.customer_consents
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;