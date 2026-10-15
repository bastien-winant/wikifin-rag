-- Create the table
create table feedback (
  id uuid primary key default gen_random_uuid(),
  exchange_id uuid references exchanges(id),
  source text not null,
  relevance text,
  explanation text,
  score text,
  created_at timestamptz default now()
);

-- Grant the privileges the role needs, which is read access
grant select on public.feedback to anon;

grant select, insert, update
on table public.feedback
to service_role;

-- Enable row level security for the table
alter table feedback enable row level security;

-- Create a policy to allow the anon role to read from the feedback table
create policy "public can read responses"
on public.feedback
for select to anon
using (true);