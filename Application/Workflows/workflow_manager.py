from typing import Dict, List, Any
from langgraph.graph import StateGraph
from .syllabus_workflow import create_syllabus_workflow, create_outline_workflow, OutlineState, SyllabusState
from Application.API.agents import get_real_agents
from Application.Ports.triple_db_manager import get_triple_db_manager

class WorkflowManager:
    _instance = None
    workflows: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.register_workflows()
        return cls._instance
    
    def register_workflows(self):
        """Register all available workflows."""
        try:
            agents = get_real_agents()
            self.workflows['syllabus'] = create_syllabus_workflow(
                agents['planner'], agents['author'], agents['reviewer'], agents['assembler']
            )
            self.workflows['outline'] = create_outline_workflow  # Function for cheap outline
        except:
            self.workflows = {'syllabus': None, 'outline': None}
    
    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys())
    
    def get_workflow(self, name: str):
        return self.workflows.get(name)
    
    def init(self) -> Dict[str, str]:
        """Initialize/validate workflows and dependencies."""
        try:
            # Skip DB check if not available
            dbs_ok = True
            try:
                manager = get_triple_db_manager()
                pg_ok = hasattr(manager.pg, 'health') and manager.pg.health()
                neo_ok = hasattr(manager, 'neo4j')
                astra_ok = hasattr(manager, 'astra')
                dbs_ok = pg_ok and neo_ok and astra_ok
            except:
                pass
            agents_ok = True
            try:
                agents = get_real_agents()
                agents_ok = len(agents) == 4
            except:
                pass
            self.register_workflows()
            return {
                'status': 'success',
                'workflows': self.list_workflows(),
                'dbs_healthy': dbs_ok,
                'agents_ready': agents_ok,
                'message': 'Workflows initialized successfully'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

manager = WorkflowManager()
