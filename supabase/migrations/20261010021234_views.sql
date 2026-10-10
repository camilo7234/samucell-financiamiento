-- views: vistas de lectura para saldos, cartera, mora y dashboard.
-- Los saldos nunca se guardan como campos editables: se calculan aqui.
-- Sin GPS, sin IP, sin datos de ubicacion.

-- Saldo pendiente por plan de credito
create or replace view public.v_credit_balance as
select
  cp.id as credit_plan_id,
  cp.sale_id,
  cp.store_id,
  sa.customer_id,
  c.full_name as customer_name,
  cp.total_obligation_amount,
  coalesce(sum(i.total_amount), 0) as total_in_installments,
  coalesce(sum(i.paid_amount), 0) as total_paid,
  cp.total_obligation_amount - coalesce(sum(i.paid_amount), 0) as balance_due,
  count(i.id) filter (where i.status = 'overdue') as overdue_count,
  coalesce(sum(i.total_amount - i.paid_amount) filter (where i.status = 'overdue'), 0) as overdue_amount
from public.credit_plans cp
join public.sales sa on sa.id = cp.sale_id
join public.customers c on c.id = sa.customer_id
left join public.installments i on i.credit_plan_id = cp.id and i.status <> 'cancelled'
group by cp.id, cp.sale_id, cp.store_id, sa.customer_id, c.full_name,
         cp.total_obligation_amount;

-- Cuotas vencidas con dias de mora
create or replace view public.v_overdue_installments as
select
  i.id as installment_id,
  i.credit_plan_id,
  cp.sale_id,
  cp.store_id,
  sa.customer_id,
  c.full_name as customer_name,
  i.installment_number,
  i.due_date,
  i.total_amount,
  i.paid_amount,
  i.total_amount - i.paid_amount as amount_due,
  (current_date - i.due_date) as days_overdue
from public.installments i
join public.credit_plans cp on cp.id = i.credit_plan_id
join public.sales sa on sa.id = cp.sale_id
join public.customers c on c.id = sa.customer_id
where i.status = 'overdue'
  and i.paid_amount < i.total_amount;

-- Cartera por cliente
create or replace view public.v_portfolio_by_customer as
select
  c.id as customer_id,
  c.full_name as customer_name,
  c.document_type,
  c.document_number,
  sa.store_id,
  count(distinct cp.id) as active_credits,
  coalesce(sum(v.balance_due), 0) as total_balance_due,
  coalesce(sum(v.overdue_amount), 0) as total_overdue
from public.customers c
join public.sales sa on sa.customer_id = c.id
join public.credit_plans cp on cp.sale_id = sa.id and cp.status = 'active'
left join public.v_credit_balance v on v.credit_plan_id = cp.id
group by c.id, c.full_name, c.document_type, c.document_number, sa.store_id;

-- Resumen para el dashboard (una fila por sucursal)
create or replace view public.v_dashboard_summary as
select
  s.id as store_id,
  s.code as store_code,
  s.name as store_name,
  (select count(*) from public.sales sa
    where sa.store_id = s.id
      and sa.sale_status = 'confirmed'
      and sa.sold_at::date = current_date) as sales_today,
  (select count(*) from public.sales sa
    where sa.store_id = s.id
      and sa.sale_status = 'confirmed'
      and date_trunc('month', sa.sold_at) = date_trunc('month', current_date)) as sales_this_month,
  (select count(*) from public.inventory_items ii
    where ii.store_id = s.id and ii.status = 'available') as inventory_available,
  (select count(*) from public.inventory_items ii
    where ii.store_id = s.id and ii.status = 'reserved') as inventory_reserved,
  (select count(*) from public.inventory_items ii
    where ii.store_id = s.id and ii.status = 'sold') as inventory_sold,
  (select count(*) from public.credit_plans cp
    where cp.store_id = s.id and cp.status = 'active') as active_credits,
  (select count(*) from public.installments i
    join public.credit_plans cp on cp.id = i.credit_plan_id
    where cp.store_id = s.id and i.status = 'overdue') as overdue_installments,
  (select count(distinct sa.customer_id) from public.sales sa
    join public.credit_plans cp on cp.sale_id = sa.id
    join public.installments i on i.credit_plan_id = cp.id
    where sa.store_id = s.id and i.status = 'overdue') as customers_in_arrears,
  (select count(*) from public.device_installations di
    where di.store_id = s.id and di.device_status = 'blocked') as devices_blocked
from public.stores s;