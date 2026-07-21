create schema if not exists extensions;
create extension if not exists vector with schema extensions;
create extension if not exists pg_trgm with schema extensions;

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    source_url text not null,
    storage_path text,
    department text,
    document_type text,
    language text,
    academic_year text,
    published_date date,
    effective_date date,
    version text,
    status text not null default 'processing'
        check (status in ('processing', 'current', 'superseded', 'archived', 'failed')),
    supersedes_document_id uuid references documents(id),
    checksum text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists pages (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    pdf_page_number integer not null check (pdf_page_number > 0),
    printed_page_number text,
    page_text text not null,
    section_title text,
    created_at timestamptz not null default now(),
    unique (document_id, pdf_page_number)
);

create table if not exists sections (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    parent_section_id uuid references sections(id) on delete set null,
    title text not null,
    section_type text,
    article_number text,
    hierarchy_level integer,
    page_start integer not null check (page_start > 0),
    page_end integer not null check (page_end >= page_start)
);

create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    page_id uuid references pages(id) on delete cascade,
    section_id uuid references sections(id) on delete set null,
    chunk_index integer not null,
    chunk_text text not null,
    embedding_text text not null,
    section_title text,
    article_number text,
    pdf_page_start integer not null check (pdf_page_start > 0),
    pdf_page_end integer not null check (pdf_page_end >= pdf_page_start),
    printed_page_start text,
    printed_page_end text,
    language text,
    academic_year text,
    document_status text,
    token_count integer,
    embedding extensions.vector(768) not null,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_index)
);

alter table documents enable row level security;
alter table pages enable row level security;
alter table sections enable row level security;
alter table chunks enable row level security;

drop policy if exists "read current documents" on documents;
create policy "read current documents"
on documents for select to anon, authenticated
using (status = 'current');

drop policy if exists "read pages of current documents" on pages;
create policy "read pages of current documents"
on pages for select to anon, authenticated
using (exists (
    select 1 from documents d
    where d.id = pages.document_id and d.status = 'current'
));

drop policy if exists "read sections of current documents" on sections;
create policy "read sections of current documents"
on sections for select to anon, authenticated
using (exists (
    select 1 from documents d
    where d.id = sections.document_id and d.status = 'current'
));

drop policy if exists "read chunks of current documents" on chunks;
create policy "read chunks of current documents"
on chunks for select to anon, authenticated
using (exists (
    select 1 from documents d
    where d.id = chunks.document_id and d.status = 'current'
));

grant select on documents, pages, sections, chunks to anon, authenticated;
