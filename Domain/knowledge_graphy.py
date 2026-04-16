from neo4j import GraphDatabase
from typing import List, Dict, Optional, Set
import logging
import networkx as nx
import numpy as np
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    """
    A class to interact with the Neo4j knowledge graph for course topics and prerequisites.
    """

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize the KnowledgeGraph with Neo4j connection details.

        Args:
            uri (str): The URI of the Neo4j database
            user (str): The username for the Neo4j database
            password (str): The password for the Neo4j database
        """
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("KnowledgeGraph initialized with connection to Neo4j")

    def close(self):
        """Close the Neo4j driver connection."""
        self._driver.close()
        logger.info("KnowledgeGraph connection closed")

    def add_topic(self, topic_name: str, description: str = "") -> bool:
        """
        Add a new topic to the knowledge graph.

        Args:
            topic_name (str): The name of the topic
            description (str): A description of the topic

        Returns:
            bool: True if the topic was added successfully, False otherwise
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MERGE (t:Topic {name: $topic_name})
                    ON CREATE SET t.description = $description, t.created_at = datetime()
                    ON MATCH SET t.description = $description, t.updated_at = datetime()
                    RETURN t
                    """,
                    topic_name=topic_name,
                    description=description
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to add topic {topic_name}: {str(e)}")
            return False

    def add_prerequisite(self, topic_name: str, prerequisite_name: str) -> bool:
        """
        Add a prerequisite relationship between two topics.

        Args:
            topic_name (str): The name of the topic
            prerequisite_name (str): The name of the prerequisite topic

        Returns:
            bool: True if the relationship was added successfully, False otherwise
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Topic {name: $topic_name})
                    MATCH (b:Topic {name: $prerequisite_name})
                    MERGE (a)-[r:PREREQUISITE]->(b)
                    RETURN r
                    """,
                    topic_name=topic_name,
                    prerequisite_name=prerequisite_name
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to add prerequisite {prerequisite_name} for {topic_name}: {str(e)}")
            return False

    def get_prerequisites(self, topic_name: str) -> List[str]:
        """
        Get all prerequisites for a given topic.

        Args:
            topic_name (str): The name of the topic

        Returns:
            List[str]: A list of prerequisite topic names
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Topic {name: $topic_name})-[:PREREQUISITE]->(b:Topic)
                    RETURN b.name AS prerequisite
                    """,
                    topic_name=topic_name
                )
                return [record["prerequisite"] for record in result]
        except Exception as e:
            logger.error(f"Failed to get prerequisites for {topic_name}: {str(e)}")
            return []

    def get_dependent_topics(self, topic_name: str) -> List[str]:
        """
        Get all topics that depend on the given topic as a prerequisite.

        Args:
            topic_name (str): The name of the topic

        Returns:
            List[str]: A list of topic names that depend on the given topic
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Topic)-[:PREREQUISITE]->(b:Topic {name: $topic_name})
                    RETURN a.name AS dependent_topic
                    """,
                    topic_name=topic_name
                )
                return [record["dependent_topic"] for record in result]
        except Exception as e:
            logger.error(f"Failed to get dependent topics for {topic_name}: {str(e)}")
            return []

    def get_all_topics(self) -> List[Dict[str, str]]:
        """
        Get all topics in the knowledge graph.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing topic information
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (t:Topic)
                    RETURN t.name AS name, t.description AS description
                    """
                )
                return [{"name": record["name"], "description": record["description"]} for record in result]
        except Exception as e:
            logger.error(f"Failed to get all topics: {str(e)}")
            return []

    def cluster_topics(self, topic_embeddings: Dict[str, List[float]], n_clusters: int = 3) -> Dict[int, List[str]]:
        """
        Group topics into thematic clusters using KMeans.
        Helps organize a long course into logically grouped modules.
        """
        if not topic_embeddings:
            return {}

        topic_names = list(topic_embeddings.keys())
        vectors = np.array(list(topic_embeddings.values()))
        
        # n_clusters shouldn't exceed number of topics
        n_clusters = min(n_clusters, len(topic_names))
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(vectors)
        
        clusters = {}
        for i, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(topic_names[i])
        
        logger.info(f"Clustered {len(topic_names)} topics into {n_clusters} groups")
        return clusters

    def get_topic_order(self, topic_names: List[str]) -> List[str]:
        """
        Get an optimal order for studying the given topics based on prerequisites.

        Args:
            topic_names (List[str]): A list of topic names

        Returns:
            List[str]: An ordered list of topic names
        """
        if not topic_names:
            return []
            
        try:
            G = nx.DiGraph()
            # Add all requested topics as nodes
            for name in topic_names:
                G.add_node(name)

            with self._driver.session() as session:
                # Fetch all relevant prerequisite relationships within the set of requested topics
                result = session.run(
                    """
                    MATCH (a:Topic)-[:PREREQUISITE]->(b:Topic)
                    WHERE a.name IN $topic_names AND b.name IN $topic_names
                    RETURN a.name AS source, b.name AS target
                    """,
                    topic_names=topic_names
                )
                for record in result:
                    # Note: PREREQUISITE relationship is (topic)->(required_topic)
                    # For topological sort, we want (required_topic)->(topic)
                    G.add_edge(record["target"], record["source"])

            # Returns a valid topological sort, or handles cycles by falling back to original order
            if nx.is_directed_acyclic_graph(G):
                return list(nx.topological_sort(G))
            else:
                logger.warning("Cycles detected in KnowledgeGraph dependencies. Falling back to input order.")
                return topic_names
        except Exception as e:
            logger.error(f"Failed to get topic order: {str(e)}")
            return topic_names

    def validate_prerequisites(self, topic_order: List[str]) -> bool:
        """
        Validate that all prerequisites are satisfied in the given topic order.

        Args:
            topic_order (List[str]): An ordered list of topic names

        Returns:
            bool: True if all prerequisites are satisfied, False otherwise
        """
        try:
            with self._driver.session() as session:
                for i, topic in enumerate(topic_order):
                    result = session.run(
                        """
                        MATCH (a:Topic {name: $topic_name})-[:PREREQUISITE]->(b:Topic)
                        RETURN b.name AS prerequisite
                        """,
                        topic_name=topic
                    )
                    prerequisites = [record["prerequisite"] for record in result]
                    for prerequisite in prerequisites:
                        if prerequisite not in topic_order[:i]:
                            logger.warning(f"Prerequisite {prerequisite} for {topic} not satisfied")
                            return False
                return True
        except Exception as e:
            logger.error(f"Failed to validate prerequisites: {str(e)}")
            return False

    def get_topic_graph(self, topic_name: str, depth: int = 1) -> Dict[str, Set[str]]:
        """
        Get a subgraph of topics related to the given topic up to a certain depth.

        Args:
            topic_name (str): The name of the central topic
            depth (int): The depth of relationships to include

        Returns:
            Dict[str, Set[str]]: A dictionary representing the topic graph
        """
        graph = {}
        try:
            with self._driver.session() as session:
                # Get prerequisites
                for current_depth in range(1, depth + 1):
                    result = session.run(
                        """
                        MATCH path = (a:Topic {{name: $topic_name}})-[:PREREQUISITE*1..{current_depth}]->(b:Topic)
                        RETURN a.name AS source, b.name AS target
                        """ % current_depth,
                        topic_name=topic_name,
                        depth=current_depth
                    )
                    for record in result:
                        source = record["source"]
                        target = record["target"]
                        if source not in graph:
                            graph[source] = set()
                        if target not in graph:
                            graph[target] = set()
                        graph[source].add(target)

                # Get dependencies
                for current_depth in range(1, depth + 1):
                    result = session.run(
                        f"""
                        MATCH path = (a:Topic)-[:PREREQUISITE*1..{current_depth}]->(b:Topic {{name: $topic_name}})
                        RETURN a.name AS source, b.name AS target
                        """,
                        topic_name=topic_name
                    )
                    for record in result:
                        source = record["source"]
                        target = record["target"]
                        if source not in graph:
                            graph[source] = set()
                        if target not in graph:
                            graph[target] = set()
                        graph[source].add(target)

                return graph
        except Exception as e:
            logger.error(f"Failed to get topic graph for {topic_name}: {str(e)}")
            return {}

    def get_related_topics(self, topic_name: str, limit: int = 5) -> List[str]:
        """
        Get topics related to the given topic.

        Args:
            topic_name (str): The name of the topic
            limit (int): The maximum number of related topics to return

        Returns:
            List[str]: A list of related topic names
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Topic {name: $topic_name})-[:RELATED_TO*1..2]-(b:Topic)
                    WHERE a <> b
                    RETURN b.name AS related_topic
                    LIMIT $limit
                    """,
                    topic_name=topic_name,
                    limit=limit
                )
                return [record["related_topic"] for record in result]
        except Exception as e:
            logger.error(f"Failed to get related topics for {topic_name}: {str(e)}")
            return []

    def add_related_topic(self, topic_name: str, related_topic_name: str) -> bool:
        """
        Add a related topic relationship between two topics.

        Args:
            topic_name (str): The name of the topic
            related_topic_name (str): The name of the related topic

        Returns:
            bool: True if the relationship was added successfully, False otherwise
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Topic {name: $topic_name})
                    MATCH (b:Topic {name: $related_topic_name})
                    MERGE (a)-[r:RELATED_TO]->(b)
                    MERGE (b)-[s:RELATED_TO]->(a)
                    RETURN r, s
                    """,
                    topic_name=topic_name,
                    related_topic_name=related_topic_name
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to add related topic {related_topic_name} for {topic_name}: {str(e)}")
            return False

    def get_topic_details(self, topic_name: str) -> Optional[Dict[str, str]]:
        """
        Get detailed information about a topic.

        Args:
            topic_name (str): The name of the topic

        Returns:
            Optional[Dict[str, str]]: A dictionary with topic details, or None if not found
        """
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (t:Topic {name: $topic_name})
                    RETURN t.name AS name, t.description AS description
                    """,
                    topic_name=topic_name
                )
                record = result.single()
                if record:
                    return {"name": record["name"], "description": record["description"]}
                return None
        except Exception as e:
            logger.error(f"Failed to get details for {topic_name}: {str(e)}")
            return None
