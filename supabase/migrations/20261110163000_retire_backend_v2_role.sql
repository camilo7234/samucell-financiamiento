-- Retira el rol samucell_backend_v2 y su politica.
-- Motivo: rol con login creado fuera de las migraciones. Diagnostico del
-- 10-nov-2026: sin objetos propios; solo dependen de el una politica RLS, un
-- permiso de esquema y un permiso de tabla. Se conserva solo samucell_backend
-- (20261105120000_backend_role.sql).
-- Nota PG16+: el rol postgres tiene ADMIN OPTION sobre el, pero sin INHERIT
-- (lo creo supabase_admin). Para DROP OWNED hace falta INHERIT, que postgres
-- puede concederse a si mismo. La membresia se elimina junto con el rol.
-- Idempotente.

drop policy if exists profiles_backend_read_v2 on public.profiles;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'samucell_backend_v2') then
    execute format(
      'grant samucell_backend_v2 to %I with inherit true', current_user
    );
    drop owned by samucell_backend_v2;
    drop role samucell_backend_v2;
  end if;
end $$;