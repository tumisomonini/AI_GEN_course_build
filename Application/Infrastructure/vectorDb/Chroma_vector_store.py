"""Vector store adapter factory for Chroma.

This module mirrors Application/Infrastructure/vectorDb/Astra_vector_store.py
so existing dependency code can switch vector DBs.
"""

from Application.Ports.Chroma_repo import ChromaRepo


def get_chroma_vector_store(collection_name: str = 'syllabus_chunks'):
    repo = ChromaRepo(collection_name)
    return repo.vector_store

