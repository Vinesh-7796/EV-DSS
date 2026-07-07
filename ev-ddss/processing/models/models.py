"""Canonical data models for the EV-DDSS document processing engine.

Every processor (PDF, Excel, DBC, Image) produces instances of these
classes, ensuring a uniform downstream interface regardless of source
document type.

Includes the Canonical Document Schema (CDS): ContentNode, Reference,
RelationshipGraph, and supporting types for a unified document representation.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
#  CDS Constants
# ──────────────────────────────────────────────

# Supported ContentNode types
NODE_TYPE_HEADING = "heading"
NODE_TYPE_PARAGRAPH = "paragraph"
NODE_TYPE_TABLE = "table"
NODE_TYPE_TABLE_ROW = "table_row"
NODE_TYPE_TABLE_CELL = "table_cell"
NODE_TYPE_WORKSHEET = "worksheet"
NODE_TYPE_SPREADSHEET_ROW = "spreadsheet_row"
NODE_TYPE_SPREADSHEET_CELL = "spreadsheet_cell"
NODE_TYPE_DBC_MESSAGE = "dbc_message"
NODE_TYPE_DBC_SIGNAL = "dbc_signal"
NODE_TYPE_IMAGE = "image"
NODE_TYPE_FIGURE = "figure"
NODE_TYPE_CAPTION = "caption"
NODE_TYPE_OCR_TEXT = "ocr_text"
NODE_TYPE_PROCEDURE = "procedure"
NODE_TYPE_WARNING = "warning"
NODE_TYPE_NOTE = "note"
NODE_TYPE_LIST = "list"
NODE_TYPE_FORMULA = "formula"
NODE_TYPE_DIAGRAM = "diagram"
NODE_TYPE_CODE = "code"
NODE_TYPE_DESCRIPTION = "description"

# Supported reference types
REF_TYPE_PDF = "pdf"
REF_TYPE_EXCEL = "excel"
REF_TYPE_DBC = "dbc"
REF_TYPE_IMAGE = "image"
REF_TYPE_KNOWLEDGE = "knowledge"

# Enrichment entity node types
NODE_TYPE_ENRICHED_ENTITY = "enriched_entity"
NODE_TYPE_ENRICHED_ERROR_CODE = "enriched_error_code"
NODE_TYPE_ENRICHED_ECU = "enriched_ecu"
NODE_TYPE_ENRICHED_CAN_MESSAGE = "enriched_can_message"
NODE_TYPE_ENRICHED_CAN_SIGNAL = "enriched_can_signal"
NODE_TYPE_ENRICHED_COMPONENT = "enriched_component"
NODE_TYPE_ENRICHED_SUBSYSTEM = "enriched_subsystem"


# ──────────────────────────────────────────────
#  Reference (origin descriptor for ContentNode)
# ──────────────────────────────────────────────

@dataclass
class Reference:
    """Describes the exact origin of a ContentNode within a source document.

    The ``type`` field indicates the source document type (pdf | excel | dbc | image).
    The ``location`` dict stores type-specific provenance information:

    - PDF:      ``{"page": int, "section": str, "paragraph": int}``
    - Excel:    ``{"worksheet": str, "table": str, "row": int, "column": str, "cell": str}``
    - DBC:      ``{"message": str, "signal": str}``
    - Image:    ``{"image_region": str, "bounding_box": {"x": int, "y": int, "w": int, "h": int}}``
    """

    type: str = ""  # pdf | excel | dbc | image
    location: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  ContentNode — canonical content unit
# ──────────────────────────────────────────────

@dataclass
class ContentNode:
    """A single piece of extracted content within the Canonical Document Schema.

    Every extracted object (heading, paragraph, table, cell, image, signal, …)
    becomes a ContentNode.  Nodes form a parent-child hierarchy and carry a
    ``Reference`` that describes their exact origin.
    """

    id: str = ""
    type: str = "paragraph"  # one of NODE_TYPE_*
    content: Any = ""
    reference: Optional[Reference] = None
    parent_id: Optional[str] = None
    children: List["ContentNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  Edge (relationship between two nodes)
# ──────────────────────────────────────────────

@dataclass
class Edge:
    """A directed relationship between two ContentNodes in the graph."""

    source: str = ""       # source node ID
    target: str = ""       # target node ID
    relationship_type: str = ""  # e.g. "contains", "references", "derives_from"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  RelationshipGraph
# ──────────────────────────────────────────────

@dataclass
class RelationshipGraph:
    """A generic graph of ContentNodes and their relationships.

    Supports future GraphRAG usage.  Nodes are stored keyed by ID; edges
    connect source → target nodes.
    """

    nodes: Dict[str, ContentNode] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)


# ──────────────────────────────────────────────
#  Processing Info
# ──────────────────────────────────────────────

@dataclass
class ProcessingInfo:
    """Processing metadata about how a document was processed."""

    processor_name: str = ""
    processing_time_s: float = 0.0
    processed_at: str = ""
    schema_version: str = "2.0"


# ──────────────────────────────────────────────
#  Statistics
# ──────────────────────────────────────────────

@dataclass
class Statistics:
    """Aggregate statistics about a processed document's CDS structure."""

    total_content_nodes: int = 0
    total_relationships: int = 0
    node_type_counts: Dict[str, int] = field(default_factory=dict)
    max_depth: int = 0


