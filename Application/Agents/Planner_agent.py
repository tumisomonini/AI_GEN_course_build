from typing import List, Optional
import networkx as nx



from ..Ports.neo4j_repo import Neo4jRepository
from Domain.knowledge_graphy import KnowledgeGraph

class PlannerAgent:
    def __init__(self, repository: Neo4jRepository):
        self._cached_graph: Optional[nx.Graph] = None
        if repository is None:
            self.graph_repo = None
        else:
            self.graph_repo = repository
        self.database = self.graph_repo.database if self.graph_repo else "neo4j"
        self.kg = KnowledgeGraph(self.graph_repo, self.database) if self.graph_repo else None

    def generate_syllabus(self, topics: List[str]) -> List[str]:
        try:
            if not self.kg:
                raise ValueError("KnowledgeGraph not initialized")
            if not topics:
                return []

            # Use KnowledgeGraph for optimal order
            ordered = self.kg.get_topic_order(topics)
            print(f"✅ KnowledgeGraph ordered {len(topics)} topics")
            return ordered

        except Exception as e:
            print(f"KG Planner failed: {e}. KnowledgeGraph now uses NetworkX internally.")
            return self._legacy_generate_syllabus(topics)

    def invalidate_cache(self):
        """Clears the cached graph, forcing a reload on the next call."""
        self._cached_graph = None

    def _legacy_generate_syllabus(self, topics: List[str]) -> List[str]:
        """Fallback ordering (NetworkX available via KnowledgeGraph primary path)."""
        return sorted(list(set(topics)))
