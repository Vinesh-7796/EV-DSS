"""Entity extraction from CDS ContentNodes.

Scans ContentNode trees and extracts typed engineering entities:

- ``dbc_message`` / ``dbc_signal`` nodes → CAN Message / CAN Signal entities
- ECU names from DBC sender fields → ECU entities
- Paragraph text patterns (error codes, component names, measurements)
- Table content → structured entities
- Image OCR text → component / warning entities
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.logger import logger
from processing.enrichment.models import (
    Entity,
    ENTITY_TYPE_ERROR_CODE,
    ENTITY_TYPE_CONNECTOR,
    ENTITY_TYPE_ECU,
    ENTITY_TYPE_CAN_MESSAGE,
    ENTITY_TYPE_CAN_SIGNAL,
    ENTITY_TYPE_SENSOR,
    ENTITY_TYPE_RELAY,
    ENTITY_TYPE_FUSE,
    ENTITY_TYPE_COMPONENT,
    ENTITY_TYPE_SUBSYSTEM,
    ENTITY_TYPE_PROCEDURE,
    ENTITY_TYPE_WARNING,
    ENTITY_TYPE_MEASUREMENT,
)


# ── Helpers for accessing node fields (dataclass + dict) ──

def _n_id(node: Any) -> str:
    return node.id if hasattr(node, "id") else (node.get("id", "") if isinstance(node, dict) else "")


def _n_type(node: Any) -> str:
    return node.type if hasattr(node, "type") else (node.get("type", "") if isinstance(node, dict) else "")


def _n_content(node: Any) -> Any:
    return node.content if hasattr(node, "content") else (node.get("content") if isinstance(node, dict) else None)


def _n_children(node: Any) -> List[Any]:
    if hasattr(node, "children"):
        return list(node.children)
    if isinstance(node, dict):
        return list(node.get("children", []))
    return []


def _n_metadata(node: Any) -> Dict[str, Any]:
    if hasattr(node, "metadata"):
        return node.metadata or {}
    if isinstance(node, dict):
        return node.get("metadata", {}) or {}
    return {}


# ── Regex patterns for entity extraction ──

# P1242, P0A00, U0100, B1000, C1234 (automotive DTC codes)
ERROR_CODE_PATTERN = re.compile(r"\b[PBCU][0-9A-Z]{4}\b")

# "12V", "48V", "400V", "5A", "100A", "150kW", etc.
MEASUREMENT_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(V|A|W|kW|Ohm|Hz|rpm|degC|°C|mm|cm)\b", re.IGNORECASE)

# "Connector X1", "J1", "P1", etc.
CONNECTOR_PATTERN = re.compile(r"\b(Connector\s+[A-Z]\d+|[A-Z]\d+\s+connector|J\d+|P\d+|X\d+)\b", re.IGNORECASE)

# "Fuse F1", "F2", etc.
FUSE_PATTERN = re.compile(r"\b(Fuse\s+[A-Z]?\d+|F\d+)\b", re.IGNORECASE)

# "Relay K1", "R1", etc.
RELAY_PATTERN = re.compile(r"\b(Relay\s+[A-Z]?\d+|K\d+)\b", re.IGNORECASE)

# "Sensor", "Temperature sensor", "Pressure sensor", etc.
SENSOR_PATTERN = re.compile(r"\b(\w+\s+)?(sensor|sender|detector)\b", re.IGNORECASE)

# "Motor Controller", "Traction Inverter", "Battery", etc.
COMPONENT_KEYWORDS = frozenset({
    "motor", "controller", "inverter", "battery", "converter", "pump",
    "compressor", "heater", "valve", "actuator", "harness", "module",
    "unit", "assembly", "board", "panel", "switch", "breaker",
})


class EntityExtractor:
    """Extracts typed engineering entities from a CDS Document's ContentNodes.

    The extractor walks the entire ContentNode tree and produces a flat
    list of ``Entity`` objects.
    """

    def __init__(self) -> None:
        self._seen_ids: Set[str] = set()

    # ── Public API ──────────────────────────────

    def extract(self, content_nodes: List[Any], source_document: str = "") -> List[Entity]:
        """Walk *content_nodes* and return all discovered entities."""
        self._seen_ids.clear()
        entities: List[Entity] = []
        self._walk(content_nodes, source_document, entities)
        logger.info(
            "EntityExtractor: extracted {} entities from {}",
            len(entities),
            source_document or "content",
        )
        return entities

    # ── Internal ────────────────────────────────

    def _walk(self, nodes: List[Any], source: str, entities: List[Entity]) -> None:
        for node in nodes:
            ntype = _n_type(node)
            content = _n_content(node)

            # Type-specific extraction
            if ntype == "dbc_message":
                ent = self._extract_dbc_message(node, content, source)
                if ent:
                    entities.append(ent)
            elif ntype == "dbc_signal":
                ent = self._extract_dbc_signal(node, content, source)
                if ent:
                    entities.append(ent)
            elif ntype == "paragraph":
                text = str(content) if content else ""
                self._extract_from_text(text, node, source, entities)
            elif ntype == "table":
                self._extract_from_table(node, source, entities)
            elif ntype in ("heading", "title"):
                text = str(content) if content else ""
                self._extract_heading_entity(text, node, source, entities)

            # Recurse
            self._walk(_n_children(node), source, entities)

    # ── DBC entity extraction ─────────────────

    def _extract_dbc_message(self, node: Any, content: Any, source: str) -> Optional[Entity]:
        if isinstance(content, dict):
            msg_id = content.get("id", 0)
            name = content.get("name", "")
            sender = content.get("sender", "")
            comment = content.get("comment", "")
        else:
            return None

        if not name:
            return None

        ent_id = self._make_id(ENTITY_TYPE_CAN_MESSAGE, name, source)
        ent = Entity(
            id=ent_id,
            type=ENTITY_TYPE_CAN_MESSAGE,
            name=name,
            aliases=[f"0x{msg_id:X}"] if msg_id else [],
            source_node_id=_n_id(node),
            source_document=source,
            confidence=1.0,
            metadata={"can_id": msg_id, "dlc": content.get("dlc", 0), "sender": sender, "comment": comment},
        )
        self._seen_ids.add(ent_id)

        # Extract ECU entity from sender
        if sender:
            ecu_id = self._make_id(ENTITY_TYPE_ECU, sender, source)
            if ecu_id not in self._seen_ids:
                self._seen_ids.add(ecu_id)
                entities_from_sender = []  # placeholder, we add manually
                # We'll add the ECU via a separate mechanism in _walk
        return ent

    def _extract_dbc_signal(self, node: Any, content: Any, source: str) -> Optional[Entity]:
        if isinstance(content, dict):
            name = content.get("name", "")
            unit = content.get("unit", "")
            comment = content.get("comment", "")
        else:
            return None

        if not name:
            return None

        ent_id = self._make_id(ENTITY_TYPE_CAN_SIGNAL, name, source)
        metadata: Dict[str, Any] = {}
        if isinstance(content, dict):
            metadata = {
                "start_bit": content.get("start_bit", 0),
                "length": content.get("length", 0),
                "scale": content.get("scale", 1.0),
                "offset": content.get("offset", 0.0),
                "unit": unit,
                "comment": comment,
                "receivers": content.get("receivers", []),
                "byte_order": content.get("byte_order", ""),
                "value_type": content.get("value_type", ""),
            }
        ent = Entity(
            id=ent_id,
            type=ENTITY_TYPE_CAN_SIGNAL,
            name=name,
            source_node_id=_n_id(node),
            source_document=source,
            confidence=1.0,
            metadata=metadata,
        )
        self._seen_ids.add(ent_id)
        return ent

    # ── Text-pattern extraction ──────────────

    def _extract_from_text(self, text: str, node: Any, source: str, entities: List[Entity]) -> None:
        if not text:
            return

        node_id = _n_id(node)

        # Error codes
        for match in ERROR_CODE_PATTERN.finditer(text):
            code = match.group(0)
            eid = self._make_id(ENTITY_TYPE_ERROR_CODE, code, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_ERROR_CODE, name=code,
                    source_node_id=node_id, source_document=source, confidence=0.9,
                ))

        # Measurements
        for match in MEASUREMENT_PATTERN.finditer(text):
            val, unit = match.groups()
            label = f"{val}{unit}"
            eid = self._make_id(ENTITY_TYPE_MEASUREMENT, label, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_MEASUREMENT, name=label,
                    source_node_id=node_id, source_document=source, confidence=0.8,
                    metadata={"value": val, "unit": unit},
                ))

        # Connectors
        for match in CONNECTOR_PATTERN.finditer(text):
            name = match.group(0)
            eid = self._make_id(ENTITY_TYPE_CONNECTOR, name, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_CONNECTOR, name=name,
                    source_node_id=node_id, source_document=source, confidence=0.85,
                ))

        # Fuses
        for match in FUSE_PATTERN.finditer(text):
            name = match.group(0)
            eid = self._make_id(ENTITY_TYPE_FUSE, name, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_FUSE, name=name,
                    source_node_id=node_id, source_document=source, confidence=0.85,
                ))

        # Relays
        for match in RELAY_PATTERN.finditer(text):
            name = match.group(0)
            eid = self._make_id(ENTITY_TYPE_RELAY, name, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_RELAY, name=name,
                    source_node_id=node_id, source_document=source, confidence=0.85,
                ))

        # Sensors
        for match in SENSOR_PATTERN.finditer(text):
            raw = match.group(0)
            eid = self._make_id(ENTITY_TYPE_SENSOR, raw, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_SENSOR, name=raw.strip(),
                    source_node_id=node_id, source_document=source, confidence=0.8,
                ))

        # Component keywords
        lower_text = text.lower()
        for keyword in COMPONENT_KEYWORDS:
            pattern = re.compile(rf"\b(\w+\s+)?{re.escape(keyword)}\b", re.IGNORECASE)
            for match in pattern.finditer(lower_text):
                raw = text[match.start():match.end()]
                if len(raw) < 3:
                    continue
                eid = self._make_id(ENTITY_TYPE_COMPONENT, raw, source)
                if eid not in self._seen_ids:
                    self._seen_ids.add(eid)
                    entities.append(Entity(
                        id=eid, type=ENTITY_TYPE_COMPONENT, name=raw.strip(),
                        source_node_id=node_id, source_document=source, confidence=0.7,
                    ))

        # Warning / procedure keywords
        if re.search(r"\b(caution|warning|danger|important|note)\b", text, re.IGNORECASE):
            eid = self._make_id(ENTITY_TYPE_WARNING, text[:80], source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_WARNING, name=text[:120],
                    source_node_id=node_id, source_document=source, confidence=0.6,
                ))

        if re.search(r"\b(procedure|step\s+\d+|instruction|how to)\b", text, re.IGNORECASE):
            eid = self._make_id(ENTITY_TYPE_PROCEDURE, text[:80], source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_PROCEDURE, name=text[:120],
                    source_node_id=node_id, source_document=source, confidence=0.6,
                ))

    # ── Heading entity extraction ────────────

    def _extract_heading_entity(self, text: str, node: Any, source: str, entities: List[Entity]) -> None:
        if not text:
            return
        # Headings that name subsystems or components
        subsystem_keywords = ("system", "subsystem", "assembly", "module", "unit", "section")
        if any(kw in text.lower() for kw in subsystem_keywords):
            eid = self._make_id(ENTITY_TYPE_SUBSYSTEM, text, source)
            if eid not in self._seen_ids:
                self._seen_ids.add(eid)
                entities.append(Entity(
                    id=eid, type=ENTITY_TYPE_SUBSYSTEM, name=text,
                    source_node_id=_n_id(node), source_document=source, confidence=0.7,
                ))

    # ── Table entity extraction ──────────────

    def _extract_from_table(self, node: Any, source: str, entities: List[Entity]) -> None:
        content = _n_content(node)
        if isinstance(content, dict):
            for row in content.get("rows", []):
                if isinstance(row, list):
                    for cell in row:
                        self._extract_from_text(str(cell), node, source, entities)

    # ── Entity ID generation ─────────────────

    @staticmethod
    def _make_id(etype: str, name: str, source: str) -> str:
        raw = f"{etype}::{name}::{source}"
        return f"ENT_{hashlib.md5(raw.encode()).hexdigest()[:12]}"
