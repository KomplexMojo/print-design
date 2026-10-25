"""Fit clearances calibrated for this printer, read from printer/h2s.yaml."""

from __future__ import annotations

from functools import lru_cache

from . import config


@lru_cache
def _fits() -> dict:
    return config.printer_config()["fits"]


def clearance(kind: str) -> float:
    """Per-side clearance in mm for a fit: press, snug, slide or loose."""
    fits = _fits()
    if kind not in fits:
        raise KeyError(f"Unknown fit '{kind}'. Choose from {', '.join(k for k in fits if k != 'hole_shrink_mm')}")
    return fits[kind]


def hole(diameter: float, fit: str = "slide") -> float:
    """Modeled diameter for a vertical hole that should take a `diameter` shaft with the given fit."""
    return diameter + 2 * clearance(fit) + _fits()["hole_shrink_mm"]


def shaft(diameter: float, fit: str = "slide") -> float:
    """Modeled diameter for a shaft that should go into a `diameter` hole with the given fit."""
    return diameter - 2 * clearance(fit)
