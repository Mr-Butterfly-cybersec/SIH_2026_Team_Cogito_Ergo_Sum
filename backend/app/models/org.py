"""Organizational hierarchy: Organization → BusinessUnit → Service → Asset."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, json_type

if TYPE_CHECKING:
    from app.models.security import Finding


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    description: Mapped[str | None] = mapped_column(Text)
    framework_scope: Mapped[list] = mapped_column(json_type(), default=list)

    business_units: Mapped[list[BusinessUnit]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class BusinessUnit(Base, TimestampMixin):
    __tablename__ = "business_units"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    criticality: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship(back_populates="business_units")
    services: Mapped[list[Service]] = relationship(
        back_populates="business_unit", cascade="all, delete-orphan"
    )


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_unit_id: Mapped[str] = mapped_column(
        ForeignKey("business_units.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    revenue_dependency: Mapped[int | None] = mapped_column(Integer)
    regulatory_scope: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    business_unit: Mapped[BusinessUnit] = relationship(back_populates="services")
    assets: Mapped[list[Asset]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    service_id: Mapped[str | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32), default="internal")
    owner: Mapped[str | None] = mapped_column(String(120))
    internet_exposed: Mapped[bool] = mapped_column(Boolean, default=False)
    rto_hours: Mapped[float | None] = mapped_column(Float)

    # criticality dimensions + derived score (see app.risk.asset_criticality)
    criticality: Mapped[dict] = mapped_column(json_type(), default=dict)
    criticality_score: Mapped[float | None] = mapped_column(Float, index=True)
    criticality_band: Mapped[str | None] = mapped_column(String(16), index=True)

    tags: Mapped[list] = mapped_column(json_type(), default=list)
    provenance: Mapped[list] = mapped_column(json_type(), default=list)

    service: Mapped[Service | None] = relationship(back_populates="assets")
    findings: Mapped[list[Finding]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
