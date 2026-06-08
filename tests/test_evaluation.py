from waterleaf.evaluation import score_predictions


def test_evaluation_reports_species_genus_and_top_three_accuracy():
    rows = [
        {
            "expected": "Lavandula angustifolia",
            "predictions": [
                "Lavandula angustifolia",
                "Salvia officinalis",
                "Salvia rosmarinus",
            ],
        },
        {
            "expected": "Salvia officinalis",
            "predictions": [
                "Salvia rosmarinus",
                "Salvia officinalis",
            ],
        },
        {
            "expected": "Rosa canina",
            "predictions": ["Rosa rubiginosa"],
        },
    ]

    metrics = score_predictions(rows)

    assert metrics["count"] == 3
    assert metrics["species_top_1"] == 1 / 3
    assert metrics["species_top_3"] == 2 / 3
    assert metrics["genus_top_1"] == 1.0

