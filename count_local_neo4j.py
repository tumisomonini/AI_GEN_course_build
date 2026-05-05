import os
from neo4j import GraphDatabase
uri = 'bolt://localhost:7687'
user = 'neo4j'
password = 'password'
database = 'neo4j'
driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session(database=database) as session:
    r = session.run('MATCH (t:Topic) RETURN count(t) as c')
    record = r.single()
    print('Local Topics:', record['c'] if record else 0)
    r = session.run('MATCH ()-[:PREREQUISITE]->() RETURN count(*) as c')
    record = r.single()
    print('Local PREREQ:', record['c'] if record else 0)
    r = session.run('MATCH ()-[:RELATED_TO]->() RETURN count(*) as c')
    record = r.single()
    print('Local RELATED_TO:', record['c'] if record else 0)
driver.close()
