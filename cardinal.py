"""Compatibility facade for plugins written for FunPay Cardinal.

Sigma keeps its runtime implementation in :mod:`sigma`, but Cardinal plugins
historically import the application module as ``cardinal``. Re-export the full
public Sigma namespace so imports such as ``from cardinal import FunPayAPI``
and ``from cardinal import types`` continue to work as well as the canonical
``Cardinal`` import.
"""

import sigma as _sigma
from sigma import *

Account = _sigma.FunPayAPI.Account
Runner = _sigma.FunPayAPI.Runner
events = _sigma.FunPayAPI.events
exceptions = _sigma.FunPayAPI.exceptions
types = _sigma.FunPayAPI.types

__all__ = [name for name in globals() if not name.startswith("_")]
