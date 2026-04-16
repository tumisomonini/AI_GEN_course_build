// Sample AI Course Knowledge Graph for testing
// Run this in Neo4j Browser connected to your AuraDB

MERGE (t1:Topic {name: "Introduction to AI"})
MERGE (t2:Topic {name: "Search Algorithms"})
MERGE (t3:Topic {name: "Knowledge Representation"})
MERGE (t4:Topic {name: "Machine Learning Basics"})
MERGE (t5:Topic {name: "Neural Networks"})
MERGE (t6:Topic {name: "Reinforcement Learning"})

MERGE (t2)-[:PREREQUISITE]->(t1)
MERGE (t3)-[:PREREQUISITE]->(t1)
MERGE (t4)-[:PREREQUISITE]->(t2)
MERGE (t5)-[:PREREQUISITE]->(t4)
MERGE (t6)-[:PREREQUISITE]->(t5)
MERGE (t6)-[:PREREQUISITE]->(t3)

RETURN "✅ Sample KG populated!" AS message;
