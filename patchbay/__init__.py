"""Rectangular fabric patch planning in integer millimetres."""

from patchbay.model import Piece, Spec, Stock, parse_spec
from patchbay.packing import build_plan, validate_plan

__all__ = ["Piece", "Spec", "Stock", "parse_spec", "build_plan", "validate_plan"]
