from typing import List, Dict, Optional
import logging
import numpy as np
from sklearn.cluster import KMeans
import networkx as nx
from Application.Infrastructure.graphDb.models import Topic
from Application.Infrastructure.graphDb.neo4j_repo import Neo4jNeomodelRepository

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    """
    Refactored KnowledgeGraph using neomodel OGM. Connection managed by Neo4jNeomodelRepository.
    """
    
    def __init__(self, repo: Neo4jNeomodelRepository, database: str = "neo4j"):
        self.repo = repo
        self._database = database
        logger.info("KnowledgeGraph initialized with neomodel repo")

    def add_topic(self, topic_name: str, description: str = "") -> bool:
        try:
            topic, created = Topic.get_or_create({'name': topic_name}, description=description)
            if created:
                topic.description = description
                topic.save()
            return True
        except Exception as e:
            logger.error(f"Failed to add topic {topic_name}: {str(e)}")
            return False

    def add_prerequisite(self, topic_name: str, prerequisite_name: str) -> bool:
        try:
            topic = Topic.nodes.get(name=topic_name)
            prereq, _ = Topic.get_or_create({'name': prerequisite_name})
            topic.prerequisites.connect(prereq)
            return True
        except Topic.DoesNotExist:
            logger.warning(f"Topic {topic_name} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to add prerequisite {prerequisite_name} for {topic_name}: {str(e)}")
            return False

    def get_prerequisites(self, topic_name: str) -> List[str]:
        try:
            topic = Topic.nodes.get(name=topic_name)
            return [p.name for p in topic.prerequisites.all()]
        except Topic.DoesNotExist:
            logger.warning(f"Topic {topic_name} not found")
            return []

    def get_dependent_topics(self, topic_name: str) -> List[str]:
        try:
            topic = Topic.nodes.get(name=topic_name)
            return [d.name for d in topic.dependents.all()]
        except Topic.DoesNotExist:
            return []

    def get_all_topics(self) -> List[Dict[str, str]]:
        topics = Topic.nodes.all()
        return [{"name": t.name, "description": t.description} for t in topics]

    def cluster_topics(self, topic_embeddings: Dict[str, List[float]], n_clusters: int = 3) -> Dict[int, List[str]]:
        if not topic_embeddings:
            return {}

        topic_names = list(topic_embeddings.keys())
        vectors = np.array(list(topic_embeddings.values()))
        n_clusters = min(n_clusters, len(topic_names))
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(vectors)
        
        clusters = {}
        for i, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(topic_names[i])
        
        logger.info(f"Clustered {len(topic_names)} topics into {n_clusters} groups")
        return clusters

    def get_topic_order(self, topic_names: List[str]) -> List[str]:
        if not topic_names:
            return []
        G = nx.DiGraph()
        all_nodes = set(topic_names)
        for topic in list(all_nodes):
            prereqs = self.repo.get_prerequisites(topic)
            for prereq in prereqs:
                G.add_edge(prereq, topic)
                all_nodes.add(prereq)
        try:
            topo_order = list(nx.topological_sort(G))
            ordered = [t for t in topo_order if t in topic_names]
            logger.info(f"Applied topological sort to {len(ordered)} topics")
            return ordered
        except nx.NetworkXUnfeasible:
            logger.warning("Graph has cycles, falling back to alphabetical order")
            return sorted(topic_names)

    def validate_prerequisites(self, topic_order: List[str]) -> bool:
        for i, topic_name in enumerate(topic_order):
            try:
                topic = Topic.nodes.get(name=topic_name)
                prereqs = [p.name for p in topic.prerequisites.all()]
                for prereq in prereqs:
                    if prereq not in topic_order[:i]:
                        logger.warning(f"Prerequisite {prereq} for {topic_name} not before it")
                        return False
            except Topic.DoesNotExist:
                continue
        return True

    def get_central_topics(self, topic_names: Optional[List[str]] = None, limit: int = 5) -> List[str]:
        """Get most central topics using NetworkX PageRank."""
        if topic_names is None:
            all_topics = self.get_all_topics()
            topic_names = [t['name'] for t in all_topics]
        if not topic_names:
            return []
        # Build same graph as topo
        G = nx.DiGraph()
        all_nodes = set(topic_names)
        for topic in list(all_nodes):
            prereqs = self.repo.get_prerequisites(topic)
            for prereq in prereqs:
                G.add_edge(prereq, topic)
                all_nodes.add(prereq)
        if len(G) == 0:
            return sorted(topic_names)[:limit]
        try:
            pagerank_scores = nx.pagerank(G.to_undirected(), alpha=0.85)
            sorted_topics = sorted(
                [(name, pagerank_scores.get(name, 0)) for name in topic_names],
                key=lambda x: x[1],
                reverse=True
            )
            central = [name for name, _ in sorted_topics[:limit]]
            logger.info(f"Central topics by PageRank: {central}")
            return central
        except Exception as e:
            logger.warning(f"PageRank failed: {e}, fallback to sorted")
            return sorted(topic_names)[:limit]

    def get_topic_graph(self, topic_name: str, depth: int = 1) -> Dict[str, set]:
        graph = {}
        try:
            topic = Topic.nodes.get(name=topic_name)
            
            # Prerequisites (outgoing)
            prereqs = [p.name for p in topic.prerequisites.all()] if hasattr(topic, 'prerequisites') and topic.prerequisites else []
            graph[topic_name] = set(prereqs)
            
            # Dependents (incoming)
            dependents = [d.name for d in topic.dependents.all()]
            for dep in dependents:
                if dep not in graph:
                    graph[dep] = set()
                graph[dep].add(topic_name)
            
            return graph
        except Topic.DoesNotExist:
            return {}

    def get_related_topics(self, topic_name: str, limit: int = 5) -> List[str]:
        try:
            topic = Topic.nodes.get(name=topic_name)
            related = [r.name for r in topic.related_to.all()]
            return related[:limit]
        except Topic.DoesNotExist:
            return []

    def add_related_topic(self, topic_name: str, related_topic_name: str) -> bool:
        try:
            t1 = Topic.nodes.get(name=topic_name)
            t2 = Topic.nodes.get(name=related_topic_name)
            t1.related_to.connect(t2)
            return True
        except Topic.DoesNotExist:
            return False

    def get_topic_details(self, topic_name: str) -> Optional[Dict[str, str]]:
        try:
            topic = Topic.nodes.get(name=topic_name)
            return {"name": topic.name, "description": topic.description}
        except Topic.DoesNotExist:
            return None
