# -*- coding: utf-8 -*-
"""
Agents for YouTube video analysis.

This package contains extraction agents:
- extraction: Transcript → structured arguments (LLM-powered)

Argument analysis (research, enrichment, pros/cons, reliability) is delegated
to the evidence-engine service via app/services/evidence_engine.py.
"""
from .extraction import extract_arguments, structure_to_dict

__all__ = [
    "extract_arguments",
    "structure_to_dict",
]
