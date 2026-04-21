from typing import List, Optional
import networkx as nx

from ..Ports.neo4j_repo import Neo4jRepository
from Domain.knowledge_graphy import KnowledgeGraph

class PlannerAgent:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, neo4j_database: str = None):
        self._cached_graph: Optional[nx.Graph] = None
        self.graph_repo = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
        self.database = self.graph_repo.database
        self.kg = KnowledgeGraph(self.graph_repo.driver, self.database)

    def generate_syllabus(self, topics: List[str]) -> List[str]:
        try:
            if not topics:
                return []

            # Use KnowledgeGraph for optimal order
            ordered = self.kg.get_topic_order(topics)
            print(f"✅ KnowledgeGraph ordered {len(topics)} topics")
            return ordered

        except Exception as e:
            print(f"KG Planner failed: {e}. Using legacy Neo4j/NetworkX.")
            return self._legacy_generate_syllabus(topics)

    def invalidate_cache(self):
        """Clears the cached graph, forcing a reload on the next call."""
        self._cached_graph = None

    def _legacy_generate_syllabus(self, topics: List[str]) -> List[str]:
        """Legacy NetworkX fallback."""
        G = self._load_neo4j_graph() or nx.DiGraph()
        nodes_in_topics = [n for n in G.nodes if n in topics]
        if not nodes_in_topics:
            return sorted(topics)
        if nx.is_directed_acyclic_graph(G):
            return list(nx.topological_sort(G.subgraph(nodes_in_topics)))
        centrality = nx.degree_centrality(G)
        return sorted(topics, key=lambda x: centrality.get(x, 0), reverse=True)

    def _load_neo4j_graph(self) -> Optional["nx.Graph"]:
        if self._cached_graph:
            return self._cached_graph
        G = nx.DiGraph()
        with self.graph_repo.driver.session(database=self.database) as session:
            result = session.run("MATCH (n:Topic) RETURN n.name AS id")
            for record in result:
                G.add_node(record['id'])
            result = session.run("MATCH (a:Topic)-[:PREREQUISITE]->(b:Topic) RETURN a.name AS source, b.name AS target")
            for record in result:
                G.add_edge(record['source'], record['target'])
        self._cached_graph = G
        return G
