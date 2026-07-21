create index if not exists documents_source_url_idx on documents (source_url);
create index if not exists documents_source_checksum_idx on documents (source_url, checksum);
create index if not exists documents_status_type_idx on documents (status, document_type);
create index if not exists pages_document_page_idx on pages (document_id, pdf_page_number);
create index if not exists sections_document_article_idx on sections (document_id, article_number);
create index if not exists sections_title_trgm_idx on sections using gin (title extensions.gin_trgm_ops);
create index if not exists chunks_document_idx on chunks (document_id);
create index if not exists chunks_article_idx on chunks (article_number);
create index if not exists chunks_embedding_hnsw_idx
    on chunks using hnsw (embedding extensions.vector_cosine_ops);
create index if not exists chunks_text_search_idx
    on chunks using gin (to_tsvector('simple', embedding_text));
create index if not exists chunks_section_trgm_idx
    on chunks using gin (section_title extensions.gin_trgm_ops);
