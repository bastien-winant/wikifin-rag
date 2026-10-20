-- Create the table
create table responses (
  id text primary key,
  exchange_id uuid references exchanges(id),
  created_at timestamptz not null,
  completed_at timestamptz not null,
  model text not null,
  input_tokens integer not null,
  output_tokens integer not null,
  input_cost numeric not null,
  output_cost numeric not null
);

-- Grant the privileges the role needs, which is read access
grant select on public.responses to anon;

grant select, insert, update
on table public.responses
to service_role;

-- Enable row level security for the table
alter table responses enable row level security;

-- Create a policy to allow the anon role to read from the responses table
create policy "public can read responses"
on public.responses
for select to anon
using (true);