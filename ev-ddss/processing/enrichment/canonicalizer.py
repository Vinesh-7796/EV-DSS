"""Alias resolution and name canonicalization for engineering entities.

Merges synonymous names into a single canonical form using a built-in
alias dictionary and fuzzy matching.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set

from backend.logger import logger
from processing.enrichment.models import (
    CanonicalEntity,
    Entity,
    EntityRelationship,
    ALL_ENTITY_TYPES,
)


# ──────────────────────────────────────────────
#  Built-in engineering alias dictionary
# ──────────────────────────────────────────────

BUILTIN_ALIASES: Dict[str, str] = {
    # ECUs / Controllers
    "MCU": "Motor Controller Unit",
    "Motor Controller": "Motor Controller Unit",
    "MotorControl Unit": "Motor Controller Unit",
    "Traction Inverter": "Motor Controller Unit",
    "Inverter": "Motor Controller Unit",
    "VCU": "Vehicle Control Unit",
    "Vehicle Controller": "Vehicle Control Unit",
    "BMS": "Battery Management System",
    "Battery Manager": "Battery Management System",
    "Battery Management": "Battery Management System",
    "HCU": "Hybrid Control Unit",
    "GCU": "Generator Control Unit",
    "TCU": "Transmission Control Unit",
    "BCM": "Body Control Module",
    "ECU": "Electronic Control Unit",
    "DCU": "Door Control Unit",
    "SCU": "Seat Control Unit",
    # Systems / Subsystems
    "HV": "High Voltage System",
    "High Voltage": "High Voltage System",
    "LV": "Low Voltage System",
    "Low Voltage": "Low Voltage System",
    "Cooling System": "Thermal Management System",
    "Thermal System": "Thermal Management System",
    "HVAC": "Heating Ventilation Air Conditioning",
    # Measurements
    "RPM": "Revolutions Per Minute",
    "rpm": "Revolutions Per Minute",
    "SOC": "State of Charge",
    "SOH": "State of Health",
    "DTC": "Diagnostic Trouble Code",
    "CAN": "Controller Area Network",
    "LIN": "Local Interconnect Network",
    "PWM": "Pulse Width Modulation",
    # Sensors
    "Temp Sensor": "Temperature Sensor",
    "Temperature Sens": "Temperature Sensor",
    "Press Sensor": "Pressure Sensor",
    "Pressure Sens": "Pressure Sensor",
    "Speed Sensor": "Speed Sensor",
    "Position Sensor": "Position Sensor",
    # Components
    "HV Battery": "Traction Battery",
    "Traction Battery": "Traction Battery",
    "Main Battery": "Traction Battery",
    "ESS": "Energy Storage System",
    "Motor Gen": "Motor Generator",
    "MG": "Motor Generator",
    "DC-DC": "DC-DC Converter",
    "DCDC": "DC-DC Converter",
    "OBC": "On-Board Charger",
    "Charger": "On-Board Charger",
    "PTC": "Positive Temperature Coefficient Heater",
    "PTC Heater": "Positive Temperature Coefficient Heater",
}

# Reverse alias map: canonical → list of known aliases
_BUILTIN_CANONICAL_TO_ALIASES: Dict[str, List[str]] = {}
for alias, canonical in BUILTIN_ALIASES.items():
    _BUILTIN_CANONICAL_TO_ALIASES.setdefault(canonical, []).append(alias)


class Canonicalizer:
    """Resolves entity aliases to canonical names and merges entities.

    Two-phase approach:

    1. **Name resolution** — look up each entity name in the built-in alias
       dictionary.  If found, use the canonical name.
    2. **Fuzzy grouping** — group entities with the same canonical name
       (or exact name when no alias exists) and merge them into a single
       ``CanonicalEntity``.

    The resulting ``CanonicalEntity`` list is the canonical entity index.
    """

    def __init__(self, custom_aliases: Optional[Dict[str, str]] = None) -> None:
        self._alias_map: Dict[str, str] = dict(BUILTIN_ALIASES)
        if custom_aliases:
            self._alias_map.update(custom_aliases)

    # ── Public API ──────────────────────────────

    def canonicalize(self, entities: List[Entity]) -> List[CanonicalEntity]:
        """Resolve a list of extracted entities to canonical entities.

        1. Resolve each entity's name to a canonical form.
        2. Group entities with identical canonical name + type.
        3. Return a deduplicated list of ``CanonicalEntity``.
        """
        groups: Dict[str, List[Entity]] = {}

        for ent in entities:
            canonical_name = self._resolve(ent.name)
            group_key = f"{ent.type}::{canonical_name}"

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(ent)

        result: List[CanonicalEntity] = []
        for group_key, group_entities in groups.items():
            etype, cname = group_key.split("::", 1)
            canonical = self._merge_group(etype, cname, group_entities)
            result.append(canonical)

        logger.info("Canonicalizer: {} entities → {} canonical", len(entities), len(result))
        return result

    # ── Internal ────────────────────────────────

    def _resolve(self, name: str) -> str:
        """Look up *name* in the alias map; return the canonical form.

        Falls back to the original name when no alias is registered.
        """
        trimmed = name.strip()
        if not trimmed:
            return name
        return self._alias_map.get(trimmed, trimmed)

    @staticmethod
    def _merge_group(etype: str, canonical_name: str, entities: List[Entity]) -> CanonicalEntity:
        """Merge a group of entities with the same canonical name."""
        all_aliases: Set[str] = set()
        all_entity_ids: List[str] = []
        all_sources: Set[str] = set()
        merged_meta: Dict[str, Any] = {}

        for ent in entities:
            all_entity_ids.append(ent.id)
            if ent.name and ent.name != canonical_name:
                all_aliases.add(ent.name)
            all_aliases.update(ent.aliases)
            if ent.source_document:
                all_sources.add(ent.source_document)
            merged_meta.update(ent.metadata)

        # Also add built-in aliases for this canonical name
        if canonical_name in _BUILTIN_CANONICAL_TO_ALIASES:
            for a in _BUILTIN_CANONICAL_TO_ALIASES[canonical_name]:
                if a != canonical_name:
                    all_aliases.add(a)

        if all_aliases and canonical_name in all_aliases:
            all_aliases.discard(canonical_name)

        raw_id = f"{etype}::{canonical_name}"
        cid = f"CENT_{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"

        return CanonicalEntity(
            id=cid,
            type=etype,
            canonical_name=canonical_name,
            aliases=sorted(all_aliases),
            entity_ids=list(dict.fromkeys(all_entity_ids)),
            source_documents=sorted(all_sources),
            metadata=merged_meta,
        )

    @property
    def alias_dictionary(self) -> Dict[str, str]:
        """Return the full alias → canonical-name map."""
        return dict(self._alias_map)
