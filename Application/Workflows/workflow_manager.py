from typing import Dict, List, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from .syllabus_workflow import create_syllabus_workflow, create_outline_workflow
from .syllabus_workflow import OutlineState, SyllabusState

from Application.API.agents import get_real_agents
from Application.API.dependencies import get_triple_db_manager

logger = logging.getLogger(__name__)

WorkflowType = Any
WorkflowFactory = Optional[callable]




class WorkflowManager:
    """Singleton manager for workflow registration and execution."""

    _instance: Optional["WorkflowManager"] = None

    def __new__(cls) -> "WorkflowManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.workflows: Dict[str, WorkflowType] = {}
        self.factories: Dict[str, WorkflowFactory] = {"outline": create_outline_workflow}

        self._healthy_cache: bool = False
        self._register_workflows()
        logger.info("WorkflowManager initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def _register_workflows(self) -> None:
        """Register compiled workflows with retry logic."""
        agents = self._get_agents_safe()
        if agents is None:
            logger.warning(
                "Skipping syllabus workflow registration due to unavailable/invalid agents"
            )
            return

        # Register compiled workflows
        self.workflows["syllabus"] = create_syllabus_workflow(
            agents["planner"],
            agents["author"],
            agents["reviewer"],
            agents["assembler"],
        )

        logger.info("Registered workflows: %s", self.list_workflows())

    def _get_agents_safe(self) -> Optional[Dict[str, Any]]:
        try:
            agents = get_real_agents()
            if not isinstance(agents, dict) or len(agents) != 4:
                logger.error("Invalid agents structure: %s", agents)
                return None
            return agents
        except Exception as e:
            logger.error("Failed to get agents: %s", str(e), exc_info=True)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    def _check_databases(self, skip_non_pg: bool = False) -> Dict[str, bool]:
        """Check database health with retry logic."""
        manager = get_triple_db_manager()
        results = {"postgres": False, "neo4j": False, "astra": False}

        pg = getattr(manager, "pg", None)
        if pg is not None and hasattr(pg, "health"):
            results["postgres"] = bool(pg.health())

        if getattr(manager, "neo4j", None) is not None:
            # manager.neo4j is currently a repository; no standard health() method.
            results["neo4j"] = True

        if getattr(manager, "astra", None) is not None:
            results["astra"] = True

        return results

    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys()) + list(self.factories.keys())

    def get_workflow(self, name: str) -> Optional[WorkflowType]:
        return self.workflows.get(name)

    def get_factory(self, name: str) -> Optional[WorkflowFactory]:
        return self.factories.get(name)

    @property
    def is_healthy(self) -> bool:
        return self._healthy_cache

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def init(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        config = config or {}
        skip_non_pg = config.get("skip_db_non_pg", False)

        try:
            db_status = self._check_databases(skip_non_pg=skip_non_pg)
            dbs_ok = all(db_status.values())

            agents = self._get_agents_safe()
            agents_ok = agents is not None

            # Register workflows (retry if fails)
            self._register_workflows()

            self._healthy_cache = dbs_ok and agents_ok

            return {
                "status": "success",
                "workflows": self.list_workflows(),
                "db_status": db_status,
                "dbs_healthy": dbs_ok,
                "agents_ready": agents_ok,
                "healthy": self.is_healthy,
                "message": "WorkflowManager ready",
            }
        except Exception as e:
            logger.error("WorkflowManager init failed: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "workflows": self.list_workflows(),
                "db_status": {},
                "dbs_healthy": False,
                "agents_ready": False,
                "healthy": False,
                "message": str(e),
            }

    async def execute_workflow(
        self, name: str, input_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        workflow = self.get_workflow(name)
        factory = self.get_factory(name)

        if workflow is None and factory is None:
            return {
                "status": "error",
                "message": f"Workflow '{name}' not found. Compiled: {list(self.workflows)}, Factories: {list(self.factories)}",
            }

        try:
            if factory:
                result = factory(**input_data, **kwargs)
            else:
                result = await workflow.ainvoke(input_data, **kwargs)  # type: ignore[union-attr]

            return {"status": "success", "result": result, "workflow": name}
        except Exception as e:
            logger.error("Workflow '%s' execution failed: %s", name, str(e), exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "workflow": name,
            }

    def close(self) -> None:
        self.workflows.clear()
        self.factories.clear()
        logger.info("WorkflowManager closed")


manager = WorkflowManager()

