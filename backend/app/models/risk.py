"""Risk scenarios and simulation results."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, json_type


class Scenario(Base, TimestampMixin):
    """A named risk scenario.

    ``status`` is ``catalogue`` for a declared scenario that has no numeric model yet, and
    ``specified`` once ``spec`` holds a full FAIR scenario definition (see
    ``app.risk.schemas.ScenarioSpec``).
    """

    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    service_id: Mapped[str | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="catalogue")
    attack_techniques: Mapped[list] = mapped_column(json_type(), default=list)
    cve_ids: Mapped[list] = mapped_column(json_type(), default=list)
    spec: Mapped[dict | None] = mapped_column(json_type())


class Simulation(Base, TimestampMixin):
    """A reproducible simulation run of a scenario."""

    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(120))
    seed: Mapped[int] = mapped_column(Integer, default=42)
    n_trials: Mapped[int] = mapped_column(Integer, default=10_000)
    model_version: Mapped[str | None] = mapped_column(String(32))
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)

    eal: Mapped[float | None] = mapped_column(Float)
    p50: Mapped[float | None] = mapped_column(Float)
    p90: Mapped[float | None] = mapped_column(Float)
    p95: Mapped[float | None] = mapped_column(Float)
    p99: Mapped[float | None] = mapped_column(Float)
    cvar_95: Mapped[float | None] = mapped_column(Float)
    vulnerability: Mapped[float | None] = mapped_column(Float)

    result: Mapped[dict | None] = mapped_column(json_type())
