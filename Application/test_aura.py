import os
from neo4j import GraphDatabase

# For test, hardcode since no venv
# In project: from dotenv import load_dotenv; load_dotenv()
uri = 'neo4j+s://04246622.databases.neo4j.io'
user = '04246622'
password = 'sAMf5Su1ZR9Bhu_rLsbM4pc4gESCDPbVgrjJHpZC6NU'
db = '04246622'

driver = GraphDatabase.driver(uri, auth=(user, password))
try:
    with driver.session(database=db) as session:
        result = session.run('RETURN 1 AS num')
        print('Aura connection successful:', result.single()['num'])
except Exception as e:
    print('Aura connection failed:', str(e))
finally:
    driver.close()
