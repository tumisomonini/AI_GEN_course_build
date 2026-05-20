from typing import List, Dict, Any, Optional
from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl
from Application.Ports.Astra_repo import AstraRepo
from Domain.knowledge_graphy import KnowledgeGraph
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


class TripleDBManager:
    """Triple store manager integrating PG, Neo4j, AstraDB (optional)."""

    # Declare instance attributes at class level so Pylance resolves __new__ assignments
    pg: Optional[PostgresRepo]
    neo: Optional[Neo4jRepoImpl]
    astra: Optional[AstraRepo]
    kg: Optional[KnowledgeGraph]

    _instance: Optional['TripleDBManager'] = None

    def __new__(cls) -> 'TripleDBManager':
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.pg = None
            instance.neo = None
            instance.astra = None
            instance.kg = None

            # Reuse the shared singleton from dependencies to avoid separate pool
            from Application.API.dependencies import init_postgres_singleton
            instance.pg = init_postgres_singleton()

            # Neo4j: prefer the centralized singleton init (Aura-first + fallback)
            try:
                from Application.API.dependencies import init_neo4j_singleton

                instance.neo = init_neo4j_singleton()
            except Exception as e:
                # As a last resort, attempt direct construction with env creds.
                neo_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
                neo_user = os.getenv('NEO4J_USERNAME', 'neo4j')
                neo_pass = os.getenv('NEO4J_PASSWORD', 'password')
                neo_db = os.getenv('NEO4J_DATABASE', 'neo4j')

                try:
                    instance.neo = Neo4jRepoImpl(neo_uri, neo_user, neo_pass, neo_db)
                except Exception as e2:
                    # If local, retry hardcoded defaults.
                    if 'localhost' in neo_uri or '127.0.0.1' in neo_uri:
                        print(f"⚠️ Neo4j auth failed ({e2}), retrying with local defaults...")
                        instance.neo = Neo4jRepoImpl('bolt://localhost:7687', 'neo4j', 'password', 'neo4j')
                    else:
                        raise



            # Astra: OPTIONAL for test environments.
            # Full vector RAG requires Astra, but most unit tests only need Postgres+Neo4j.
            try:
                instance.astra = AstraRepo()
                logger.info("✅ AstraDB connected in TripleDBManager")
            except Exception as e:
                instance.astra = None
                logger.warning(f"⚠️ AstraDB init failed (optional): {e}")

            if instance.neo:
                instance.kg = KnowledgeGraph(instance.neo, os.getenv('NEO4J_DATABASE', 'neo4j'))
            else:
                instance.kg = None

            # Degrade gracefully in environments where one/both backends are unavailable.
            # Unit/integration tests should still be able to import the application.
            if not instance.pg or not instance.neo:
                logger.warning(
                    "TripleDBManager running in degraded mode: pg=%s neo4j=%s",
                    bool(instance.pg),
                    bool(instance.neo),
                )
                # Ensure kg is None when neo4j is missing.
                instance.kg = None

            cls._instance = instance

        # Ensure health endpoint never crashes due to missing optional deps.
        # (Astra may be None in test env.)
        return cls._instance


    def create_linked_course(self, title: str, audience: str = 'general') -> int:
        if not self.pg:
            raise RuntimeError("Postgres not available")
        course_id = self.pg.create_course(title, audience)

        if self.kg and self.neo:
            # Hardcoded topics removed to allow for dynamic syllabus generation
            pass
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
                print(f"❌ Astra upsert failed for course {course_id}: {e}")
                raise

        print(f'✅ Linked course {course_id} across available DBs')
        return course_id

    async def hybrid_search(self, query: str, k: int = 5, strategy: str = "hybrid") -> Dict[str, Any]:
        """Orchestrated parallel search across TripleDB based on routing strategy."""
        loop = asyncio.get_event_loop()
        results: Dict[str, Any] = {'vector': [], 'kg_context': [], 'pg_courses': []}

        async def _pg():
            if not self.pg:
                return []
            courses = await loop.run_in_executor(None, lambda: self.pg.search_courses(query))  # type: ignore[union-attr]
            return [{'course_id': c['course_id'], 'title': c['title']} for c in courses]

        async def _vector():
            if strategy in ["vector", "hybrid"] and self.astra:
                try:
                    return await loop.run_in_executor(None, lambda: self.astra.similarity_search(query, k=k))  # type: ignore[union-attr]
                except Exception as e:
                    print(f"⚠️ Vector search failed: {e}")
            return []

        async def _kg():
            kg_context = []
            if strategy in ["kg", "hybrid"] and self.kg:
                details, prereqs = await asyncio.gather(
                    loop.run_in_executor(None, lambda: self.kg.get_topic_details(query)),  # type: ignore[union-attr]
                    loop.run_in_executor(None, lambda: self.kg.get_prerequisites(query))   # type: ignore[union-attr]
                )
                if details:
                    kg_context.append(f"Concept: {details.get('description')}")
                if prereqs:
                    kg_context.append(f"Prerequisites: {', '.join(prereqs)}")
            return kg_context

        pg_res, vec_res, kg_res = await asyncio.gather(_pg(), _vector(), _kg())
        results['pg_courses'] = pg_res
        results['vector'] = vec_res
        results['kg_context'] = kg_res
        return results

    def get_health(self) -> Dict[str, str]:
        return {
            'postgres': 'healthy' if self.pg else 'down',
            'neo4j': 'healthy' if self.neo else 'down',
            'astra': 'healthy' if self.astra else 'down',
            'integrated': 'ready'
        }

    def sync_metadata(self):
        if not self.pg or not self.neo:
            print("⚠️ sync_metadata skipped: Postgres or Neo4j unavailable")
            return
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
