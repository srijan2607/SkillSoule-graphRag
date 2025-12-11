"""Unit tests for hybrid scoring functionality."""

import pytest
from app.agents.nodes.vector_search import calculate_hybrid_score


class TestHybridScoring:
    """Test hybrid scoring calculation."""

    def test_calculate_hybrid_score_all_components(self):
        """Test hybrid score with all components present."""
        node = {
            "centrality": 0.8,
            "demand_count": 50,
        }
        vector_score = 0.9
        max_demand = 100

        # Expected: 0.5*0.9 + 0.3*0.8 + 0.2*(50/100) = 0.45 + 0.24 + 0.10 = 0.79
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.79

    def test_calculate_hybrid_score_no_centrality(self):
        """Test hybrid score when centrality is missing (defaults to 0)."""
        node = {
            "demand_count": 100,
        }
        vector_score = 1.0
        max_demand = 100

        # Expected: 0.5*1.0 + 0.3*0.0 + 0.2*(100/100) = 0.5 + 0.0 + 0.2 = 0.7
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.7

    def test_calculate_hybrid_score_no_demand(self):
        """Test hybrid score when demand is missing (defaults to 0)."""
        node = {
            "centrality": 1.0,
        }
        vector_score = 0.8
        max_demand = 100

        # Expected: 0.5*0.8 + 0.3*1.0 + 0.2*0 = 0.4 + 0.3 + 0.0 = 0.7
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.7

    def test_calculate_hybrid_score_max_demand_zero(self):
        """Test hybrid score when max_demand is zero (edge case)."""
        node = {
            "centrality": 0.5,
            "demand_count": 50,
        }
        vector_score = 0.6
        max_demand = 0  # Edge case

        # Expected: 0.5*0.6 + 0.3*0.5 + 0.2*0 = 0.3 + 0.15 + 0.0 = 0.45
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.45

    def test_calculate_hybrid_score_max_values(self):
        """Test hybrid score with maximum values."""
        node = {
            "centrality": 1.0,
            "demand_count": 200,
        }
        vector_score = 1.0
        max_demand = 200

        # Expected: 0.5*1.0 + 0.3*1.0 + 0.2*1.0 = 0.5 + 0.3 + 0.2 = 1.0
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 1.0

    def test_calculate_hybrid_score_min_values(self):
        """Test hybrid score with minimum values."""
        node = {
            "centrality": 0.0,
            "demand_count": 0,
        }
        vector_score = 0.0
        max_demand = 100

        # Expected: 0.5*0.0 + 0.3*0.0 + 0.2*0.0 = 0.0
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.0

    def test_calculate_hybrid_score_formula_weights(self):
        """Test that the formula uses correct weights (50%, 30%, 20%)."""
        node = {
            "centrality": 0.6,
            "demand_count": 30,
        }
        vector_score = 0.5
        max_demand = 100

        # Expected: 0.5*0.5 + 0.3*0.6 + 0.2*0.3 = 0.25 + 0.18 + 0.06 = 0.49
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.49

    def test_calculate_hybrid_score_demand_normalization(self):
        """Test demand normalization works correctly."""
        node = {
            "centrality": 0.0,
            "demand_count": 75,
        }
        vector_score = 0.0
        max_demand = 150

        # Expected: 0.5*0.0 + 0.3*0.0 + 0.2*(75/150) = 0.0 + 0.0 + 0.1 = 0.1
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert pytest.approx(hybrid_score, rel=0.01) == 0.1

    def test_calculate_hybrid_score_realistic_scenario(self):
        """Test hybrid score with realistic job market data."""
        # Scenario: Python skill
        node = {
            "name": "Python",
            "centrality": 0.92,  # High centrality
            "demand_count": 150,  # High demand
        }
        vector_score = 0.85  # High similarity to query
        max_demand = 200

        # Expected: 0.5*0.85 + 0.3*0.92 + 0.2*(150/200) = 0.425 + 0.276 + 0.15 = 0.851
        hybrid_score = calculate_hybrid_score(node, vector_score, max_demand)

        assert hybrid_score > 0.8  # Should be very high
        assert hybrid_score <= 1.0
        assert pytest.approx(hybrid_score, rel=0.01) == 0.851
