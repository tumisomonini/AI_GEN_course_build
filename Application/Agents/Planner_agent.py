from typing import List, Optional
from node2vec import Node2Vec
import networkx as nx
from Application.Ports.neo4j_repo import Neo4jRepository

class PlannerAgent:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, neo4j_database: str = None, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._node2vec_model = None
        if not mock_mode:
            self.graph_repo = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

    def generate_syllabus(self, topics: List[str]) -> List[str]:
        if self.mock_mode:
            return topics
        model = self._get_node2vec_model()
        return sorted(topics, key=lambda x: float(model.wv[x].dot(model.wv[x])) if x in model.wv else 0.0, reverse=True)

    def _get_node2vec_model(self):
        if self._node2vec_model is None:
            G = self._load_neo4j_graph()
            node2vec = Node2Vec(G, dimensions=64, walk_length=30, num_walks=200)
            self._node2vec_model = node2vec.fit(window=10, min_count=1)
        return self._node2vec_model

    def invalidate_cache(self):
        self._node2vec_model = None

    def _load_neo4j_graph(self) -> nx.Graph:
        G = nx.Graph()
        with self.graph_repo.driver.session() as session:
            result = session.run("MATCH (n:Topic) RETURN n.name AS id")
            for record in result:
                G.add_node(record['id'])
            result = session.run("MATCH (a:Topic)-[:PREREQUISITE]->(b:Topic) RETURN a.name AS source, b.name AS target")
            for record in result:
                G.add_edge(record['source'], record['target'])
        return G
