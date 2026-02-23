from __future__ import annotations

import json
from pathlib import Path

from .contracts import RelationEdge
from .utils import normalize_text, singularize, tokenize


class Phase6Taxonomy:
    def __init__(self, alias_path: Path | None = None, relation_path: Path | None = None):
        root = self._resolve_repo_root()
        aliases_file = alias_path or (root / "data" / "raw" / "phase6_aliases.json")
        relations_file = relation_path or (root / "data" / "raw" / "phase6_relations.json")

        self.concept_aliases: dict[str, list[str]] = self._load_aliases(aliases_file)
        self.alias_to_concept: dict[str, str] = self._build_alias_lookup(self.concept_aliases)
        self.relations: list[RelationEdge] = self._load_relations(relations_file)

        self.adjacency: dict[str, list[RelationEdge]] = {}
        self.reverse_adjacency: dict[str, list[RelationEdge]] = {}
        for edge in self.relations:
            self.adjacency.setdefault(edge.source, []).append(edge)
            self.reverse_adjacency.setdefault(edge.target, []).append(edge)

    @staticmethod
    def _resolve_repo_root() -> Path:
        candidates = [
            Path("/workspace"),
            Path(__file__).resolve().parents[4],
            Path.cwd(),
        ]
        for candidate in candidates:
            if (candidate / "data" / "raw" / "phase6_aliases.json").exists():
                return candidate
        return Path(__file__).resolve().parents[4]

    @staticmethod
    def _load_aliases(path: Path) -> dict[str, list[str]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        output: dict[str, list[str]] = {}
        for concept_id, aliases in payload.items():
            if not isinstance(concept_id, str) or not isinstance(aliases, list):
                continue
            output[concept_id] = [str(alias) for alias in aliases if isinstance(alias, str)]
        return output

    @staticmethod
    def _load_relations(path: Path) -> list[RelationEdge]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        output: list[RelationEdge] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source") or "").strip()
            relation = str(row.get("relation") or "").strip()
            target = str(row.get("target") or "").strip()
            provenance = str(row.get("provenance") or "phase6.curated")
            if not source or not relation or not target:
                continue
            output.append(
                RelationEdge(
                    source=source,
                    relation=relation,
                    target=target,
                    provenance=provenance,
                )
            )
        return output

    def _build_alias_lookup(self, concept_aliases: dict[str, list[str]]) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for concept, aliases in concept_aliases.items():
            concept_label = concept.split(".")[-1].replace("_", " ")
            expanded_aliases = list(aliases) + [concept_label]
            for raw_alias in expanded_aliases:
                normalized = normalize_text(raw_alias)
                if not normalized:
                    continue
                lookup.setdefault(normalized, concept)

                tokens = tokenize(normalized)
                singular_tokens = [singularize(token) for token in tokens]
                if singular_tokens:
                    singular_phrase = " ".join(singular_tokens)
                    if singular_phrase:
                        lookup.setdefault(singular_phrase, concept)

                words = normalized.split()
                if len(words) == 1:
                    singular_word = singularize(words[0])
                    if singular_word:
                        lookup.setdefault(singular_word, concept)
        return lookup

    def concept_for_phrase(self, phrase: str) -> str | None:
        return self.alias_to_concept.get(normalize_text(phrase))

    @staticmethod
    def label_for(concept_id: str) -> str:
        return concept_id.split(".")[-1].replace("_", " ")

    def query_slice_keys(self, concept_ids: list[str]) -> set[str]:
        keys: set[str] = set()
        for concept in concept_ids:
            parts = concept.split(".")
            if len(parts) < 2:
                continue
            if parts[0] == "biz" and len(parts) >= 3 and parts[1] == "type":
                keys.add("business_type")
            keys.add(parts[0])
            keys.add(f"{parts[0]}.{parts[1]}")
        return keys
