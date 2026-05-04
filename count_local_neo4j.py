import os
from neo4j import GraphDatabase
uri = 'bolt://localhost:7687'
user = 'neo4j'
password = 'password'
database = 'neo4j'
driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session(database=database) as session:
    r = session.run('MATCH (t:Topic) RETURN count(t) as c')
    print('Local Topics:', r.single()['c'])
    r = session.run('MATCH ()-[:PREREQUISITE]->() RETURN count(*) as c')
    print('Local PREREQ:', r.single()['c'])
    r = session.run('MATCH ()-[:RELATED_TO]->() RETURN count(*) as c')
    print('Local RELATED_TO:', r.single()['c'])
driver.close()

