-- sales: ventas de contado y credito, con fotografia historica de precios.
-- La TEA se calcula y guarda para cumplir el deber de informacion de la
-- Ley 1480 de 2011. Sin GPS, sin IP, sin datos de ubicacion.

create table public.sales (
  id               uuid primary key default gen_random_uuid(),
  store_id         uuid not null references public.stores (id) on delete restrict,
  sale_number      bigint generated always as identity,
  customer_id      uuid not null references public.customers (id) on delete restrict,
  sale_type        text not null check (sale_type in ('cash', 'credit')),
  sale_status      text not null default 'draft'
                    check (sale_status in ('draft', 'confirmed', 'cancelled')),
  subtotal_amount  numeric(14,2) not null check (subtotal_amount >= 0),
  discount_amount  numeric(14,2) not null default 0 check (discount_amount >= 0),
  total_amount     numeric(14,2) not null check (total_amount >= 0),
  payment_status   text not null default 'pending'
                    check (payment_status in ('pending', 'partial', 'paid')),
  sold_at          timestamptz not null default now(),
  confirmed_at     timestamptz,
  confirmed_by     uuid references public.profiles (id),
  cancelled_at     timestamptz,
  cancelled_by     uuid references public.profiles (id),
  cancel_reason    text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (store_id, sale_number)
);

create index sales_store_status_idx   on public.sales (store_id, sale_status);
create index sales_customer_idx       on public.sales (customer_id, sold_at desc);
create index sales_sold_at_idx        on public.sales (sold_at desc);
create index sales_payment_status_idx on public.sales (payment_status);

-- Detalle de la venta. description_snapshot conserva el texto del equipo
-- aunque el producto cambie despues.
create table public.sale_items (
  id                   uuid primary key default gen_random_uuid(),
  sale_id              uuid not null references public.sales (id) on delete cascade,
  sale_status          text not null check (sale_status in ('draft', 'confirmed', 'cancelled')),
  inventory_item_id    uuid not null references public.inventory_items (id) on delete restrict,
  description_snapshot text not null,
  unit_price_amount    numeric(14,2) not null check (unit_price_amount >= 0),
  quantity             integer not null default 1 check (quantity = 1),
  total_amount         numeric(14,2) not null check (total_amount >= 0),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

create index sale_items_sale_idx on public.sale_items (sale_id);
create index sale_items_item_idx on public.sale_items (inventory_item_id);

-- Un equipo fisico no puede estar en dos ventas activas (borrador o confirmada)
create unique index sale_items_one_active_sale_per_item
  on public.sale_items (inventory_item_id)
  where sale_status in ('draft', 'confirmed');

-- Plan de credito. Fotografia historica: si cambia la tasa o el redondeo,
-- los creditos ya formalizados no se modifican.
create table public.credit_plans (
  id                       uuid primary key default gen_random_uuid(),
  store_id                 uuid not null references public.stores (id) on delete restrict,
  sale_id                  uuid not null unique references public.sales (id) on delete restrict,
  initial_percentage       numeric(5,2) not null check
                            (initial_percentage >= 0 and initial_percentage <= 100),
  initial_amount           numeric(14,2) not null check (initial_amount >= 0),
  financed_amount          numeric(14,2) not null check (financed_amount > 0),
  nominal_rate             numeric(9,6) not null check (nominal_rate >= 0),
  effective_annual_rate    numeric(9,6) not null check (effective_annual_rate >= 0),
  interest_amount          numeric(14,2) not null check (interest_amount >= 0),
  total_obligation_amount  numeric(14,2) not null check (total_obligation_amount > 0),
  installment_count        integer not null check (installment_count between 1 and 60),
  installment_amount       numeric(14,2) not null check (installment_amount > 0),
  frequency                text not null default 'monthly'
                            check (frequency in ('monthly')),
  purchase_date            date not null,
  first_due_date           date not null,
  rounding_rule            text not null default 'ceil_last_installment'
                            check (rounding_rule in ('ceil_last_installment')),
  due_date_policy          text not null default 'last_day_of_month'
                            check (due_date_policy in ('last_day_of_month')),
  liquidation_method       text not null default 'fixed_interest_on_financed'
                            check (liquidation_method in ('fixed_interest_on_financed')),
  status                   text not null default 'active'
                            check (status in ('active', 'paid', 'cancelled')),
  calculation_version      text not null default 'v1',
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);

create index credit_plans_store_status_idx on public.credit_plans (store_id, status);
create index credit_plans_first_due_idx    on public.credit_plans (first_due_date);

create table public.installments (
  id                 uuid primary key default gen_random_uuid(),
  credit_plan_id     uuid not null references public.credit_plans (id) on delete restrict,
  installment_number integer not null check (installment_number >= 1),
  due_date           date not null,
  principal_amount   numeric(14,2) not null check (principal_amount >= 0),
  interest_amount    numeric(14,2) not null check (interest_amount >= 0),
  total_amount       numeric(14,2) not null check (total_amount > 0),
  paid_amount        numeric(14,2) not null default 0 check (paid_amount >= 0),
  status             text not null default 'pending'
                      check (status in ('pending', 'paid', 'overdue', 'cancelled')),
  paid_at            timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (credit_plan_id, installment_number)
);

create index installments_plan_idx   on public.installments (credit_plan_id, installment_number);
create index installments_due_idx    on public.installments (due_date, status);
create index installments_status_idx on public.installments (status);

-- Garantia de producto (fabricante o vendedor). Distinta de la garantia mobiliaria.
create table public.product_warranties (
  id                uuid primary key default gen_random_uuid(),
  store_id          uuid not null references public.stores (id) on delete restrict,
  inventory_item_id uuid not null references public.inventory_items (id) on delete restrict,
  sale_id           uuid references public.sales (id) on delete set null,
  starts_on         date not null,
  ends_on           date not null,
  status            text not null default 'active'
                     check (status in ('active', 'expired', 'claimed', 'closed')),
  terms             text,
  notes             text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint product_warranties_dates check (ends_on > starts_on)
);

create index product_warranties_item_idx on public.product_warranties (inventory_item_id);
create index product_warranties_ends_idx on public.product_warranties (ends_on, status);

-- Triggers updated_at
create trigger sales_set_updated_at before update on public.sales
  for each row execute function public.set_updated_at();
create trigger sale_items_set_updated_at before update on public.sale_items
  for each row execute function public.set_updated_at();
create trigger credit_plans_set_updated_at before update on public.credit_plans
  for each row execute function public.set_updated_at();
create trigger installments_set_updated_at before update on public.installments
  for each row execute function public.set_updated_at();
create trigger product_warranties_set_updated_at before update on public.product_warranties
  for each row execute function public.set_updated_at();

-- Sincroniza el estado de la venta en cada item, para que el indice parcial
-- de venta unica por equipo funcione sin subconsultas.
create or replace function public.sync_sale_item_status()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  update public.sale_items
  set sale_status = new.sale_status
  where sale_id = new.id;
  return new;
end;
$$;

create trigger sales_sync_item_status
  after update of sale_status on public.sales
  for each row execute function public.sync_sale_item_status();

-- Seguridad por defecto
alter table public.sales               enable row level security;
alter table public.sale_items          enable row level security;
alter table public.credit_plans        enable row level security;
alter table public.installments        enable row level security;
alter table public.product_warranties  enable row level security;

revoke all on table public.sales, public.sale_items, public.credit_plans,
                    public.installments, public.product_warranties
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;