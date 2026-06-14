from __future__ import annotations

from pathlib import Path
from typing import Protocol

from waterleaf.models import IdentificationResult, TaxonCandidate, VisualAnalysis


class VisionService(Protocol):
    def analyze_images(self, image_paths: list[Path]) -> VisualAnalysis: ...

    def rerank(
        self,
        image_paths: list[Path],
        visual: VisualAnalysis,
        candidates: list[TaxonCandidate],
    ) -> list[dict]: ...


class TaxonomyService(Protocol):
    def suggest(self, query: str, limit: int = 5) -> list[TaxonCandidate]: ...


class IdentificationService:
    def __init__(self, *, vision: VisionService, taxonomy: TaxonomyService):
        self.vision = vision
        self.taxonomy = taxonomy

    def identify(self, image_paths: list[Path]) -> IdentificationResult:
        visual = self.vision.analyze_images(image_paths)
        grounded: list[TaxonCandidate] = []
        seen: set[str] = set()
        for name in visual.proposed_names:
            for candidate in self.taxonomy.suggest(name, limit=3):
                if candidate.taxon_key not in seen:
                    grounded.append(candidate)
                    seen.add(candidate.taxon_key)
                    break

        ranking = self.vision.rerank(image_paths, visual, grounded)
        ranking_by_key = {
            item["taxon_key"]: item for item in ranking if item["taxon_key"] in seen
        }
        candidates: list[TaxonCandidate] = []
        for candidate in grounded:
            scored = ranking_by_key.get(candidate.taxon_key)
            if not scored:
                continue
            candidates.append(
                candidate.model_copy(
                    update={
                        "confidence": scored["confidence"],
                        "rationale": scored["rationale"],
                    }
                )
            )
        candidates.sort(key=lambda item: item.confidence, reverse=True)
        return IdentificationResult(visual=visual, candidates=candidates[:3])

