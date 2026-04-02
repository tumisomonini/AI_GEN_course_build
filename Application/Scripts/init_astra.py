"""AstraDB initialization module."""

def init_astra(collection_name: str, astra_token: str, astra_api_endpoint: str):
    """Initialize AstraDB vector store.
    
    Args:
        collection_name: Collection name in AstraDB
        astra_token: AstraDB API token
        astra_api_endpoint: AstraDB API endpoint
    """
    try:
        from Infrastructure.vectorDb.Astra_vector_store import AstraVectorStore
        store = AstraVectorStore(collection_name, astra_token, astra_api_endpoint)
        print(f"AstraDB collection '{collection_name}' initialized successfully!")
    except Exception as e:
        print(f"Error initializing AstraDB: {e}")
        raise
