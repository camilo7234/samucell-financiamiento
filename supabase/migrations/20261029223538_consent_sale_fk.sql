-- Vincula cada consentimiento a la venta exacta y garantiza que
-- el cliente del consentimiento sea el mismo cliente de la venta.

alter table public.sales
  add constraint sales_id_customer_id_key unique (id, customer_id);

alter table public.customer_consents
  add constraint customer_consents_sale_customer_fkey
  foreign key (sale_id, customer_id)
  references public.sales (id, customer_id)
  on delete restrict;

create index if not exists idx_customer_consents_sale_id
  on public.customer_consents (sale_id)
  where sale_id is not null;