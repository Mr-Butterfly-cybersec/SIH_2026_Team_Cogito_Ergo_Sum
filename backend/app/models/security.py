"""Security posture: vulnerabilities, findings, controls and their evidence."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, json_type

if TYPE_CHECKING:
    from app.models.org import Asset


class Vulnerability(Base, TimestampMixin):
    """A CVE enriched from public intelligence (see app.ingestion)."""

    __tablename__ = "vulnerabilities"

    cve_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    published: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(64))

    cvss_version: Mapped[str | None] = mapped_column(String(8))
    cvss_base_score: Mapped[float | None] = mapped_column(Float, index=True)
    cvss_severity: Mapped[str | None] = mapped_column(String(16), index=True)
    cvss_vector: Mapped[str | None] = mapped_column(String(255))
    cwes: Mapped[list] = mapped_column(json_type(), default=list)
    affected_cpe: Mapped[list] = mapped_column(json_type(), default=list)

    epss: Mapped[float | None] = mapped_column(Float, index=True)
    epss_percentile: Mapped[float | None] = mapped_column(Float)
    epss_date: Mapped[date | None] = mapped_column(Date)

    kev: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    kev_date_added: Mapped[date | None] = mapped_column(Date)
    kev_due_date: Mapped[date | None] = mapped_column(Date)
    kev_ransomware: Mapped[bool] = mapped_column(Boolean, default=False)
    kev_required_action: Mapped[str | None] = mapped_column(Text)

    attack_techniques: Mapped[list] = mapped_column(json_type(), default=list)
    references: Mapped[list] = mapped_column(json_type(), default=list)
    sources: Mapped[list] = mapped_column(json_type(), default=list)
    provenance: Mapped[list] = mapped_column(json_type(), default=list)

    findings: Mapped[list[Finding]] = relationship(back_populates="vulnerability")


class Finding(Base, TimestampMixin):
    """An observed issue on an asset, optionally tied to a CVE."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    cve_id: Mapped[str | None] = mapped_column(
        ForeignKey("vulnerabilities.cve_id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(64), default="unknown")
    raw_severity: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="open")
    detected_at: Mapped[date | None] = mapped_column(Date)

    asset: Mapped[Asset] = relationship(back_populates="findings")
    vulnerability: Mapped[Vulnerability | None] = relationship(back_populates="findings")


class Control(Base, TimestampMixin):
    """A security control, mapped to the FAIR factor it moves."""

    __tablename__ = "controls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32), default="resistive")
    factor: Mapped[str] = mapped_column(String(32), default="resistance_strength")
    effectiveness: Mapped[float | None] = mapped_column(Float, index=True)
    applies_to_assets: Mapped[list] = mapped_column(json_type(), default=list)
    cost: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[list] = mapped_column(json_type(), default=list)

    evidence: Mapped[ControlEvidence | None] = relationship(
        back_populates="control", cascade="all, delete-orphan", uselist=False
    )


class ControlEvidence(Base, TimestampMixin):
    """Evidence behind a control's effectiveness (never a bare yes/no)."""

    __tablename__ = "control_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_id: Mapped[str] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), index=True
    )
    coverage: Mapped[float | None] = mapped_column(Float)
    configuration_strength: Mapped[float | None] = mapped_column(Float)
    policy_compliance: Mapped[float | None] = mapped_column(Float)
    recent_incident_signal: Mapped[float | None] = mapped_column(Float)
    verification_age_days: Mapped[int | None] = mapped_column(Integer)
    measured_at: Mapped[date | None] = mapped_column(Date)

    control: Mapped[Control] = relationship(back_populates="evidence")
