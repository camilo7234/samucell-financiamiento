-- Rol del backend con privilegios mínimos.
-- Idempotente: seguro si el rol ya existe por prueba manual.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'samucell_backend') then
    create role samucell_backend
      login
      nosuperuser
      nocreatedb
      nocreaterole
      noinherit
      nobypassrls;
  end if;
end $$;

grant usage on schema public to samucell_backend;

grant select on public.profiles to samucell_backend;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'profiles'
      and policyname = 'profiles_backend_read'
  ) then
    create policy profiles_backend_read
      on public.profiles
      for select
      to samucell_backend
      using (true);
  end if;
end $$;