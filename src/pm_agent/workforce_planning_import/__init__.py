"""Versioned workforce and planning clean-import capability.

The package initializer is intentionally side-effect free so schema composition
does not load the import workflow. Callers import the public service contract
from ``pm_agent.workforce_planning_import.service``.
"""
