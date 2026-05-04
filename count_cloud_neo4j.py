import os
from neo4j import GraphDatabase
uri = 'neo4j+s://780e4b3a.databases.neo4j.io'
user = '780e4b3a'
password = 'G8hMcmRovD--SSgcVCcIORJIAYBKB0Xe-f6Jvo1P1-s'
database = '780e4b3a'
driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session(database=database) as session:
    r = session.run('MATCH (t:Topic) RETURN count(t) as c')
    print('Cloud Topics:', r.single()['c'])
    r = session.run('MATCH ()-[:PREREQUISITE]->() RETURN count(*) as c')
    print('Cloud PREREQ:', r.single()['c'])
    r = session.run('MATCH ()-[:RELATED_TO]->() RETURN count(*) as c')
    print('Cloud RELATED_TO:', r.single()['c'])
driver.close()
