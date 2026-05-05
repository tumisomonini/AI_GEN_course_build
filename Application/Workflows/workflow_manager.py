from typing import Dict, List, Any, Optional
import logging
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential
from langgraph.graph import StateGraph
from .syllabus_workflow import (
    create_syllabus_workflow,
    create_outline_workflow,
    OutlineState,
    SyllabusState
)
from Application.API.agents import get_real_agents
from Application.API.dependencies import get_triple_db_manager

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases for better type hints
WorkflowType = Any
WorkflowFactory = Optional[callable]

class WorkflowManager:
    """
    Singleton manager for workflow registration, initialization, and execution.
    Supports both compiled workflows and workflow factories.
    """

    _instance: Optional['WorkflowManager'] = None
    workflows: Dict[str, WorkflowType] = {}
    factories: Dict[str, WorkflowFactory] = {}
    _healthy_cache: bool = False
    _initialized: bool = False

    def __new__(cls) -> 'WorkflowManager':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Prevent re-initialization."""
        if self._initialized:
            return
        self._initialized = True
        self.workflows = {}
        self.factories = {'outline': create_outline_workflow}
        self._register_workflows()
        logger.info("WorkflowManager initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _register_workflows(self) -> None:
        """Register all available workflows with retry logic."""
        try:
            agents = self._get_agents_safe()\n            if agents is None:\n                logger.warning("Skipping syllabus workflow registration due to unavailable agents")\n                return\n            if not isinstance(agents, dict) or len(agents) != 4:\n                logger.warning("Invalid agents structure, skipping workflow registration")\n                return

            # Register compiled workflows
            self.workflows['syllabus'] = create_syllabus_workflow(
                agents['planner'],
                agents['author'],
                agents['reviewer'],
                agents['assembler']
            )

            logger.info(f"Registered workflows: {self.list_workflows()}")

        except Exception as e:
            logger.error(f"Failed to register workflows: {str(e)}", exc_info=True)
            raise

    def _get_agents_safe(self) -> Optional[Dict[str, Any]]:
        """Safely get agents with validation."""
        try:
            agents = get_real_agents()
            if not isinstance(agents, dict) or len(agents) != 4:
                logger.error(f"Invalid agents: {agents}")
                return None
            return agents
        except Exception as e:
            logger.error(f"Failed to get agents: {str(e)}", exc_info=True)
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _check_databases(self, skip_non_pg: bool = False) -> Dict[str, bool]:
        """Check database health with retry logic. Skip Neo4j/Astra if configured."""
        try:
            manager = get_triple_db_manager()
            results = {
                'postgres': False,
                'neo4j': False,
                'astra': False
            }

            pg = getattr(manager, 'pg', None)
            if pg and hasattr(pg, 'health'):
                results['postgres'] = pg.health()

            if getattr(manager, 'neo4j', None) is not None:
                try:
                    results['neo4j'] = True  # TODO: Add manager.neo4j.ping() if available
                except Exception:
                    results['neo4j'] = skip_non_pg

            if getattr(manager, 'astra', None) is not None:
                try:
                    results['astra'] = True  # TODO: Add manager.astra.health() if available
                except Exception:
                    results['astra'] = skip_non_pg

            return results
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}", exc_info=True)
            raise

    def list_workflows(self) -> List[str]:
        """List all registered workflow names."""
        return list(self.workflows.keys()) + list(self.factories.keys())

    def get_workflow(self, name: str) -> Optional[WorkflowType]:
        """Get compiled workflow by name."""
        return self.workflows.get(name)

    def get_factory(self, name: str) -> Optional[WorkflowFactory]:
        """Get raw workflow factory by name."""
        if name in self.factories:
            return self.factories[name]
        logger.warning(f"Factory '{name}' not found. Available: {list(self.factories)}")
        return None

    @property
    def is_healthy(self) -> bool:
        """Overall health status."""
        return self._healthy_cache

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def init(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize/validate workflows and dependencies.
        Args:
            config: {'skip_db_non_pg': bool}
        """
        config = config or {}
        skip_non_pg = config.get('skip_db_non_pg', False)
        
        try:
            # Check databases
            db_status = self._check_databases(skip_non_pg=skip_non_pg)
            dbs_ok = all(db_status.values())

            # Check agents
            agents = self._get_agents_safe()
            agents_ok = agents is not None

            # Register workflows (will retry if fails)
            self._register_workflows()

            self._healthy_cache = dbs_ok and agents_ok

            return {
                'status': 'success',
                'workflows': self.list_workflows(),
                'db_status': db_status,
                'dbs_healthy': dbs_ok,
                'agents_ready': agents_ok,
                'healthy': self.is_healthy,
                'message': 'WorkflowManager ready'
            }
        except Exception as e:
            logger.error(f"WorkflowManager init failed: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'workflows': self.list_workflows(),
                'db_status': {},
                'dbs_healthy': False,
                'agents_ready': False,
                'healthy': False,
                'message': str(e)
            }

    async def execute_workflow(
        self,
        name: str,
        input_data: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute a workflow asynchronously.
        Handles both compiled workflows and factories.
        """
        workflow = self.get_workflow(name)
        factory = self.get_factory(name)
        if workflow is None and factory is None:
            return {
                'status': 'error',
                'message': f"Workflow '{name}' not found. Compiled: {list(self.workflows)}, Factories: {list(self.factories)}"
            }

        try:
            if factory:
                result = factory(**input_data, **kwargs)
            else:
                result = await workflow.ainvoke(input_data, **kwargs)

            return {
                'status': 'success',
                'result': result,
                'workflow': name
            }
        except Exception as e:
            logger.error(f"Workflow '{name}' execution failed: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'workflow': name
            }

    def close(self) -> None:
        """Clean up resources."""
        self.workflows.clear()
        self.factories.clear()
        logger.info("WorkflowManager closed")

# Singleton instance
manager = WorkflowManager()

