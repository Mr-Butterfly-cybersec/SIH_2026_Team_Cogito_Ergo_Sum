"""Telemetry ingestion: adapters for public intelligence and organization sources."""

from app.ingestion.base import HttpClient, TelemetryAdapter
from app.ingestion.csv_adapter import CsvAdapter
from app.ingestion.epss import EpssClient
from app.ingestion.kev import KevClient
from app.ingestion.mitre import AttackCatalog, AttackTechnique, MitreAttackClient
from app.ingestion.models import (
    AssetRecord,
    ControlRecord,
    CvssScore,
    EpssScore,
    EventRecord,
    FindingRecord,
    KevEntry,
    VulnerabilityRecord,
)
from app.ingestion.nvd import NvdClient
from app.ingestion.service import EnrichmentReport, EnrichmentService, build_default_service
from app.ingestion.store import VulnerabilityStore
from app.ingestion.synthetic import SyntheticAdapter

__all__ = [
    "AssetRecord",
    "AttackCatalog",
    "AttackTechnique",
    "ControlRecord",
    "CsvAdapter",
    "CvssScore",
    "EnrichmentReport",
    "EnrichmentService",
    "EpssClient",
    "EpssScore",
    "EventRecord",
    "FindingRecord",
    "HttpClient",
    "KevClient",
    "KevEntry",
    "MitreAttackClient",
    "NvdClient",
    "SyntheticAdapter",
    "TelemetryAdapter",
    "VulnerabilityRecord",
    "VulnerabilityStore",
    "build_default_service",
]
