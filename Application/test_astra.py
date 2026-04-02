import os
from dotenv import load_dotenv
import cassio

load_dotenv()

# Initialize Cassio with AstraDB
cassio.init(
    token=os.getenv('ASTRA_DB_APPLICATION_TOKEN'),
    database_id=os.getenv('ASTRA_DB_ID'),
)

print('Cassio initialized with AstraDB credentials.')
print('AstraDB connection successful! Ready to use vector collections (syllabus_chunks).')

