-- Create the table
create table tool_calls (
  id text primary key,
  call_id text not null,
  response_id text references responses(id),
  name text not null,
  arguments json
);

-- Grant the privileges the role needs, which is read access
grant select on public.tool_calls to anon;

grant select, insert, update
on table public.tool_calls
to service_role;

-- Enable row level security for the table
alter table tool_calls enable row level security;

-- Create a policy to allow the anon role to read from the tool_calls table
create policy "public can read responses"
on public.tool_calls
for select to anon
using (true);