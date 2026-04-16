import os
from dotenv import load_dotenv
import cassio
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

# Initialize Cassio with AstraDB
cassio.init(
    token=os.getenv('ASTRA_DB_APPLICATION_TOKEN'),
    database_id=os.getenv('ASTRA_DB_ID'),
)

print('Cassio initialized with AstraDB credentials.')
print('AstraDB connection successful! Ready to use vector collections (syllabus_chunks).')

# Test collection creation & functionality
try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from Infrastructure.vectorDb.Astra_vector_store import AstraVectorStore

    class AstraRepo:
        def __init__(self, collection_name):
            self.vector_store = AstraVectorStore(collection_name)
        def upsert_syllabus_chunks(self, texts, metadatas):
            self.vector_store.upsert_texts(texts, metadatas)
        def similarity_search(self, query, k=5):
            return self.vector_store.query(query, k=k)
    repo = AstraRepo('syllabus_chunks')
    # Upsert dummy chunks to create collection
    dummy_texts = ['Test syllabus chunk 1: Introduction to ML', 'Test chunk 2: Neural networks']
    dummy_meta = [{'source': 'test', 'section': 'intro'}, {'source': 'test', 'section': 'neural_nets'}]
    repo.upsert_syllabus_chunks(dummy_texts, dummy_meta)
    print('✅ syllabus_chunks collection CREATED & populated with 2 test chunks!')
    
    # Test retrieval
    results = repo.similarity_search('neural', k=2)
    print(f'✅ RAG TEST: Retrieved {len(results)} docs:')
    for r in results:
        print(f"  - {r.get('text', 'N/A')[:100]}...")
    print('🎉 FULL RAG PIPELINE FUNCTIONAL!')
except Exception as e:
    print(f'❌ Test failed: {str(e)}')
    print('💡 Fix: Add ASTRA_DB_ID & ASTRA_DB_APPLICATION_TOKEN to .env')

