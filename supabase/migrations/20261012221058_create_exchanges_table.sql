-- Create the table
create table exchanges (
  id uuid primary key default gen_random_uuid(),
  model text not null,
  instructions text not null,
  query text,
  response text,
  start_datetime timestamptz,
  end_datetime timestamptz
);

-- Grant the privileges the role needs, which is read access
grant select on public.exchanges to anon;

grant select, insert, update
on table public.exchanges
to service_role;

-- Enable row level security for the table
alter table exchanges enable row level security;

-- Create a policy to allow the anon role to read from the exchanges table
create policy "public can read exchanges"
on public.exchanges
for select to anon
using (true);