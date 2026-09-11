"""API route modules.

``health`` is mounted at the root; the analytical routers are mounted under ``/api/v1``.
"""

from app.api.routes import (
    ai,
    catalog,
    compliance,
    health,
    optimization,
    simulation,
    whatif,
)

API_V1_ROUTERS = (
    catalog.router,
    simulation.router,
    optimization.router,
    whatif.router,
    compliance.router,
    ai.router,
)
API_V1_PREFIX = "/api/v1"

__all__ = [
    "API_V1_PREFIX",
    "API_V1_ROUTERS",
    "ai",
    "catalog",
    "compliance",
    "health",
    "optimization",
    "simulation",
    "whatif",
]
