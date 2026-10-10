-- inventory: catalogo de productos, equipos fisicos con IMEI y movimientos.
-- Un equipo fisico es la unidad de control. El IMEI es obligatorio y unico.
-- Sin GPS, sin IP, sin datos de ubicacion.

create table public.products (
  id                   uuid primary key default gen_random_uuid(),
  brand                text not null,
  model                text not null,
  variant              text,
  storage_capacity     text,
  ram_capacity         text,
  color                text,
  operating_system     text not null check (operating_system in
                        ('android', 'ios', 'other')),
  compatibility_status text not null default 'untested'
                        check (compatibility_status in
                        ('compatible', 'incompatible', 'untested')),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

create index products_brand_model_idx on public.products (lower(brand), lower(model));
create table public.suppliers (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  document_number text,
  phone           text,
  address         text,
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger suppliers_set_updated_at before update on public.suppliers
  for each row execute function public.set_updated_at();

alter table public.suppliers enable row level security;
revoke all on table public.suppliers from anon, authenticated;

create table public.inventory_items (
  id                 uuid primary key default gen_random_uuid(),
  store_id           uuid not null references public.stores (id) on delete restrict,
  product_id         uuid not null references public.products (id) on delete restrict,
  supplier_id        uuid references public.suppliers (id) on delete set null,
  imei_1             text not null unique check (imei_1 ~ '^[0-9]{14,16}$'),
  imei_2             text unique check (imei_2 is null or imei_2 ~ '^[0-9]{14,16}$'),
  serial_number      text unique,
  condition          text not null check (condition in ('new', 'used')),
  cost_amount        numeric(14,2) not null check (cost_amount >= 0),
  sale_price_amount  numeric(14,2) not null check (sale_price_amount >= 0),
  status             text not null default 'available'
                      check (status in
                      ('available', 'reserved', 'sold', 'warranty', 'retired')),
  purchase_date      date not null,
  notes              text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  constraint inventory_items_imei_distinct
    check (imei_2 is null or imei_1 <> imei_2)
);

create index inventory_items_store_status_idx on public.inventory_items (store_id, status);
create index inventory_items_product_idx      on public.inventory_items (product_id);
create index inventory_items_imei_idx         on public.inventory_items (imei_1);

-- Historial de cambios de estado de cada equipo
create table public.inventory_movements (
  id                uuid primary key default gen_random_uuid(),
  store_id          uuid not null references public.stores (id) on delete restrict,
  inventory_item_id uuid not null references public.inventory_items (id) on delete restrict,
  movement_type     text not null check (movement_type in
                     ('purchase', 'transfer', 'reserve', 'sale', 'return',
                      'warranty', 'retire', 'adjustment')),
  from_status       text,
  to_status         text not null,
  reference_type    text,
  reference_id      text,
  performed_by      uuid references public.profiles (id),
  notes             text,
  created_at        timestamptz not null default now()
);

create index inventory_movements_item_idx   on public.inventory_movements (inventory_item_id, created_at desc);
create index inventory_movements_store_idx  on public.inventory_movements (store_id, created_at desc);

create trigger inventory_items_set_updated_at before update on public.inventory_items
  for each row execute function public.set_updated_at();
create trigger products_set_updated_at before update on public.products
  for each row execute function public.set_updated_at();

alter table public.products             enable row level security;
alter table public.inventory_items      enable row level security;
alter table public.inventory_movements  enable row level security;

revoke all on table public.products, public.inventory_items, public.inventory_movements
  from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;