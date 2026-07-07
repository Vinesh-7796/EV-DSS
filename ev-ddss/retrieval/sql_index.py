"""SQL Index — exact lookup and filtered search over the PostgreSQL
knowledge store.

Provides direct SQL queries against the normalised ContentNode and
ProcessedDocument tables for exact-match retrieval, metadata filtering,
and document-level lookups.
"""

import json
from typing import Any, Dict, List, Optional

from backend.logger import logger
from database.connection import get_database

try:
    from sqlalchemy import text as sa_text
    from sqlalchemy.orm import Session

    _HAS_SQLA = True
except ImportError:
    _HAS_SQLA = False


class SQLIndex:
    """Exact-lookup index backed by PostgreSQL.

    Queries the existing ``content_nodes`` and ``processed_documents``
    tables populated by the ``PostgreSQLKnowledgeStore``.

    All methods are safe to call when PostgreSQL is unavailable — they
    return empty results instead of throwing.
    """

    def __init__(self) -> None:
        self._db = get_database()
        self._connected_cache: Optional[bool] = None

    # ── Public query API ────────────────────────

    def lookup_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Exact lookup of a ContentNode by its ID.

        Returns the node dict (including document metadata) or None.
        """
        if not self._check():
            return None
        with self._db.get_session() as session:
            row = session.execute(
                sa_text("""
                    SELECT cn.id, cn.type, cn.content, cn.reference,
                           cn.parent_id, cn.metadata,
                           pd.source, pd.type AS doc_type, pd.filename
                    FROM content_nodes cn
                    JOIN processed_documents pd ON pd.id = cn.document_id
                    WHERE cn.id = :nid
                """),
                {"nid": node_id},
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)

    def lookup_by_type(self, node_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve content nodes of a specific type."""
        if not self._check():
            return []
        with self._db.get_session() as session:
            rows = session.execute(
                sa_text("""
                    SELECT cn.id, cn.type, cn.content, cn.reference,
                           cn.parent_id, cn.metadata,
                           pd.source, pd.type AS doc_type, pd.filename
                    FROM content_nodes cn
                    JOIN processed_documents pd ON pd.id = cn.document_id
                    WHERE cn.type = :ntype
                    LIMIT :lim
                """),
                {"ntype": node_type, "lim": limit},
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def search_by_text(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Full-text search on ContentNode content (JSONB text fields)."""
        if not self._check():
            return []
        pattern = f"%{query}%"
        with self._db.get_session() as session:
            rows = session.execute(
                sa_text("""
                    SELECT cn.id, cn.type, cn.content, cn.reference,
                           cn.parent_id, cn.metadata,
                           pd.source, pd.type AS doc_type, pd.filename
                    FROM content_nodes cn
                    JOIN processed_documents pd ON pd.id = cn.document_id
                    WHERE cn.content::text ILIKE :pattern
                    LIMIT :lim
                """),
                {"pattern": pattern, "lim": limit},
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def filter_by_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filter content nodes by metadata JSONB fields.

        Example filters:
            ``{"node_type": "paragraph"}``
            ``{"source": "bms.pdf"}``
            ``{"doc_type": "pdf"}``
        """
        if not self._check():
            return []
        conditions: List[str] = []
        params: Dict[str, Any] = {"lim": limit}
        for i, (key, val) in enumerate(filters.items()):
            pname = f"p{i}"
            if key == "node_type":
                conditions.append(f"cn.type = :{pname}")
                params[pname] = val
            elif key == "source":
                conditions.append(f"pd.source = :{pname}")
                params[pname] = val
            elif key == "doc_type":
                conditions.append(f"pd.type = :{pname}")
                params[pname] = val
            elif key == "document_id":
                conditions.append(f"pd.id::text = :{pname}")
                params[pname] = val
            else:
                conditions.append(f"cn.metadata @> :{pname}::jsonb")
                params[pname] = f'{{"{key}": {json.dumps(val)}}}'

        if not conditions:
            return self.lookup_all(limit)

        where_clause = " AND ".join(conditions)
        with self._db.get_session() as session:
            rows = session.execute(
                sa_text(f"""
                    SELECT cn.id, cn.type, cn.content, cn.reference,
                           cn.parent_id, cn.metadata,
                           pd.source, pd.type AS doc_type, pd.filename
                    FROM content_nodes cn
                    JOIN processed_documents pd ON pd.id = cn.document_id
                    WHERE {where_clause}
                    LIMIT :lim
                """),
                params,
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def lookup_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return all content nodes (up to limit)."""
        if not self._check():
            return []
        with self._db.get_session() as session:
            rows = session.execute(
                sa_text("""
                    SELECT cn.id, cn.type, cn.content, cn.reference,
                           cn.parent_id, cn.metadata,
                           pd.source, pd.type AS doc_type, pd.filename
                    FROM content_nodes cn
                    JOIN processed_documents pd ON pd.id = cn.document_id
                    LIMIT :lim
                """),
                {"lim": limit},
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return summary of all stored documents."""
        if not self._check():
            return []
        with self._db.get_session() as session:
            rows = session.execute(
                sa_text("""
                    SELECT id, source, type, filename, file_size,
                           content_node_count, edge_count, created_at
                    FROM processed_documents
                    ORDER BY created_at DESC
                """),
            ).fetchall()
            return [
                {
                    "id": str(r[0]),
                    "source": r[1],
                    "type": r[2],
                    "filename": r[3],
                    "file_size": r[4],
                    "content_node_count": r[5],
                    "edge_count": r[6],
                    "created_at": r[7].isoformat() if r[7] else "",
                }
                for r in rows
            ]

    def health_check(self) -> bool:
        return self._check()

    # ── Internal ────────────────────────────────

    def _check(self) -> bool:
        if not _HAS_SQLA:
            return False
        if self._connected_cache is False:
            return False
        if not self._db.is_connected:
            try:
                self._db.connect()
                self._connected_cache = True
            except Exception:
                self._connected_cache = False
                return False
        return True

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        content = row[2] if isinstance(row[2], (dict, str, int, float, list)) else str(row[2] or "")
        return {
            "id": row[0],
            "node_type": row[1],
            "content": content,
            "reference": row[3] if isinstance(row[3], dict) else {},
            "parent_id": row[4],
            "metadata": row[5] if isinstance(row[5], dict) else {},
            "source": row[6],
            "doc_type": row[7],
            "filename": row[8],
        }



