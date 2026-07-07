"""DBC (CAN database) file processor.

Parses Vector CANdb DBC text files to extract messages, signals,
ECUs, and their attributes. Produces a standardised Document with
message/signal hierarchy and CAN-specific metadata.
"""

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document as IngestionDocument, ProcessingResult, ProcessingStatus
from processing.models.models import (
    ContentNode,
    Document,
    DocumentMetadata,
    DBCMessage,
    DBCSignal,
    DBCNode,
    Edge,
    IDGenerator,
    ProcessingInfo,
    Reference,
    RelationshipGraph,
    Section,
    Element,
    Chunk,
    NODE_TYPE_DBC_MESSAGE,
    NODE_TYPE_DBC_SIGNAL,
    NODE_TYPE_PARAGRAPH,
    REF_TYPE_DBC,
)
from processing.utils.io import save_processed_document


class DBCProcessor(BaseParser):
    """Parses CAN database (.dbc) files into structured message/signal models."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".dbc"]

    @property
    def parser_name(self) -> str:
        return "DBCProcessor"

    def parse(self, ingestion_doc: IngestionDocument) -> ProcessingResult:
        logger.info("DBCProcessor processing: {}", ingestion_doc.filename)
        start = time.time()

        path = ingestion_doc.path
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            ingestion_doc.add_error(f"Cannot read DBC file: {exc}")
            ingestion_doc.mark(ProcessingStatus.FAILED)
            return ProcessingResult(documents=[ingestion_doc], parser_name=self.parser_name)

        # ── Parse DBC sections ──
        nodes: List[DBCNode] = self._parse_nodes(text)
        messages: List[DBCMessage] = self._parse_messages(text)
        self._parse_message_attributes(text, messages)
        self._parse_comments(text, messages, nodes)

        # ── Build output ──
        meta = DocumentMetadata(
            filename=ingestion_doc.filename,
            file_size=ingestion_doc.size,
            checksum=ingestion_doc.checksum,
            message_count=len(messages),
            processed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            processing_time_s=time.time() - start,
        )

        sections = [
            Section(
                id=f"msg_{m.name}",
                title=f"Message 0x{m.id:X} ({m.name})",
                level=2,
                elements=[
                    Element(type="paragraph", content=f"DLC: {m.dlc} | Sender: {m.sender} | Cycle: {m.cycle_time or 'N/A'} ms"),
                    *(Element(type="paragraph", content=f"  Signal {s.name}: bit {s.start_bit}, len {s.length}, scale {s.scale}, offset {s.offset} {s.unit}")
                      for s in m.signals),
                ],
            )
            for m in messages
        ]

        raw_lines = [f"// DBC: {m.name} (0x{m.id:X}) DLC={m.dlc}" for m in messages]
        for m in messages:
            for s in m.signals:
                raw_lines.append(f"  {s.name}: bit={s.start_bit} len={s.length} scale={s.scale} off={s.offset} [{s.unit}]")
        raw_text = "\n".join(raw_lines)

        chunks = [
            Chunk(
                id=f"chunk_msg_{m.name}",
                text=f"Message 0x{m.id:X} ({m.name}): {len(m.signals)} signals. " +
                     " ".join(f"{s.name} (bit {s.start_bit}, {s.length} bits, {s.scale}{s.unit})" for s in m.signals),
                section_id=f"msg_{m.name}",
                section_title=m.name,
                source_file=ingestion_doc.filename,
                metadata={"message_id": m.id, "dlc": m.dlc, "sender": m.sender},
            )
            for m in messages
        ]

        output = Document(
            source=ingestion_doc.filename,
            type="dbc",
            metadata=meta,
            sections=sections,
            chunks=chunks,
            raw_text=raw_text,
        )

        # ── Build CDS ──
        content_nodes, graph = self._build_cds(messages)
        output.content_nodes = content_nodes
        output.relationship_graph = graph
        output.processing_info = ProcessingInfo(
            processor_name=self.parser_name,
            processing_time_s=time.time() - start,
            processed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            schema_version="2.0",
        )

        save_processed_document(output)
        ingestion_doc.mark(ProcessingStatus.COMPLETED)
        logger.info("DBCProcessor done: {} messages, {} signals total",
                     len(messages), sum(len(m.signals) for m in messages))
        return ProcessingResult(documents=[ingestion_doc], parser_name=self.parser_name,
                                duration_s=time.time() - start)

    # ────────────────────────────────────────────
    #  CDS Builder
    # ────────────────────────────────────────────

    @staticmethod
    def _build_cds(
        messages: List[DBCMessage],
    ) -> Tuple[List[ContentNode], RelationshipGraph]:
        """Build CDS ContentNode hierarchy from DBC messages."""
        id_gen = IDGenerator(doc_number=1)
        all_nodes: Dict[str, ContentNode] = {}
        edges: List[Edge] = []
        root_nodes: List[ContentNode] = []

        for msg in messages:
            msg_node_id = id_gen.msg_id(msg.id)
            msg_node = ContentNode(
                id=msg_node_id,
                type=NODE_TYPE_DBC_MESSAGE,
                content={
                    "name": msg.name,
                    "id": msg.id,
                    "dlc": msg.dlc,
                    "sender": msg.sender,
                    "cycle_time": msg.cycle_time,
                    "comment": msg.comment,
                },
                reference=Reference(
                    type=REF_TYPE_DBC,
                    location={"message": msg.name},
                ),
            )
            all_nodes[msg_node_id] = msg_node
            edges.append(Edge(source=msg_node_id, target=id_gen.doc_id,
                              relationship_type="child_of"))

            for sig in msg.signals:
                sig_node_id = id_gen.signal_id(msg_node_id, sig.name)
                sig_node = ContentNode(
                    id=sig_node_id,
                    type=NODE_TYPE_DBC_SIGNAL,
                    content={
                        "name": sig.name,
                        "start_bit": sig.start_bit,
                        "length": sig.length,
                        "scale": sig.scale,
                        "offset": sig.offset,
                        "min_val": sig.min_val,
                        "max_val": sig.max_val,
                        "unit": sig.unit,
                        "comment": sig.comment,
                        "byte_order": sig.byte_order,
                        "value_type": sig.value_type,
                        "receivers": sig.receiver,
                    },
                    reference=Reference(
                        type=REF_TYPE_DBC,
                        location={"message": msg.name, "signal": sig.name},
                    ),
                    parent_id=msg_node_id,
                    metadata={
                        "start_bit": sig.start_bit,
                        "length": sig.length,
                    },
                )
                all_nodes[sig_node_id] = sig_node
                edges.append(Edge(source=sig_node_id, target=msg_node_id,
                                  relationship_type="child_of"))
                msg_node.children.append(sig_node)

            root_nodes.append(msg_node)

        return root_nodes, RelationshipGraph(nodes=all_nodes, edges=edges)

    # ────────────────────────────────────────────
    #  Parsing helpers
    # ────────────────────────────────────────────

    @staticmethod
    def _parse_nodes(text: str) -> List[DBCNode]:
        """Extract BU_: node definitions."""
        nodes: List[DBCNode] = []
        for m in re.finditer(r"BU_: (.+)", text):
            for name in m.group(1).split():
                nodes.append(DBCNode(name=name.strip()))
        return nodes

    @staticmethod
    def _parse_messages(text: str) -> List[DBCMessage]:
        """Extract BO_: message definitions."""
        messages: List[DBCMessage] = []
        msg_pattern = re.compile(
            r"BO_ (\d+) (\w+): (\d+) (\w+)",
            re.MULTILINE,
        )
        # Collect signals per message
        msg_blocks = re.split(r"\n\s*\n", text)
        current_msg_id: Optional[int] = None

        for block in msg_blocks:
            msg_match = msg_pattern.search(block)
            if msg_match:
                current_msg_id = int(msg_match.group(1))
                msg = DBCMessage(
                    id=current_msg_id,
                    name=msg_match.group(2),
                    dlc=int(msg_match.group(3)),
                    sender=msg_match.group(4),
                )
                # Parse SG_: lines that follow (multiplexer is optional)
                for sg_match in re.finditer(
                    r"SG_ (\w+)(?:\s+\w+)? : (\d+)\|(\d+)@(\d+)([+-]) \(([\d.e+-]+),([\d.e+-]+)\) \[([\d.e+-]*)\|([\d.e+-]*)\] \"(.*?)\" (\w+(?: \w+)*)",
                    block,
                ):
                    signal = DBCSignal(
                        name=sg_match.group(1),
                        start_bit=int(sg_match.group(2)),
                        length=int(sg_match.group(3)),
                        scale=float(sg_match.group(6)),
                        offset=float(sg_match.group(7)),
                        unit=sg_match.group(10),
                        receiver=sg_match.group(11).split(),
                        byte_order="big_endian" if sg_match.group(4) == "1" else "little_endian",
                        value_type="signed" if sg_match.group(5) == "-" else "unsigned",
                    )
                    # Optional min/max
                    try:
                        signal.min_val = float(sg_match.group(8)) if sg_match.group(8) else None
                    except ValueError:
                        signal.min_val = None
                    try:
                        signal.max_val = float(sg_match.group(9)) if sg_match.group(9) else None
                    except ValueError:
                        signal.max_val = None

                    msg.signals.append(signal)
                messages.append(msg)
        return messages

    @staticmethod
    def _parse_message_attributes(text: str, messages: List[DBCMessage]) -> None:
        """Extract BA_: attribute definitions for messages."""
        msg_map = {m.id: m for m in messages}
        # Cycle time
        for m in re.finditer(r'BA_ "GenMsgCycleTime" BO_ (\d+) (\d+)', text):
            msg_id = int(m.group(1))
            if msg_id in msg_map:
                msg_map[msg_id].cycle_time = float(m.group(2))

    @staticmethod
    def _parse_comments(text: str, messages: List[DBCMessage], nodes: List[DBCNode]) -> None:
        """Extract CM_: comment definitions."""
        msg_map = {m.id: m for m in messages}
        node_map = {n.name: n for n in nodes}
        # Message comments
        for m in re.finditer(r'CM_ BO_ (\d+) "(.*?)"', text, re.DOTALL):
            msg_id = int(m.group(1))
            if msg_id in msg_map:
                msg_map[msg_id].comment = m.group(2).strip()
        # Signal comments
        for m in re.finditer(r'CM_ SG_ (\d+) (\w+) "(.*?)"', text, re.DOTALL):
            msg_id = int(m.group(1))
            sig_name = m.group(2)
            comment = m.group(3).strip()
            if msg_id in msg_map:
                for sig in msg_map[msg_id].signals:
                    if sig.name == sig_name:
                        sig.comment = comment
                        break
        # Node comments
        for m in re.finditer(r'CM_ BU_ (\w+) "(.*?)"', text, re.DOTALL):
            node_name = m.group(1)
            if node_name in node_map:
                node_map[node_name].comment = m.group(2).strip()
