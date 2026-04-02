import pytest
from unittest.mock import Mock, patch
from Application.Agents.Planner_agent import PlannerAgent
from Application.Ports.neo4j_repo import Neo4jRepository
import networkx as nx
from node2vec import Node2Vec
from unittest.mock import MagicMock

@pytest.fixture
def mock_neo4j_repo():
    session_context = MagicMock()
    session_context.run.side_effect = [
        [{'id': 'ML'}, {'id': 'Python'}],
        [{'source': 'Python', 'target': 'ML'}]
    ]
    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_context
    repo = MagicMock()
    repo.driver.session.return_value = session_mock
    return repo

def test_planner_generate_syllabus(mock_neo4j_repo):
    class FakeVector:
        def __init__(self, scalar):
            self.scalar = scalar

        def dot(self, other):
            return self.scalar * other.scalar

    with patch('networkx.Graph') as mock_G, \
         patch('Application.Agents.Planner_agent.Node2Vec') as mock_n2v:

        mock_graph = mock_G.return_value
        mock_model = mock_n2v.return_value.fit.return_value
        mock_model.wv.__contains__.return_value = True
        mock_model.wv.__getitem__.side_effect = lambda x: FakeVector(1.0 if x == "ML" else 0.5)

        planner = PlannerAgent("bolt://test", "user", "pass")
        planner.graph_repo = mock_neo4j_repo
        
        syllabus = planner.generate_syllabus(["Python", "ML"])
        assert syllabus == ["ML", "Python"]  # sorted reverse
        mock_n2v.assert_called()
