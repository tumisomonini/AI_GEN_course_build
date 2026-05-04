"""Workflows package init.

Provides workflow constructors and node functions for syllabus generation.
"""

from .syllabus_workflow import (
    create_syllabus_workflow,
    create_outline_workflow,
    create_real_syllabus_workflow,
    OutlineState,
    scrape_node,
    planner_node,
    author_node,
    reviewer_node,
    assemble_node,
    planner_node_outline,
)

from .workflow_manager import manager

__all__ = [
    "create_syllabus_workflow",
    "create_outline_workflow",
    "create_real_syllabus_workflow",
    "OutlineState",
    "scrape_node",
    "planner_node",
    "author_node",
    "reviewer_node",
    "assemble_node",
    "planner_node_outline",
    "manager",
]

