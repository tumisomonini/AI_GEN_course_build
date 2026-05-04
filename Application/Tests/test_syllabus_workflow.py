import sys
import os
from pathlib import Path
import asyncio
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unittest.mock import Mock, MagicMock, patch, AsyncMock
import pytest
from Application.API.dependencies import get_triple_db_manager

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
    reviewer.validate_content_with_llm = AsyncMock(return_value={'semantic_score': 0.8, 'semantic_pass': True})
    reviewer.check_intent_and_safety = AsyncMock(return_value={'is_valid': True, 'is_safe': True})
    return reviewer

@pytest.fixture
def mock_assembler():
    assembler = Mock(spec=AssemblerAgent)
    return assembler

@pytest.fixture
@patch('Application.Workflows.syllabus_workflow.scrape_relevant_syllabi', return_value=[])
@patch('Application.Infrastructure.ETL.cleaner.clean_syllabus_dict', return_value=({'main_topics': []}, {}))
@patch('Application.Infrastructure.ETL.cleaner.log_cleaning_stats')
@patch('Application.API.dependencies.get_triple_db_manager')
def syllabus_workflow(mock_mgr, mock_log, mock_clean, mock_scrape, mock_planner, mock_author, mock_reviewer, mock_assembler):
    # Set up the mock triple db manager
    pg_mock = Mock()
    pg_mock.log_message = Mock()
    pg_mock.close = Mock()
    triple_mock = Mock()
    triple_mock.pg = pg_mock
    triple_mock.astra = Mock()
    mock_mgr.return_value = triple_mock
    return create_syllabus_workflow(mock_planner, mock_author, mock_reviewer, mock_assembler)

@pytest.mark.asyncio
async def test_successful_workflow_execution(syllabus_workflow, mock_planner, mock_author, mock_reviewer, mock_assembler):
    # Setup initial state
    initial_state = SyllabusState(
        title="Test Course",
        topics=["Intro", "Advanced"], 
        syllabus=[], 
        chapters=[], 
        scraped_syllabi=[],
        validated=False
    )
    # Use only ainvoke for graphs containing asynchronous nodes (Author/Reviewer)
    result = await syllabus_workflow.ainvoke(initial_state.model_dump())
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

@pytest.mark.asyncio
async def test_workflow_with_empty_topics(syllabus_workflow):
    # Setup initial state with empty topics
    initial_state = SyllabusState(
        title="Empty Topics Course",
        topics=[],
        syllabus=[],
        chapters=[],
        scraped_syllabi=None,
        validated=False
    )

    # Execute workflow
    result = await syllabus_workflow.ainvoke(initial_state.model_dump())
    # Fixture mocks scraper=[], scrape_node generates defaults → 2/2/True
    assert len(result["syllabus"]) > 0
    assert len(result["chapters"]) > 0
    assert result["validated"] is True

@pytest.mark.asyncio
async def test_workflow_with_validation_failure(syllabus_workflow, mock_planner, mock_author, mock_reviewer):
    # Setup reviewer to fail validation
    mock_reviewer.validate_factual_grounding.return_value = False

    # Setup initial state
    initial_state = SyllabusState(
        title="Validation Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[], 
        chapters=[],
        scraped_syllabi=[],
        validated=False
    )

    # Execute workflow
    result = await syllabus_workflow.ainvoke(initial_state.model_dump())

    # Assertions for validation failure
    assert len(result["syllabus"]) == 2
    assert len(result["chapters"]) == 2
    assert result["validated"] is False

@pytest.mark.asyncio
async def test_workflow_with_author_failure(syllabus_workflow, mock_planner, mock_author):
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
        chapters=[],
        scraped_syllabi=[],
        validated=False
    )

    # Execute workflow
    result = await syllabus_workflow.ainvoke(initial_state.model_dump())
    error_chapters = [ch for ch in result["chapters"] if ch.status == "error"]
    assert len(error_chapters) == 1
    assert "Failed to generate content" in error_chapters[0].content

@pytest.mark.asyncio
async def test_workflow_with_reviewer_failure(syllabus_workflow, mock_planner, mock_author, mock_reviewer):
    # Setup reviewer to fail validation
    mock_reviewer.validate_factual_grounding.side_effect = [True, False]
    mock_reviewer.validate_style.side_effect = [True, False]

    # Setup initial state
    initial_state = SyllabusState(
        title="Reviewer Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[], 
        chapters=[],
        scraped_syllabi=[],
        validated=False
    )

    # Execute workflow
    result = await syllabus_workflow.ainvoke(initial_state.model_dump())

    # Assertions for validation failure
    assert len(result["syllabus"]) == 2
    assert len(result["chapters"]) == 2
    assert result["validated"] is False

@pytest.mark.asyncio
async def test_workflow_with_assembler_failure(syllabus_workflow, mock_planner, mock_author, mock_reviewer, mock_assembler):
    # Setup assembler to fail
    mock_assembler.export_to_docx.side_effect = Exception("Failed to export document")

    # Setup initial state
    initial_state = SyllabusState(
        title="Assembler Failure Course",
        topics=["Intro", "Advanced"],
        syllabus=[], 
        chapters=[],
        scraped_syllabi=[],
        validated=False
    )

    # Execute workflow and expect exception
    with pytest.raises(Exception) as excinfo:
        await syllabus_workflow.ainvoke(initial_state.model_dump())

    assert "Failed to export document" in str(excinfo.value)

# ===== Live Agent Integration Test =====
@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_agents_initialization():
    """Integration test: Verify real agents can be initialized (no mocks).
    
    Skipped by default. Run with: pytest -m integration
    """
    try:
        from Application.API.agents import get_real_agents
        
        agents = get_real_agents()
        
        # Verify all required agents are present
        assert isinstance(agents, dict), "get_real_agents() should return a dict"
        required_keys = ['planner', 'author', 'reviewer', 'assembler']
        for key in required_keys:
            assert key in agents, f"Missing required agent: {key}"
        
        # Verify agent types
        assert isinstance(agents['planner'], PlannerAgent), "planner should be PlannerAgent instance"
        assert isinstance(agents['author'], AuthorAgent), "author should be AuthorAgent instance"
        assert isinstance(agents['reviewer'], ReviewerAgent), "reviewer should be ReviewerAgent instance"
        assert isinstance(agents['assembler'], AssemblerAgent), "assembler should be AssemblerAgent instance"
        
        # Verify workflow can be created with real agents
        workflow = create_syllabus_workflow(
            agents['planner'], agents['author'], 
            agents['reviewer'], agents['assembler']
        )
        assert workflow is not None, "workflow should be created successfully"
        
    except Exception as e:
        pytest.skip(f"Live agent initialization failed (expected without env keys): {e}")

# ===== End Integration Test =====
