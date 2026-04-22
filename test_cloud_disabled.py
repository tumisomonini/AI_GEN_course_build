import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()
uri = os.getenv('NEO4J_URI', 'neo4j+s://04246622.databases.neo4j.io:7687')
user = os.getenv('NEO4J_USERNAME', 'neo4j')
password = os.getenv('NEO4J_PASSWORD')
database = os.getenv('NEO4J_DATABASE', 'neo4j')
print(f"Testing URI: {uri}, User: {user}, Database: {database}")
driver = GraphDatabase.driver(uri, auth=(user, password))
try:
    conn = driver.verify_connectivity()
    print("✅ Aura Connectivity OK:", conn)
    with driver.session(database=database) as session:
        result = session.run("RETURN 1")
        print("✅ Query OK:", result.single())
except Exception as e:
    print("❌ Fail:", str(e))
finally:
    driver.close()
