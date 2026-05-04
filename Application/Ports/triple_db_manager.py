from typing import List, Dict, Any, Optional
from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl
from Application.Ports.Astra_repo import AstraRepo
from Domain.knowledge_graphy import KnowledgeGraph
import os
import logging

logger = logging.getLogger(__name__)

class TripleDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.pg = PostgresRepo()

            # Neo4j: try env credentials first, fallback to local hardcoded on auth failure
            neo_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            neo_user = os.getenv('NEO4J_USERNAME', 'neo4j')
            neo_pass = os.getenv('NEO4J_PASSWORD', 'password')
            neo_db = os.getenv('NEO4J_DATABASE', 'neo4j')

            try:
                cls._instance.neo = Neo4jRepoImpl(neo_uri, neo_user, neo_pass, neo_db)
            except Exception as e:
                if 'localhost' in neo_uri or '127.0.0.1' in neo_uri:
                    print(f"⚠️ Neo4j auth failed with env credentials ({e}), retrying with local defaults...")
                    cls._instance.neo = Neo4jRepoImpl('bolt://localhost:7687', 'neo4j', 'password', 'neo4j')
                else:
                    raise

            # Astra: optional — don't crash the whole app if Astra is unavailable
            try:
                cls._instance.astra = AstraRepo()
                logger.info("✅ AstraDB connected in TripleDBManager")
            except Exception as e:
                print(f"⚠️ AstraDB initialization failed: {e}. Vector RAG will be disabled.")
                cls._instance.astra = None

            if cls._instance.neo:
                cls._instance.kg = KnowledgeGraph(cls._instance.neo, os.getenv('NEO4J_DATABASE', 'neo4j'))
            else:
                cls._instance.kg = None
            # Only require Postgres + Neo4j; Astra is optional (warns if missing)
            if not cls._instance.pg or not cls._instance.neo:
                raise ValueError("Postgres and Neo4j must be healthy for TripleDBManager (Astra is optional)")
        return cls._instance

    def create_linked_course(self, title: str, audience: str = 'general') -> int:
        # PG: Create course
        course_id = self.pg.create_course(title, audience)

        # Neo4j: Link topics to course
        if self.kg:
            self.kg.add_topic('Introduction', f'Intro to {title}')
            self.kg.add_topic('Advanced', f'Advanced {title}')
            self.kg.add_prerequisite('Advanced', 'Introduction')

            # Delegate linking to the repository port
            self.neo.link_topics_to_course(course_id, title, ['Introduction', 'Advanced'])

        # Astra: Upsert sample chunks with metadata (optional — skip if Astra unavailable)
        if self.astra:
            sample_texts = [
                f'Sample content for {title}: Introduction.',
                f'Sample content for {title}: Advanced topics.'
            ]
            sample_metas = [
                {'course_id': course_id, 'course_title': title, 'section': 'intro', 'hierarchy_level': 'concept'},
                {'course_id': course_id, 'course_title': title, 'section': 'advanced', 'hierarchy_level': 'concept'}
            ]
            try:
                self.astra.upsert_syllabus_chunks(sample_texts, sample_metas, topic_id=f"course_{course_id}_intro")
            except Exception as e:
                print(f"⚠️ Astra upsert failed for course {course_id}: {e}")
        else:
            print(f"⚠️ Astra unavailable — skipping vector upsert for course {course_id}")

        print(f'✅ Linked course {course_id} across available DBs')
        return course_id

    def hybrid_search(self, query: str, k: int = 5, strategy: str = "hybrid") -> Dict[str, Any]:
        """Orchestrated search across TripleDB based on routing strategy."""
        results = {
            'vector': [],
            'kg_context': [],
            'pg_courses': []
        }

        # 0. PG Metadata (Always fetched for global context/naming)
        pg_courses = self.pg.search_courses(query)
        results['pg_courses'] = [{'course_id': c['course_id'], 'title': c['title']} for c in pg_courses]

        # 1. Vector Search (Semantic)
        if strategy in ["vector", "hybrid"] and self.astra:
            try:
                vector_data = self.astra.similarity_search(query, k=k)
                results['vector'] = vector_data
            except Exception as e:
                print(f"⚠️ Vector search failed: {e}")
                results['vector'] = []

        # 2. KG Context (Structural)
        if strategy in ["kg", "hybrid"] and self.kg:
            # Instead of manually filtering all topics, use the KnowledgeGraph domain methods
            details = self.kg.get_topic_details(query)
            if details:
                results['kg_context'].append(f"Concept: {details.get('description')}")

            prereqs = self.kg.get_prerequisites(query)
            if prereqs:
                results['kg_context'].append(f"Prerequisites: {', '.join(prereqs)}")

        return results

    def get_health(self) -> Dict[str, str]:
        return {
            'postgres': 'healthy' if self.pg else 'down',
            'neo4j': 'healthy' if self.neo else 'down',
            'astra': 'healthy' if self.astra else 'down',
            'integrated': 'ready'
        }

    def sync_metadata(self):
        # Example bi-directional: Fetch PG courses, ensure Neo4j Course nodes exist
        courses = self.pg.search_courses('')
        for c in courses:
            with self.neo.driver.session() as session:
                session.run(
                    'MERGE (c:Course {course_id: $id, title: $title})',
                    id=c['course_id'], title=c['title']
                )
        print('✅ Metadata synced PG → Neo4j')

    def sync_neo4j_to_cloud(self, dry_run: bool = False) -> dict:
        """
        Sync local Docker Neo4j Topic graph to cloud Aura instance.
        Uses environment variables with TARGET_ prefix for cloud credentials.
        """
        from Application.Scripts.sync_neo4j import run_sync, _build_config

        source_cfg = _build_config("local")
        target_cfg = _build_config("cloud", env_prefix="TARGET_")

        stats = run_sync(source_cfg, target_cfg, dry_run=dry_run)
        print(f"✅ Neo4j synced local → cloud: {stats}")
        return stats
