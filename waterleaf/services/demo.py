from __future__ import annotations

from pathlib import Path

from waterleaf.models import TaxonCandidate, VisualAnalysis
from waterleaf.services.identification import IdentificationService

DEMO_TAXA = [
    TaxonCandidate(
        taxon_key="2925518",
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
    ),
    TaxonCandidate(
        taxon_key="2927009",
        scientific_name="Salvia officinalis",
        common_name="Common sage",
    ),
    TaxonCandidate(
        taxon_key="2926017",
        scientific_name="Salvia rosmarinus",
        common_name="Rosemary",
    ),
]


class DemoVision:
    def analyze_images(self, image_paths: list[Path]) -> VisualAnalysis:
        return VisualAnalysis(
            traits=[
                "purple flower spikes",
                "narrow gray-green leaves",
                "woody compact growth",
            ],
            proposed_names=[
                "Lavandula angustifolia",
                "Salvia officinalis",
                "Salvia rosmarinus",
            ],
            is_container=True,
            size_label="medium",
        )

    def rerank(self, image_paths, visual, candidates):
        scores = [0.92, 0.34, 0.18]
        reasons = [
            "Flower spikes and narrow gray-green leaves match.",
            "Leaf color is plausible, but the flower form is weaker.",
            "Woody growth is plausible, but leaf and flower shape differ.",
        ]
        return [
            {
                "taxon_key": candidate.taxon_key,
                "confidence": scores[index] if index < len(scores) else 0.1,
                "rationale": reasons[index] if index < len(reasons) else "Weak visual match.",
            }
            for index, candidate in enumerate(candidates)
        ]


class DemoTaxonomy:
    def suggest(self, query: str, limit: int = 10) -> list[TaxonCandidate]:
        needle = query.casefold().strip()
        if not needle:
            return []
        matches = [
            candidate
            for candidate in DEMO_TAXA
            if needle in candidate.common_name.casefold()
            or needle in candidate.scientific_name.casefold()
        ]
        return matches[:limit]


def build_demo_identification() -> IdentificationService:
    return IdentificationService(vision=DemoVision(), taxonomy=DemoTaxonomy())

