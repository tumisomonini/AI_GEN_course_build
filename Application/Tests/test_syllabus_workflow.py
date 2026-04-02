import pytest
from unittest.mock import Mock, MagicMock
from Application.Workflows.syllabus_workflow import create_syllabus_workflow, SyllabusState
from Application.Agents.Planner_agent import PlannerAgent
from Application.Agents.Author_agent import AuthorAgent
from Application.Agents.Reviewer_agent import ReviewerAgent
from Application.Agents.Assembler_agent import AssemblerAgent

@pytest.fixture
def mock_planner():
    planner = Mock(spec=PlannerAgent)
    planner.generate_syllabus.return_value = ["Intro to Python", "Advanced Python"]
    return planner

@pytest.fixture
def mock_author():
    author = Mock(spec=AuthorAgent)
    author.generate_content.return_value = "Mock content for topic"
    return author

@pytest.fixture
def mock_reviewer():
    reviewer = Mock(spec=ReviewerAgent)
    reviewer.validate_factual_grounding.return_value = True
    reviewer.validate_style.return_value = True
    return reviewer

@pytest.fixture
def mock_assembler():
    assembler = Mock(spec=AssemblerAgent)
    assembler.export_to_docx = Mock()
    return assembler

def test_workflow_compilation(mock_planner, mock_author, mock_reviewer, mock_assembler):
    workflow = create_syllabus_workflow(mock_planner, mock_author, mock_reviewer, mock_assembler)
    assert workflow is not None

def test_workflow_execution(mock_planner, mock_author, mock_reviewer, mock_assembler):
    workflow = create_syllabus_workflow(mock_planner, mock_author, mock_reviewer, mock_assembler)
    initial_state = {"title": "Test course", "topics": ["Intro", "Advanced"], "syllabus": [], "chapters": {}, "validated": False}
    result = workflow.invoke(initial_state)
    assert len(result["syllabus"]) == 2
    assert len(result["chapters"]) == 2
    assert result["validated"] == True
    mock_assembler.export_to_docx.assert_called()
