-- Restaura la politica RLS de lectura de profiles para samucell_backend.
-- Motivo: el diagnostico del 10-nov-2026 mostro que en la base solo existia
-- profiles_backend_read_v2 (rol samucell_backend_v2), mientras el backend
-- se conecta como samucell_backend. Idempotente.

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