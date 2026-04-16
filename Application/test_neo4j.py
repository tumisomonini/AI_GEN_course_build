import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USERNAME')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE')

driver = GraphDatabase.driver(uri, auth=(user, password))
try:
    with driver.session(database=database) as session:
        result = session.run('RETURN 1 AS num')
        print('Neo4j connection successful:', result.single()['num'])
except Exception as e:
    print('Neo4j connection failed:', str(e))
finally:
    driver.close()
