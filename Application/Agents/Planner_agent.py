from typing import List
from node2vec import Node2Vec
import networkx as nx
from domain.knowledge_graph import Neo4jKnowledgeGraph

class PlannerAgent:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.graph_repo = Neo4jKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password)

    def generate_syllabus(self, topics: List[str]) -> List[str]:
        G = self._load_neo4j_graph()
        node2vec = Node2Vec(G, dimensions=64, walk_length=30, num_walks=200)
        model = node2vec.fit(window=10, min_count=1)
        return sorted(topics, key=lambda x: model.wv[x], reverse=True)

    def _load_neo4j_graph(self) -> nx.Graph:
        G = nx.Graph()
        with self.graph_repo.driver.session() as session:
            result = session.run("MATCH (n:Topic) RETURN n.name AS id")
            for record in result:
                G.add_node(record["id"])
            result = session.run("MATCH (a:Topic)-[:PREREQUISITE]->(b:Topic) RETURN a.name AS source, b.name AS target")
            for record in result:
                G.add_edge(record["source"], record["target"])
        return G