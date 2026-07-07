"""Image document processor.

Extracts image metadata (dimensions, format, resolution) using Pillow
and performs OCR text detection using Tesseract (pytesseract).
Produces a standardised Document with OCR text results and image metadata.
"""

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
    Edge,
    IDGenerator,
    ProcessingInfo,
    Reference,
    RelationshipGraph,
    Section,
    Element,
    Chunk,
    ImageReference,
    OCRText,
    BoundingBox,
    NODE_TYPE_IMAGE,
    NODE_TYPE_OCR_TEXT,
    NODE_TYPE_PARAGRAPH,
    REF_TYPE_IMAGE,
)
from processing.utils.io import save_processed_document


class ImageProcessor(BaseParser):
    """Extracts metadata and OCR text from raster image files."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]

    @property
    def parser_name(self) -> str:
        return "ImageProcessor"

    def parse(self, ingestion_doc: IngestionDocument) -> ProcessingResult:
        logger.info("ImageProcessor processing: {}", ingestion_doc.filename)
        start = time.time()

        path = ingestion_doc.path

        # ── Extract image metadata (Pillow) ──
        width, height, img_format, mode = self._extract_metadata(path)

        # ── Run OCR (pytesseract, best-effort) ──
        ocr_results: List[OCRText] = []
        ocr_full_text = ""
        try:
            ocr_full_text, ocr_results = self._run_ocr(path)
        except Exception as exc:
            logger.warning("OCR failed for {}: {}", ingestion_doc.filename, exc)
            ocr_full_text = ""

        # ── Build output ──
        meta = DocumentMetadata(
            filename=ingestion_doc.filename,
            file_size=ingestion_doc.size,
            checksum=ingestion_doc.checksum,
            image_width=width,
            image_height=height,
            image_format=img_format or "",
            processed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            processing_time_s=time.time() - start,
        )

        img_ref = ImageReference(
            id="img_1",
            path=str(path.resolve()),
            width=width,
            height=height,
            format=img_format or "",
        )

        sections = [
            Section(
                id="img_metadata",
                title="Image Metadata",
                level=1,
                elements=[
                    Element(type="paragraph", content=f"Format: {img_format}"),
                    Element(type="paragraph", content=f"Dimensions: {width} x {height} px"),
                    Element(type="paragraph", content=f"Mode: {mode}"),
                ],
            ),
        ]

        if ocr_results:
            ocr_section = Section(
                id="ocr_text",
                title="OCR Detected Text",
                level=1,
                elements=[
                    Element(
                        type="paragraph",
                        content=ocr_text.text,
                        metadata={"confidence": ocr_text.confidence,
                                   "bbox": {"x": ocr_text.bbox.x, "y": ocr_text.bbox.y,
                                             "w": ocr_text.bbox.width, "h": ocr_text.bbox.height}}
                        if ocr_text.bbox else {"confidence": ocr_text.confidence},
                    )
                    for ocr_text in ocr_results
                ],
            )
            sections.append(ocr_section)

        chunks = [
            Chunk(
                id="chunk_img_meta",
                text=f"Image: {ingestion_doc.filename} ({width}x{height}, {img_format})",
                section_id="img_metadata",
                section_title="Image Metadata",
                source_file=ingestion_doc.filename,
            ),
        ]
        if ocr_full_text.strip():
            chunks.append(Chunk(
                id="chunk_ocr",
                text=ocr_full_text,
                section_id="ocr_text",
                section_title="OCR Detected Text",
                source_file=ingestion_doc.filename,
            ))

        ext = Path(ingestion_doc.filename).suffix.lstrip(".").lower() or "image"
        output = Document(
            source=ingestion_doc.filename,
            type=ext,
            metadata=meta,
            sections=sections,
            images=[img_ref],
            chunks=chunks,
            raw_text=ocr_full_text,
        )

        # ── Build CDS ──
        content_nodes, graph = self._build_cds(
            ingestion_doc.filename, width, height, img_format, mode, ocr_results, ocr_full_text, path
        )
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
        logger.info("ImageProcessor done: {}x{} {} (OCR: {} chars)",
                     width, height, img_format, len(ocr_full_text))
        return ProcessingResult(documents=[ingestion_doc], parser_name=self.parser_name,
                                duration_s=time.time() - start)

    # ────────────────────────────────────────────
    #  CDS Builder
    # ────────────────────────────────────────────

    @staticmethod
    def _build_cds(
        filename: str,
        width: int,
        height: int,
        img_format: str,
        mode: str,
        ocr_results: List[OCRText],
        ocr_full_text: str,
        path: Path,
    ) -> Tuple[List[ContentNode], RelationshipGraph]:
        """Build CDS ContentNode hierarchy from image metadata and OCR results."""
        id_gen = IDGenerator(doc_number=1)
        all_nodes: Dict[str, ContentNode] = {}
        edges: List[Edge] = []
        root_nodes: List[ContentNode] = []

        # Image metadata node
        img_node_id = id_gen.node_id(None, "IMG")
        img_node = ContentNode(
            id=img_node_id,
            type=NODE_TYPE_IMAGE,
            content={
                "filename": filename,
                "width": width,
                "height": height,
                "format": img_format,
                "mode": mode,
            },
            reference=Reference(
                type=REF_TYPE_IMAGE,
                location={"image_region": "full", "path": str(path.resolve())},
            ),
        )
        all_nodes[img_node_id] = img_node
        edges.append(Edge(source=img_node_id, target=id_gen.doc_id,
                          relationship_type="child_of"))
        root_nodes.append(img_node)

        # OCR text nodes
        for idx, ocr in enumerate(ocr_results):
            ocr_node_id = id_gen.node_id(img_node_id, "OCR")
            bbox_dict: Dict[str, int] = {}
            if ocr.bbox:
                bbox_dict = {"x": ocr.bbox.x, "y": ocr.bbox.y, "w": ocr.bbox.width, "h": ocr.bbox.height}
            ocr_node = ContentNode(
                id=ocr_node_id,
                type=NODE_TYPE_OCR_TEXT,
                content=ocr.text,
                reference=Reference(
                    type=REF_TYPE_IMAGE,
                    location={
                        "image_region": f"ocr_{idx}",
                        "bounding_box": bbox_dict,
                    },
                ),
                parent_id=img_node_id,
                metadata={"confidence": ocr.confidence},
            )
            all_nodes[ocr_node_id] = ocr_node
            edges.append(Edge(source=ocr_node_id, target=img_node_id,
                              relationship_type="child_of"))
            img_node.children.append(ocr_node)

        return root_nodes, RelationshipGraph(nodes=all_nodes, edges=edges)

    # ────────────────────────────────────────────
    #  Helpers
    # ────────────────────────────────────────────

    @staticmethod
    def _extract_metadata(path: Path) -> tuple:
        """Extract image properties using Pillow."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                return img.width, img.height, img.format, img.mode
        except ImportError:
            logger.warning("Pillow not installed, cannot read image metadata")
            return 0, 0, "", ""
        except Exception as exc:
            logger.warning("Cannot read image metadata for {}: {}", path.name, exc)
            return 0, 0, "", ""

    @staticmethod
    def _run_ocr(path: Path) -> tuple:
        """Run Tesseract OCR on the image.

        Returns (full_text, list_of_OCRText).
        """
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            logger.warning("pytesseract not installed; OCR unavailable")
            return "", []

        try:
            img = Image.open(path)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            full_text = pytesseract.image_to_string(img).strip()
            results: list = []
            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                conf = int(data["conf"][i]) if data["conf"][i] != "-1" else 0
                if not text or conf < 10:
                    continue
                ocr = OCRText(
                    text=text,
                    confidence=conf / 100.0,
                    bbox=BoundingBox(
                        x=data["left"][i],
                        y=data["top"][i],
                        width=data["width"][i],
                        height=data["height"][i],
                    ),
                )
                results.append(ocr)
            img.close()
            return full_text, results
        except Exception as exc:
            logger.warning("OCR extraction error for {}: {}", path.name, exc)
            return "", []
