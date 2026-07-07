"""Persistence for the Canonical Entity Index and Alias Dictionary.

The index and dictionary are stored as JSON files in ``data/knowledge/``
and can be loaded / saved independently of the KnowledgeStore.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.enrichment.models import (
    CanonicalEntity,
    EntityRelationship,
)


class CanonicalEntityIndex:
    """Maintains the canonical entity index as a JSON file.

    The index maps ``{entity_id -> {name, type, aliases, sources, relationships}}``.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path or Path("data") / "knowledge" / "canonical_entity_index.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self._load()

    # ── Public API ──────────────────────────────

    def save(self, entities: List[CanonicalEntity]) -> None:
        """Persist the index to disk."""
        self._data = {
            "version": "2.0",
            "updated_at": datetime.now().isoformat(),
            "entity_count": len(entities),
            "entities": {},
        }
        for ce in entities:
            self._data["entities"][ce.id] = {
                "id": ce.id,
                "type": ce.type,
                "canonical_name": ce.canonical_name,
                "aliases": ce.aliases,
                "entity_ids": ce.entity_ids,
                "source_documents": ce.source_documents,
                "relationships": [
                    {
                        "source_entity_id": r.source_entity_id,
                        "target_entity_id": r.target_entity_id,
                        "relationship_type": r.relationship_type,
                        "confidence": r.confidence,
                    }
                    for r in ce.relationships
                ],
                "metadata": ce.metadata,
            }
        self._write()
        logger.info("CanonicalEntityIndex: saved {} entities to {}", len(entities), self._path)

    def load(self) -> List[CanonicalEntity]:
        """Load and return all canonical entities from the index."""
        self._load()
        entities: List[CanonicalEntity] = []
        for eid, raw in self._data.get("entities", {}).items():
            rels = [
                EntityRelationship(
                    source_entity_id=r["source_entity_id"],
                    target_entity_id=r["target_entity_id"],
                    relationship_type=r["relationship_type"],
                    confidence=r.get("confidence", 1.0),
                )
                for r in raw.get("relationships", [])
            ]
            entities.append(CanonicalEntity(
                id=raw.get("id", eid),
                type=raw.get("type", ""),
                canonical_name=raw.get("canonical_name", ""),
                aliases=raw.get("aliases", []),
                entity_ids=raw.get("entity_ids", []),
                source_documents=raw.get("source_documents", []),
                relationships=rels,
                metadata=raw.get("metadata", {}),
            ))
        logger.info("CanonicalEntityIndex: loaded {} entities from {}", len(entities), self._path)
        return entities

    def lookup(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Look up a single entity by its canonical ID."""
        self._load()
        return self._data.get("entities", {}).get(entity_id)

    def search(self, name: str, etype: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for entities by name (case-insensitive substring)."""
        self._load()
        name_lower = name.lower()
        results: List[Dict[str, Any]] = []
        for raw in self._data.get("entities", {}).values():
            if etype and raw.get("type") != etype:
                continue
            if name_lower in raw.get("canonical_name", "").lower():
                results.append(raw)
                continue
            for alias in raw.get("aliases", []):
                if name_lower in alias.lower():
                    results.append(raw)
                    break
        return results

    @property
    def path(self) -> Path:
        return self._path

    # ── Internal ────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {"version": "2.0", "entities": {}}

    def _write(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


class AliasDictionary:
    """Maintains the alias → canonical-name dictionary as a JSON file."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path or Path("data") / "knowledge" / "alias_dictionary.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self._load()

    # ── Public API ──────────────────────────────

    def save(self, alias_map: Dict[str, str]) -> None:
        """Persist the alias dictionary to disk."""
        self._data = {
            "version": "2.0",
            "updated_at": datetime.now().isoformat(),
            "alias_count": len(alias_map),
            "aliases": dict(alias_map),
        }
        self._write()
        logger.info("AliasDictionary: saved {} aliases to {}", len(alias_map), self._path)

    def load(self) -> Dict[str, str]:
        """Load and return the alias → canonical-name map."""
        self._load()
        return dict(self._data.get("aliases", {}))

    def resolve(self, name: str) -> str:
        """Look up a single name; returns canonical name or original."""
        aliases = self.load()
        return aliases.get(name, name)

    @property
    def path(self) -> Path:
        return self._path

    # ── Internal ────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {"version": "2.0", "aliases": {}}

    def _write(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