# ──────────────────────────────────────────────
#  ID Generator (deterministic hierarchical IDs)
# ──────────────────────────────────────────────

class IDGenerator:
    """Produces deterministic hierarchical IDs for CDS content nodes.

    Example IDs::

        DOC001
        DOC001.SEC010
        DOC001.SEC010.NODE005
        DOC001.SEC010.TABLE002
        DOC001.SEC010.TABLE002.ROW003
        DOC003.MSG_0x181
        DOC003.MSG_0x181.SIG_MotorRPM
    """

    def __init__(self, doc_number: int = 1) -> None:
        self._doc_id: str = f"DOC{doc_number:03d}"
        self._counters: Dict[str, int] = {}

    @property
    def doc_id(self) -> str:
        return self._doc_id

    def next_id(self, parent_id: Optional[str], prefix: str = "NODE") -> str:
        key = f"{parent_id or self._doc_id}.{prefix}"
        self._counters[key] = self._counters.get(key, 0) + 1
        n = self._counters[key]
        parent = parent_id or self._doc_id
        return f"{parent}.{prefix}{n:03d}"

    def section_id(self, parent_id: Optional[str] = None) -> str:
        return self.next_id(parent_id, "SEC")

    def node_id(self, parent_id: Optional[str] = None, prefix: str = "NODE") -> str:
        return self.next_id(parent_id, prefix)

    def table_id(self, parent_id: Optional[str] = None) -> str:
        return self.next_id(parent_id, "TABLE")

    def row_id(self, parent_id: Optional[str] = None) -> str:
        return self.next_id(parent_id, "ROW")

    def msg_id(self, can_id: int) -> str:
        return f"{self._doc_id}.MSG_0x{can_id:X}"

    def signal_id(self, msg_id: str, name: str) -> str:
        return f"{msg_id}.SIG_{name}"

    def worksheet_id(self, parent_id: Optional[str] = None) -> str:
        return self.next_id(parent_id, "WS")

    def cell_id(self, parent_id: Optional[str] = None) -> str:
        return self.next_id(parent_id, "CELL")


# ──────────────────────────────────────────────
#  Bounding Box (shared by Image / OCR)
# ──────────────────────────────────────────────

@dataclass
class BoundingBox:
    """Pixel coordinates of a detected region within an image."""

    x: int
    y: int
    width: int
    height: int


# ──────────────────────────────────────────────
#  Table element (shared by PDF / Excel)
# ──────────────────────────────────────────────

@dataclass
class Table:
    """A structured table extracted from a document."""

    id: str = ""
    caption: str = ""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    page_number: int = 0
    source_section: str = ""
    col_count: int = 0
    row_count: int = 0


# ──────────────────────────────────────────────
#  Image reference (shared by PDF / Image)
# ──────────────────────────────────────────────

@dataclass
class ImageReference:
    """Reference to an image found inside or provided as a source document."""

    id: str = ""
    path: str = ""
    caption: str = ""
    page_number: int = 0
    width: int = 0
    height: int = 0
    format: str = ""
    bbox: Optional[BoundingBox] = None


# ──────────────────────────────────────────────
#  Generic element inside a section
# ──────────────────────────────────────────────

@dataclass
class Element:
    """A single content element within a document section."""

    type: str = "paragraph"  # paragraph | heading | table | image | list | code
    content: Any = ""
    level: int = 0
    page_number: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  Section (heading + content hierarchy)
# ──────────────────────────────────────────────

@dataclass
class Section:
    """A logical section within a document, identified by a heading."""

    id: str = ""
    title: str = ""
    level: int = 1
    page_number: int = 0
    parent_id: Optional[str] = None
    elements: List[Element] = field(default_factory=list)
    subsections: List["Section"] = field(default_factory=list)


# ──────────────────────────────────────────────
#  Chunk (atomic retrieval unit)
# ──────────────────────────────────────────────

@dataclass
class Chunk:
    """An atomic text unit suitable for embedding and retrieval."""

    id: str = ""
    text: str = ""
    section_id: str = ""
    section_title: str = ""
    chapter: str = ""
    page_number: int = 0
    source_file: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  Document metadata
# ──────────────────────────────────────────────

