from typing import List, Optional
import networkx as nx

from ..Ports.neo4j_repo import Neo4jRepository

class PlannerAgent:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, neo4j_database: str = None):
        self._cached_graph: Optional[nx.Graph] = None
        self.graph_repo = Neo4jRepository(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

    def generate_syllabus(self, topics: List[str]) -> List[str]:
        try:
            if not topics:
                return []

            G = self._load_neo4j_graph()
            
            # Only process nodes that actually exist in the topics list
            nodes_in_topics = [n for n in G.nodes if n in topics]
            
            if not nodes_in_topics:
                return sorted(topics) # Fallback to alphabetical if no graph data

            # Use Topological Sort for valid DAGs, fallback to Degree Centrality for complex graphs
            if nx.is_directed_acyclic_graph(G):
                subgraph = G.subgraph(nodes_in_topics)
                return list(nx.topological_sort(subgraph))
            else:
                # If there are cycles, sort by degree (most connected topics first)
                centrality = nx.degree_centrality(G)
                return sorted(topics, key=lambda x: centrality.get(x, 0), reverse=True)

        except Exception as e:
            print(f"Planner logic failed: {e}. Using simple alphabetical order.")
            return sorted(topics)

    def invalidate_cache(self):
        """Clears the cached graph, forcing a reload on the next call."""
        self._cached_graph = None

    def _load_neo4j_graph(self) -> Optional["nx.Graph"]:
        if self._cached_graph:
            return self._cached_graph

        G = nx.DiGraph()

        with self.graph_repo.driver.session() as session:
            result = session.run("MATCH (n:Topic) RETURN n.name AS id")
            for record in result:
                G.add_node(record['id'])
            result = session.run("MATCH (a:Topic)-[:PREREQUISITE]->(b:Topic) RETURN a.name AS source, b.name AS target")
            for record in result:
                G.add_edge(record['source'], record['target'])
        self._cached_graph = G
        return G
