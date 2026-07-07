"""PDF document processor.

Extracts text, headings, tables, and image references from PDF files
using PyMuPDF (fitz). Produces a standardised Document with section
hierarchy, raw text, intelligent chunking, and Canonical Document Schema.
"""

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document as IngestionDocument, ProcessingResult, ProcessingStatus
from processing.models.models import (
    ContentNode,
    Document,
    DocumentMetadata,
    Edge,
    IDGenerator,
    ImageReference,
    ProcessingInfo,
    Reference,
    RelationshipGraph,
    Section,
    Element,
    Chunk,
    Table,
    BoundingBox,
    NODE_TYPE_HEADING,
    NODE_TYPE_PARAGRAPH,
    NODE_TYPE_TABLE,
    NODE_TYPE_TABLE_ROW,
    NODE_TYPE_TABLE_CELL,
    NODE_TYPE_IMAGE,
    REF_TYPE_PDF,
)
from processing.utils.io import save_processed_document


class PDFProcessor(BaseParser):
    """Extracts structured content from PDF engineering documents."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    @property
    def parser_name(self) -> str:
        return "PDFProcessor"

    def parse(self, ingestion_doc: IngestionDocument) -> ProcessingResult:
        """Full pipeline: read → extract → structure → chunk → save."""
        logger.info("PDFProcessor processing: {}", ingestion_doc.filename)
        start = time.time()

        try:
            import fitz
        except ImportError:
            ingestion_doc.add_error("PyMuPDF (fitz) not installed")
            ingestion_doc.mark(ProcessingStatus.FAILED)
            return ProcessingResult(documents=[ingestion_doc], parser_name=self.parser_name)

        path = ingestion_doc.path
        try:
            pdf = fitz.open(path)
        except Exception as exc:
            ingestion_doc.add_error(f"Cannot open PDF: {exc}")
            ingestion_doc.mark(ProcessingStatus.FAILED)
            return ProcessingResult(documents=[ingestion_doc], parser_name=self.parser_name)

        # ── Extract pages ──
        raw_text_parts: List[str] = []
        sections: List[Section] = []
        tables: List[Table] = []
        images: List[ImageReference] = []
        heading_stack: List[Section] = []
        table_counter = 0
        image_counter = 0

        # Collect raw blocks for CDS building
        raw_blocks: List[Dict[str, Any]] = []

        for page_num, page in enumerate(pdf, start=1):
            page_text = page.get_text()
            raw_text_parts.append(page_text)

            # ── Detect headings ──
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                block_info: Dict[str, Any] = {
                    "page": page_num,
                    "block": block,
                    "type": block["type"],
                    "elements": [],
                }
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if not text:
                                continue
                            font_size = span["size"]
                            is_bold = "bold" in span["font"].lower()
                            # Heuristic: large or bold text at line start = heading
                            if (font_size >= 11 and is_bold) or font_size >= 14:
                                level = self._heading_level(font_size)
                                sec = Section(
                                    id=str(uuid.uuid4())[:8],
                                    title=text,
                                    level=level,
                                    page_number=page_num,
                                )
                                # Attach to parent
                                while heading_stack and heading_stack[-1].level >= level:
                                    heading_stack.pop()
                                if heading_stack:
                                    sec.parent_id = heading_stack[-1].id
                                    heading_stack[-1].subsections.append(sec)
                                else:
                                    sections.append(sec)
                                heading_stack.append(sec)
                                block_info["elements"].append(("heading", text, font_size, level))
                            else:
                                # Regular paragraph
                                elem = Element(
                                    type="paragraph",
                                    content=text,
                                    page_number=page_num,
                                )
                                if heading_stack:
                                    heading_stack[-1].elements.append(elem)
                                block_info["elements"].append(("paragraph", text, font_size, 0))

                elif block["type"] == 1:  # image block
                    image_counter += 1
                    img_ref = ImageReference(
                        id=f"img_{image_counter}",
                        path=f"page{page_num}_img{image_counter}",
                        page_number=page_num,
                        width=block.get("width", 0),
                        height=block.get("height", 0),
                        bbox=BoundingBox(
                            x=int(block["bbox"][0]),
                            y=int(block["bbox"][1]),
                            width=int(block["bbox"][2] - block["bbox"][0]),
                            height=int(block["bbox"][3] - block["bbox"][1]),
                        ),
                    )
                    images.append(img_ref)
                    block_info["elements"].append(("image", img_ref))

                raw_blocks.append(block_info)

            # ── Detect tables (via PyMuPDF table detection) ──
            try:
                tab_data = page.find_tables()
                for tab in tab_data:
                    table_counter += 1
                    headers = [str(h).strip() for h in tab.header.names] if tab.header else []
                    rows_data = []
                    for row in tab.extract():
                        rows_data.append([str(c).strip() if c else "" for c in row])
                    tbl = Table(
                        id=f"tbl_{table_counter}",
                        caption=f"Table from page {page_num}",
                        headers=headers,
                        rows=rows_data,
                        page_number=page_num,
                        col_count=len(headers) if headers else (len(rows_data[0]) if rows_data else 0),
                        row_count=len(rows_data),
                    )
                    tables.append(tbl)
            except Exception:
                pass  # Table detection is best-effort

        pdf.close()
        raw_text = "\n".join(raw_text_parts)

        # ── Build chunks ──
        chunks = self._chunk_document(sections, raw_text, ingestion_doc.filename)

        # ── Assemble output document ──
        doc_meta = DocumentMetadata(
            filename=ingestion_doc.filename,
            file_size=ingestion_doc.size,
            checksum=ingestion_doc.checksum,
            page_count=len(raw_text_parts),
            processed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            processing_time_s=time.time() - start,
        )

        output = Document(
            source=ingestion_doc.filename,
            type="pdf",
            metadata=doc_meta,
            sections=sections,
            tables=tables,
            images=images,
            chunks=chunks,
            raw_text=raw_text,
        )

        # ── Build CDS ──
        content_nodes, graph = self._build_cds(sections, tables, images, raw_blocks)
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
        logger.info("PDFProcessor done: {} pages, {} sections, {} tables, {} chunks",
                     doc_meta.page_count, len(sections), len(tables), len(chunks))
        return ProcessingResult(documents=[ingestion_doc], parser_name=self.parser_name,
                                duration_s=time.time() - start)

    # ────────────────────────────────────────────
    #  CDS Builder
    # ────────────────────────────────────────────

    @staticmethod
    def _build_cds(
        sections: List[Section],
        tables: List[Table],
        images: List[ImageReference],
        raw_blocks: List[Dict[str, Any]],
    ) -> Tuple[List[ContentNode], RelationshipGraph]:
        """Build CDS ContentNode hierarchy and RelationshipGraph from extracted data."""
        id_gen = IDGenerator(doc_number=1)
        all_nodes: Dict[str, ContentNode] = {}
        edges: List[Edge] = []
        root_nodes: List[ContentNode] = []

        # Build section hierarchy
        def build_section_nodes(sec_list: List[Section], parent_id: Optional[str]) -> List[ContentNode]:
            nodes: List[ContentNode] = []
            for sec in sec_list:
                sec_node_id = id_gen.section_id(parent_id)
                sec_node = ContentNode(
                    id=sec_node_id,
                    type=NODE_TYPE_HEADING,
                    content=sec.title,
                    reference=Reference(
                        type=REF_TYPE_PDF,
                        location={"page": sec.page_number, "section": sec.title, "level": sec.level},
                    ),
                    parent_id=parent_id,
                )
                all_nodes[sec_node_id] = sec_node
                edges.append(Edge(source=sec_node_id, target=parent_id or id_gen.doc_id,
                                  relationship_type="child_of"))

                # Paragraph / element nodes
                for elem in sec.elements:
                    elem_node_id = id_gen.node_id(sec_node_id)
                    elem_type = NODE_TYPE_PARAGRAPH
                    if elem.type in ("heading", "list", "code", "image"):
                        elem_type = elem.type
                    elem_node = ContentNode(
                        id=elem_node_id,
                        type=elem_type,
                        content=elem.content,
                        reference=Reference(
                            type=REF_TYPE_PDF,
                            location={"page": elem.page_number, "section": sec.title},
                        ),
                        parent_id=sec_node_id,
                    )
                    all_nodes[elem_node_id] = elem_node
                    edges.append(Edge(source=elem_node_id, target=sec_node_id,
                                      relationship_type="child_of"))
                    sec_node.children.append(elem_node)

                # Recurse subsections
                child_nodes = build_section_nodes(sec.subsections, sec_node_id)
                for cn in child_nodes:
                    sec_node.children.append(cn)

                nodes.append(sec_node)
            return nodes

        root_nodes = build_section_nodes(sections, None)

        # Table nodes
        for tbl in tables:
            tbl_node_id = id_gen.table_id(None)
            tbl_node = ContentNode(
                id=tbl_node_id,
                type=NODE_TYPE_TABLE,
                content={"headers": tbl.headers, "caption": tbl.caption},
                reference=Reference(
                    type=REF_TYPE_PDF,
                    location={"page": tbl.page_number, "table": tbl.id},
                ),
            )
            all_nodes[tbl_node_id] = tbl_node
            edges.append(Edge(source=tbl_node_id, target=id_gen.doc_id,
                              relationship_type="child_of"))

            for row_idx, row_data in enumerate(tbl.rows):
                row_node_id = id_gen.row_id(tbl_node_id)
                row_node = ContentNode(
                    id=row_node_id,
                    type=NODE_TYPE_TABLE_ROW,
                    content=row_data,
                    reference=Reference(
                        type=REF_TYPE_PDF,
                        location={"page": tbl.page_number, "table": tbl.id, "row": row_idx},
                    ),
                    parent_id=tbl_node_id,
                )
                all_nodes[row_node_id] = row_node
                edges.append(Edge(source=row_node_id, target=tbl_node_id,
                                  relationship_type="child_of"))
                tbl_node.children.append(row_node)

                for col_idx, cell_val in enumerate(row_data):
                    cell_node_id = id_gen.cell_id(row_node_id)
                    cell_node = ContentNode(
                        id=cell_node_id,
                        type=NODE_TYPE_TABLE_CELL,
                        content=cell_val,
                        parent_id=row_node_id,
                    )
                    all_nodes[cell_node_id] = cell_node
                    row_node.children.append(cell_node)

            root_nodes.append(tbl_node)

        # Image nodes
        for idx, img in enumerate(images):
            img_node_id = id_gen.node_id(None, "IMG")
            bbox_dict: Dict[str, int] = {}
            if img.bbox:
                bbox_dict = {"x": img.bbox.x, "y": img.bbox.y, "w": img.bbox.width, "h": img.bbox.height}
            img_node = ContentNode(
                id=img_node_id,
                type=NODE_TYPE_IMAGE,
                content={"path": img.path, "width": img.width, "height": img.height, "format": img.format},
                reference=Reference(
                    type=REF_TYPE_PDF,
                    location={"page": img.page_number, "image_region": img.id, "bounding_box": bbox_dict},
                ),
            )
            all_nodes[img_node_id] = img_node
            edges.append(Edge(source=img_node_id, target=id_gen.doc_id,
                              relationship_type="child_of"))
            root_nodes.append(img_node)

        return root_nodes, RelationshipGraph(nodes=all_nodes, edges=edges)

    # ────────────────────────────────────────────
    #  Helpers
    # ────────────────────────────────────────────

    @staticmethod
    def _heading_level(font_size: float) -> int:
        """Map font size to heading level (1=h1, 2=h2, …)."""
        if font_size >= 18:
            return 1
        if font_size >= 14:
            return 2
        if font_size >= 12:
            return 3
        return 4

    @staticmethod
    def _chunk_document(
        sections: List[Section],
        raw_text: str,
        source_file: str,
    ) -> List[Chunk]:
        """Split the document into atomic retrieval chunks.

        Each chunk corresponds to a section and carries its
        chapter, page number, and source reference.
        """
        chunks: List[Chunk] = []
        chunk_counter = 0

        def walk(section_list: List[Section], chapter_path: str = "") -> None:
            nonlocal chunk_counter
            for sec in section_list:
                chunk_counter += 1
                # Collect text from this section's elements
                texts = [e.content for e in sec.elements if e.type == "paragraph"]
                section_text = "\n".join(texts) if texts else (sec.title or "")
                chunk = Chunk(
                    id=f"chunk_{chunk_counter}",
                    text=section_text,
                    section_id=sec.id,
                    section_title=sec.title,
                    chapter=chapter_path or sec.title,
                    page_number=sec.page_number,
                    source_file=source_file,
                    metadata={
                        "level": sec.level,
                        "parent_id": sec.parent_id or "",
                    },
                )
                chunks.append(chunk)
                # Recurse into subsections
                child_path = f"{chapter_path} > {sec.title}" if chapter_path else sec.title
                walk(sec.subsections, child_path)

        walk(sections)
        if not chunks and raw_text.strip():
            # Fallback for documents with no detected headings
            chunks.append(Chunk(
                id="chunk_1",
                text=raw_text[:2000],
                source_file=source_file,
                page_number=1,
            ))
        return chunks
