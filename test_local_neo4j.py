from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
try:
  with driver.session(database='neo4j') as session:
    result = session.run('RETURN 1 AS num')
    print('Local Neo4j connection successful:', result.single()['num'])
except Exception as e:
  print('Local Neo4j connection failed:', str(e))
finally:
  driver.close()

