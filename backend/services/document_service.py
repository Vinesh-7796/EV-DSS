"""DocumentService — adapter for document retrieval and management."""

from typing import Any, Dict, List, Optional


class DocumentService:
    """Provides document listing and retrieval from the knowledge store.

    Never implements document processing logic — delegates to the
    existing ingestion / processing modules in the AI Core.
    """

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def list_documents(
        self,
        doc_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return []

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return None


_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
