-- Afhandeling per pagina: de redactie legt per URL binnen een signaal vast of het
-- gefixt is, genegeerd wordt of in behandeling is. "Open" = geen rij.
--
-- De tabel was nog leeg; we richten hem daarom opnieuw in. De RLS-policies (alleen
-- teamleden mogen lezen, zetten, wijzigen en verwijderen) blijven van kracht.

drop table if exists public.afvinkingen;

create table public.afvinkingen (
  bevinding_id   text        not null,          -- vingerafdruk van het signaal (data-id)
  url            text        not null,          -- de pagina binnen het signaal
  familie        text        not null,
  status         text        not null check (status in ('in_behandeling', 'gefixt', 'negeren')),
  bewijs_hash    text        not null,          -- waarde(n) op die pagina bij het afhandelen
  datum_controle text        not null,          -- controledatum van het tabblad bij het afhandelen
  notitie        text,
  door           text,
  bijgewerkt_op  timestamptz not null default now(),
  primary key (bevinding_id, url)
);

alter table public.afvinkingen enable row level security;

create policy "team leest vinkjes" on public.afvinkingen
  for select to authenticated using ((select private.is_teamlid()));
create policy "team zet vinkjes" on public.afvinkingen
  for insert to authenticated with check ((select private.is_teamlid()));
create policy "team wijzigt vinkjes" on public.afvinkingen
  for update to authenticated
  using ((select private.is_teamlid())) with check ((select private.is_teamlid()));
create policy "team haalt vinkjes weg" on public.afvinkingen
  for delete to authenticated using ((select private.is_teamlid()));

-- Wie het deed en wanneer, komt van de server en niet uit de browser.
create or replace function public.afvinking_stempel() returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.door := coalesce(auth.jwt() ->> 'email', new.door);
  new.bijgewerkt_op := now();
  return new;
end;
$$;

create trigger afvinkingen_stempel
  before insert or update on public.afvinkingen
  for each row execute function public.afvinking_stempel();

revoke all on function public.afvinking_stempel() from public, anon, authenticated;
