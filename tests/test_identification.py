from pathlib import Path

from waterleaf.models import TaxonCandidate, VisualAnalysis
from waterleaf.services.identification import IdentificationService


class FakeVision:
    def analyze_images(self, image_paths):
        assert image_paths == [Path("plant.jpg")]
        return VisualAnalysis(
            traits=["purple flower spikes", "narrow gray-green leaves"],
            proposed_names=["Lavandula angustifolia", "Salvia officinalis"],
            is_container=True,
            size_label="medium",
        )

    def rerank(self, image_paths, visual, candidates):
        assert all(candidate.taxon_key for candidate in candidates)
        return [
            {"taxon_key": "lavender", "confidence": 0.91, "rationale": "Flower and leaf match"},
            {"taxon_key": "sage", "confidence": 0.22, "rationale": "Leaf color only"},
            {"taxon_key": "invented", "confidence": 0.99, "rationale": "Must be ignored"},
        ]


class FakeTaxonomy:
    def suggest(self, query, limit=5):
        if query == "Lavandula angustifolia":
            return [
                TaxonCandidate(
                    taxon_key="lavender",
                    scientific_name="Lavandula angustifolia",
                    common_name="English lavender",
                )
            ]
        if query == "Salvia officinalis":
            return [
                TaxonCandidate(
                    taxon_key="sage",
                    scientific_name="Salvia officinalis",
                    common_name="Common sage",
                )
            ]
        return []


def test_identification_only_returns_grounded_reranked_candidates():
    service = IdentificationService(vision=FakeVision(), taxonomy=FakeTaxonomy())

    result = service.identify([Path("plant.jpg")])

    assert [candidate.taxon_key for candidate in result.candidates] == [
        "lavender",
        "sage",
    ]
    assert result.candidates[0].confidence == 0.91
    assert result.visual.is_container is True

