import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import Mock, MagicMock, patch
from Application.Workflows.syllabus_workflow import create_syllabus_workflow
from Domain.syllabus import SyllabusState
from Domain.course import Chapter
from Application.Agents.Planner_agent import PlannerAgent
from Application.Agents.Author_agent import AuthorAgent
from Application.Agents.Reviewer_agent import ReviewerAgent
from Application.Agents.Assembler_agent import AssemblerAgent

@pytest.fixture
def mock_planner():
    planner = Mock(spec=PlannerAgent)
    planner.generate_syllabus.return_value = ["Intro", "Advanced"]
    return planner

@pytest.fixture
def mock_author():
    author = Mock(spec=AuthorAgent)
    author.generate_content.side_effect = [
        Chapter(title="Intro", content="Detailed content for Intro.", chapter_order=1, status="generated"),
        Chapter(title="Advanced", content="Detailed content for Advanced.", chapter_order=2, status="generated")
    ]
    return author

@pytest.fixture
def mock_reviewer():
    reviewer = Mock(spec=ReviewerAgent)
    reviewer.validate_factual_grounding.return_value = True
    reviewer.validate_style.return_value = True
    reviewer.validate_coverage.return_value = 0.9
    return reviewer

@pytest.fixture
def mock_assembler():
    assembler = Mock(spec=AssemblerAgent)
    return assembler

@pytest.fixture
def syllabus_workflow(mock_planner, mock_author, mock_reviewer, mock_assembler):
    return create_syllabus_workflow(mock_planner, mock_author, mock_reviewer, mock_assembler)

def test_successful_workflow_execution(syllabus_workflow, mock_planner, mock_author, mock_reviewer, mock_assembler):
    # Setup initial state
    initial_state = SyllabusState(
        title="Test Course", 
        topics=["Intro", "Advanced"], 
        syllabus=[], 
        chapters={}, 
        validated=False
    )
    # Pydantic v2 model_dump() is used for LangGraph compatibility
    result = syllabus_workflow.invoke(initial_state.model_dump())

    # Assertions
    assert len(result["syllabus"]) == 2
    assert len(result["chapters"]) == 2
    assert result["validated"] is True

    # Verify planner was called
    mock_planner.generate_syllabus.assert_called_once_with(["Intro", "Advanced"])

    # Verify author was called for each topic
    assert mock_author.generate_content.call_count == 2

    # Verify reviewer was called for each chapter
    assert mock_reviewer.validate_factual_grounding.call_count == 2
    assert mock_reviewer.validate_style.call_count == 2

    # Verify assembler was called
    mock_assembler.export_to_docx.assert_called_once()

def test_workflow_with_empty_topics(syllabus_workflow):
    # Setup initial state with empty topics
    initial_state = SyllabusState(
        title="Empty Topics Course",
        topics=[],
        syllabus=[],
        chapters={},
        validated=False
    )

    # Execute workflow
    result = syllabus_workflow.invoke(initial_state.model_dump())

    # Assertions for empty topics
    assert len(result["syllabus"]) == 0
    assert len(result["chapters"]) == 0
    assert result["validated"] is False

def test_workflow_with_validation_failure(syllabus_workflow, mock_planner, mock_author, mock_reviewer):
    # Setup reviewer to fail validation
    mock_reviewer.validate_factual_grounding.return_value = False

    # Setup initial state
    initial_state = SyllabusState(
        title="Validation Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[],
        chapters={},
        validated=False
    )

    # Execute workflow
    result = syllabus_workflow.invoke(initial_state.model_dump())

    # Assertions for validation failure
    assert len(result["syllabus"]) == 2
    assert len(result["chapters"]) == 2
    assert result["validated"] is False

def test_workflow_with_author_failure(syllabus_workflow, mock_planner, mock_author):
    # Setup author to fail content generation
    mock_author.generate_content.side_effect = [
        Chapter(title="Intro", content="Detailed content for Intro.", chapter_order=1, status="generated"),
        Exception("Failed to generate content")
    ]

    # Setup initial state
    initial_state = SyllabusState(
        title="Author Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[],
        chapters={},
        validated=False
    )

    # Execute workflow and expect exception
    with pytest.raises(Exception) as excinfo:
        syllabus_workflow.invoke(initial_state.model_dump())

    assert "Failed to generate content" in str(excinfo.value)

def test_workflow_with_reviewer_failure(syllabus_workflow, mock_planner, mock_author, mock_reviewer):
    # Setup reviewer to fail validation
    mock_reviewer.validate_factual_grounding.side_effect = [True, False]
    mock_reviewer.validate_style.side_effect = [True, False]

    # Setup initial state
    initial_state = SyllabusState(
        title="Reviewer Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[],
        chapters={},
        validated=False
    )

    # Execute workflow
    result = syllabus_workflow.invoke(initial_state.model_dump())

    # Assertions for validation failure
    assert len(result["syllabus"]) == 2
    assert len(result["chapters"]) == 2
    assert result["validated"] is False

def test_workflow_with_assembler_failure(syllabus_workflow, mock_planner, mock_author, mock_reviewer, mock_assembler):
    # Setup assembler to fail
    mock_assembler.export_to_docx.side_effect = Exception("Failed to export document")

    # Setup initial state
    initial_state = SyllabusState(
        title="Assembler Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[],
        chapters={},
        validated=False
    )

    # Execute workflow and expect exception
    with pytest.raises(Exception) as excinfo:
        syllabus_workflow.invoke(initial_state.model_dump())

    assert "Failed to export document" in str(excinfo.value)