@dataclass
class DocumentMetadata:
    """Filesystem and processing metadata for a document."""

    filename: str = ""
    file_size: int = 0
    checksum: str = ""
    page_count: int = 0
    sheet_count: int = 0
    message_count: int = 0
    image_width: int = 0
    image_height: int = 0
    image_format: str = ""
    processed_at: str = ""
    processing_time_s: float = 0.0


# ──────────────────────────────────────────────
#  Top-level Document
# ──────────────────────────────────────────────

@dataclass
class Document:
    """Standardised representation of any processed engineering document.

    Retains the original flat fields (sections, tables, chunks, …) for
    backward compatibility.  New code should prefer the CDS fields:

    * ``content_nodes`` — root-level ContentNodes forming a hierarchy
    * ``relationship_graph`` — nodes + edges for graph traversal
    * ``processing_info`` — processor metadata
    * ``statistics`` — aggregate node/edge stats
    """

    source: str = ""
    type: str = ""  # pdf | excel | dbc | image
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    sections: List[Section] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    images: List[ImageReference] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    raw_text: str = ""

    # ── CDS fields ──
    content_nodes: List[ContentNode] = field(default_factory=list)
    relationship_graph: RelationshipGraph = field(default_factory=RelationshipGraph)
    processing_info: ProcessingInfo = field(default_factory=ProcessingInfo)
    statistics: Statistics = field(default_factory=Statistics)

    def to_dict(self) -> Dict[str, Any]:
        """Recursively convert to a JSON-serialisable dictionary."""
        return _deep_asdict(self)

    def find_node(self, node_id: str) -> Optional[ContentNode]:
        """Look up a ContentNode by its ID in the content hierarchy."""
        def _search(nodes: List[ContentNode]) -> Optional[ContentNode]:
            for n in nodes:
                if n.id == node_id:
                    return n
                found = _search(n.children)
                if found:
                    return found
            return None
        return _search(self.content_nodes)


# ──────────────────────────────────────────────
#  Excel-specific models
# ──────────────────────────────────────────────

@dataclass
class Cell:
    """A single cell within an Excel worksheet."""

    value: Any = ""
    column: str = ""
    row_index: int = 0
    column_index: int = 0
    is_merged: bool = False
    is_header: bool = False


@dataclass
class Row:
    """A single row within an Excel worksheet."""

    index: int = 0
    cells: List[Cell] = field(default_factory=list)
    is_header: bool = False


@dataclass
class Worksheet:
    """A single worksheet within an Excel workbook."""

    name: str = ""
    rows: List[Row] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    merged_cells: List[Tuple[int, int, int, int]] = field(default_factory=list)
    column_count: int = 0
    row_count: int = 0


@dataclass
class Workbook:
    """Complete Excel workbook representation."""

    filename: str = ""
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    worksheets: List[Worksheet] = field(default_factory=list)


# ──────────────────────────────────────────────
#  DBC-specific models
# ──────────────────────────────────────────────

@dataclass
class DBCSignal:
    """A single CAN signal definition from a DBC file."""

    name: str = ""
    start_bit: int = 0
    length: int = 0
    scale: float = 1.0
    offset: float = 0.0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    unit: str = ""
    receiver: List[str] = field(default_factory=list)
    comment: str = ""
    byte_order: str = "little_endian"  # little_endian | big_endian
    value_type: str = "unsigned"  # unsigned | signed


@dataclass
class DBCMessage:
    """A single CAN message (frame) definition from a DBC file."""

    id: int = 0
    name: str = ""
    dlc: int = 8
    sender: str = ""
    signals: List[DBCSignal] = field(default_factory=list)
    cycle_time: Optional[float] = None
    comment: str = ""


@dataclass
class DBCNode:
    """An ECU / node definition from a DBC file."""

    name: str = ""
    comment: str = ""


# ──────────────────────────────────────────────
#  Image / OCR-specific models
# ──────────────────────────────────────────────

@dataclass
class OCRText:
    """A single text detection result from OCR."""

    text: str = ""
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None


# ──────────────────────────────────────────────
#  Serialisation helper
# ──────────────────────────────────────────────

def _deep_asdict(obj: Any) -> Any:
    """Convert a dataclass (or nested dataclass structure) to a dict.

    Handles lists, optional fields, and basic types safely.
    """
    if hasattr(obj, "_asdict"):  # support dataclasses.asdict protocol
        return obj._asdict()
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for f in obj.__dataclass_fields__:
            val = getattr(obj, f)
            if val is not None:
                result[f] = _deep_asdict(val)
            else:
                result[f] = None
        return result
    if isinstance(obj, list):
        return [_deep_asdict(v) for v in obj]
    if isinstance(obj, tuple) and hasattr(obj, "_fields"):  # namedtuple
        return {k: _deep_asdict(v) for k, v in obj._asdict().items()}
    if isinstance(obj, dict):
        return {k: _deep_asdict(v) for k, v in obj.items()}
    return obj
