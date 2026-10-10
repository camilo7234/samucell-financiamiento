-- payments: pagos recibidos y su asignacion a cuotas.
-- Reglas: pagos completos por cuota, sin borrado fisico (solo anulacion),
-- idempotencia para evitar pagos duplicados. Sin GPS, sin IP.

create table public.payments (
  id               uuid primary key default gen_random_uuid(),
  store_id         uuid not null references public.stores (id) on delete restrict,
  sale_id          uuid not null references public.sales (id) on delete restrict,
  customer_id      uuid not null references public.customers (id) on delete restrict,
  amount           numeric(14,2) not null check (amount > 0),
  payment_method   text not null check (payment_method in ('cash', 'transfer')),
  reference        text,
  idempotency_key  text not null unique,
  received_at      timestamptz not null default now(),
  received_by      uuid references public.profiles (id),
  status           text not null default 'valid'
                    check (status in ('valid', 'voided')),
  voided_at        timestamptz,
  voided_by        uuid references public.profiles (id),
  void_reason      text,
  notes            text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint payments_void_requires_reason
    check (status = 'valid' or (voided_at is not null and void_reason is not null))
);

create index payments_sale_idx        on public.payments (sale_id, received_at desc);
create index payments_customer_idx    on public.payments (customer_id, received_at desc);
create index payments_store_idx       on public.payments (store_id, received_at desc);
create index payments_status_idx      on public.payments (status);
create index payments_reference_idx   on public.payments (reference)
  where reference is not null;

-- Asignacion de un pago a una cuota. Permite trazabilidad exacta
-- de que pago cubrio que cuota, sin guardar saldos editables.
create table public.payment_allocations (
  id             uuid primary key default gen_random_uuid(),
  payment_id     uuid not null references public.payments (id) on delete restrict,
  installment_id uuid not null references public.installments (id) on delete restrict,
  amount         numeric(14,2) not null check (amount > 0),
  created_at     timestamptz not null default now(),
  unique (payment_id, installment_id)
);

create index payment_allocations_payment_idx     on public.payment_allocations (payment_id);
create index payment_allocations_installment_idx on public.payment_allocations (installment_id);

-- Evita que un mismo pago se asigne dos veces a la misma cuota
-- (redundante con el unique, pero documenta la regla a nivel de indice)
create unique index payment_allocations_payment_installment_unique
  on public.payment_allocations (payment_id, installment_id);

-- Triggers updated_at
create trigger payments_set_updated_at before update on public.payments
  for each row execute function public.set_updated_at();

-- Seguridad por defecto
alter table public.payments             enable row level security;
alter table public.payment_allocations  enable row level security;

revoke all on table public.payments, public.payment_allocations
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;