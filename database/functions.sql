create or replace function match_chunks(
    p_query_embedding extensions.vector(768),
    p_match_count integer default 12,
    p_document_type text default null,
    p_language text default null,
    p_status text default 'current'
)
returns table (
    chunk_id uuid,
    document_id uuid,
    document_title text,
    source_url text,
    chunk_text text,
    section_title text,
    article_number text,
    pdf_page_start integer,
    pdf_page_end integer,
    printed_page_start text,
    printed_page_end text,
    published_date date,
    effective_date date,
    document_status text,
    language text,
    score double precision
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
    select
        c.id,
        c.document_id,
        d.title,
        d.source_url,
        c.chunk_text,
        c.section_title,
        c.article_number,
        c.pdf_page_start,
        c.pdf_page_end,
        c.printed_page_start,
        c.printed_page_end,
        d.published_date,
        d.effective_date,
        d.status,
        c.language,
        1 - (c.embedding <=> p_query_embedding) as score
    from chunks c
    join documents d on d.id = c.document_id
    where d.status = p_status
      and (p_document_type is null or d.document_type = p_document_type)
      and (p_language is null or c.language = p_language)
    order by c.embedding <=> p_query_embedding
    limit greatest(1, least(p_match_count, 100));
$$;

create or replace function search_chunks_keyword(
    p_query_text text,
    p_match_count integer default 12,
    p_document_type text default null,
    p_language text default null,
    p_status text default 'current'
)
returns table (
    chunk_id uuid,
    document_id uuid,
    document_title text,
    source_url text,
    chunk_text text,
    section_title text,
    article_number text,
    pdf_page_start integer,
    pdf_page_end integer,
    printed_page_start text,
    printed_page_end text,
    published_date date,
    effective_date date,
    document_status text,
    language text,
    score real
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
    with query as (
        select websearch_to_tsquery('simple', p_query_text) as value
    )
    select
        c.id,
        c.document_id,
        d.title,
        d.source_url,
        c.chunk_text,
        c.section_title,
        c.article_number,
        c.pdf_page_start,
        c.pdf_page_end,
        c.printed_page_start,
        c.printed_page_end,
        d.published_date,
        d.effective_date,
        d.status,
        c.language,
        ts_rank_cd(to_tsvector('simple', c.embedding_text), query.value) as score
    from chunks c
    join documents d on d.id = c.document_id
    cross join query
    where d.status = p_status
      and query.value @@ to_tsvector('simple', c.embedding_text)
      and (p_document_type is null or d.document_type = p_document_type)
      and (p_language is null or c.language = p_language)
    order by score desc
    limit greatest(1, least(p_match_count, 100));
$$;

create or replace function search_sections(
    p_query_text text,
    p_match_count integer default 8,
    p_document_type text default null,
    p_language text default null,
    p_status text default 'current'
)
returns table (
    chunk_id uuid,
    document_id uuid,
    document_title text,
    source_url text,
    chunk_text text,
    section_title text,
    article_number text,
    pdf_page_start integer,
    pdf_page_end integer,
    printed_page_start text,
    printed_page_end text,
    published_date date,
    effective_date date,
    document_status text,
    language text,
    score real
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
    select
        c.id,
        c.document_id,
        d.title,
        d.source_url,
        c.chunk_text,
        c.section_title,
        c.article_number,
        c.pdf_page_start,
        c.pdf_page_end,
        c.printed_page_start,
        c.printed_page_end,
        d.published_date,
        d.effective_date,
        d.status,
        c.language,
        greatest(
            case
                when length(coalesce(c.section_title, '')) > 2
                 and p_query_text ilike '%' || c.section_title || '%'
                then 1.0
                else 0.0
            end,
            case
                when length(coalesce(c.article_number, '')) > 0
                 and p_query_text ilike '%' || c.article_number || '%'
                then 1.0
                else 0.0
            end,
            similarity(coalesce(c.section_title, ''), p_query_text),
            similarity(coalesce(c.article_number, ''), p_query_text)
        )::real as score
    from chunks c
    join documents d on d.id = c.document_id
    where d.status = p_status
      and (p_document_type is null or d.document_type = p_document_type)
      and (p_language is null or c.language = p_language)
      and (
          coalesce(c.section_title, '') % p_query_text
          or coalesce(c.article_number, '') % p_query_text
          or (
              length(coalesce(c.section_title, '')) > 2
              and p_query_text ilike '%' || c.section_title || '%'
          )
          or (
              length(coalesce(c.article_number, '')) > 0
              and p_query_text ilike '%' || c.article_number || '%'
          )
      )
    order by score desc
    limit greatest(1, least(p_match_count, 100));
$$;

grant execute on function match_chunks(extensions.vector, integer, text, text, text) to anon, authenticated;
grant execute on function search_chunks_keyword(text, integer, text, text, text) to anon, authenticated;
grant execute on function search_sections(text, integer, text, text, text) to anon, authenticated;
