from __future__ import annotations

from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import OntologyTerm


class OntologyService:
    def normalize(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def _find_best_term(self, db: Session, raw_query: str) -> OntologyTerm | None:
        query = self.normalize(raw_query)
        if not query:
            return None

        exact_stmt = select(OntologyTerm).where(func.lower(OntologyTerm.term) == query)
        exact = db.execute(exact_stmt).scalar_one_or_none()
        if exact:
            return exact

        fuzzy_stmt = (
            select(OntologyTerm, func.similarity(func.lower(OntologyTerm.term), query).label("score"))
            .where(func.lower(OntologyTerm.term).contains(query.split()[0]))
            .order_by(func.similarity(func.lower(OntologyTerm.term), query).desc())
            .limit(1)
        )
        row = db.execute(fuzzy_stmt).first()
        if row and row.score >= 0.18:
            return row.OntologyTerm

        fallback_stmt = (
            select(OntologyTerm, func.similarity(func.lower(OntologyTerm.term), query).label("score"))
            .order_by(func.similarity(func.lower(OntologyTerm.term), query).desc())
            .limit(1)
        )
        row = db.execute(fallback_stmt).first()
        if row and row.score >= 0.28:
            return row.OntologyTerm

        return None

    def expand_query(self, db: Session, query: str, max_depth: int | None = None) -> list[str]:
        depth_limit = max_depth or settings.max_ontology_depth
        matched = self._find_best_term(db, query)
        if not matched:
            return []

        chain: list[str] = []
        seen: set[str] = set()

        current = matched
        depth = 0
        while current and depth < depth_limit:
            normalized = self.normalize(current.term)
            if normalized not in seen:
                seen.add(normalized)
                chain.append(current.term)

            if not current.parent_term:
                break

            parent_stmt = select(OntologyTerm).where(func.lower(OntologyTerm.term) == self.normalize(current.parent_term))
            current = db.execute(parent_stmt).scalar_one_or_none()
            depth += 1

        return chain

    def suggest(self, db: Session, partial: str, limit: int = 8) -> list[str]:
        normalized = self.normalize(partial)
        if not normalized:
            return []

        prefix_stmt = (
            select(OntologyTerm.term)
            .where(func.lower(OntologyTerm.term).like(f"{normalized}%"))
            .order_by(func.char_length(OntologyTerm.term).asc(), OntologyTerm.term.asc())
            .limit(limit)
        )
        prefix_matches = [row[0] for row in db.execute(prefix_stmt).all()]
        if prefix_matches:
            return prefix_matches

        fuzzy_stmt = (
            select(OntologyTerm.term)
            .order_by(func.similarity(func.lower(OntologyTerm.term), normalized).desc(), OntologyTerm.term.asc())
            .limit(limit)
        )
        return [row[0] for row in db.execute(fuzzy_stmt).all()]

    def related_items(self, db: Session, query: str, limit: int = 6) -> list[str]:
        term = self._find_best_term(db, query)
        if not term:
            return []

        related: list[str] = []
        seen = {self.normalize(term.term)}

        if term.parent_term:
            siblings_stmt = (
                select(OntologyTerm.term)
                .where(func.lower(OntologyTerm.parent_term) == self.normalize(term.parent_term))
                .where(func.lower(OntologyTerm.term) != self.normalize(term.term))
                .limit(limit)
            )
            for row in db.execute(siblings_stmt).all():
                key = self.normalize(row.term)
                if key not in seen:
                    seen.add(key)
                    related.append(row.term)

        if len(related) < limit:
            children_stmt = (
                select(OntologyTerm.term)
                .where(func.lower(OntologyTerm.parent_term) == self.normalize(term.term))
                .limit(limit)
            )
            for row in db.execute(children_stmt).all():
                key = self.normalize(row.term)
                if key not in seen:
                    seen.add(key)
                    related.append(row.term)

        return related[:limit]

    def compute_depth_map(self, terms: Iterable[dict[str, str | None]]) -> dict[str, int]:
        parent_map: dict[str, str | None] = {}
        for item in terms:
            term = self.normalize(str(item["term"]))
            parent = item.get("parent_term")
            parent_map[term] = self.normalize(str(parent)) if parent else None

        memo: dict[str, int] = {}

        def depth(term_key: str) -> int:
            if term_key in memo:
                return memo[term_key]
            parent_key = parent_map.get(term_key)
            if not parent_key:
                memo[term_key] = 0
                return 0
            memo[term_key] = min(50, 1 + depth(parent_key))
            return memo[term_key]

        for key in parent_map:
            depth(key)
        return memo


ontology_service = OntologyService()
