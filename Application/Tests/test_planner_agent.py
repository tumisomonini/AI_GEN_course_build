import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.abspath('../../'))
from Application.Agents.Planner_agent import PlannerAgent
import sys
import os
sys.path.insert(0, os.path.abspath('../../'))
from Application.Ports.neo4j_repo import Neo4jRepository



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

    # Patch KnowledgeGraph since PlannerAgent uses it for ordering
    with patch('Application.Agents.Planner_agent.KnowledgeGraph') as mock_kg_class:
        mock_kg = mock_kg_class.return_value
        mock_kg.get_topic_order.return_value = ["ML", "Python"]

        planner = PlannerAgent(mock_neo4j_repo)
        syllabus = planner.generate_syllabus(["Python", "ML"])
        assert syllabus == ["ML", "Python"]
        mock_kg.get_topic_order.assert_called_with(["Python", "ML"])
