# Wrapper/alias for Ports.Astra_repo vector_store - keeps compatibility
from Application.Ports.Astra_repo import AstraRepo  # Compatible with updated init

def get_astra_vector_store(collection_name: str = 'syllabus_chunks'):
    repo = AstraRepo(collection_name)
    return repo.vector_store
