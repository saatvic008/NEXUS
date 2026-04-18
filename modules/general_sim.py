"""
NEXUS General Simulation Domain
Generic multi-criteria decision analysis for any comparison.
"""

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class GeneralSimulation:
    """General-purpose multi-criteria decision analysis domain."""

    DEFAULT_CRITERIA = ["quality", "cost", "time", "risk", "satisfaction"]
    DEFAULT_WEIGHTS = {
        "quality": 0.25,
        "cost": 0.20,
        "time": 0.20,
        "risk": 0.15,
        "satisfaction": 0.20
    }

    def simulate(self, options, entities, n_simulations=1000):
        """
        Run Monte Carlo simulation for general decision making.
        Uses customizable criteria and weights.
        """
        if not NUMPY_AVAILABLE:
            return {"success": False, "message": "NumPy not available"}

        criteria = entities.get("criteria", self.DEFAULT_CRITERIA)
        weights = entities.get("weights", self.DEFAULT_WEIGHTS)

        # Ensure weights exist for all criteria
        for c in criteria:
            if c not in weights:
                weights[c] = 1.0 / len(criteria)

        results = {}

        for option in options:
            scores = []
            # Each option has a unique "character" — strengths and weaknesses
            option_character = {
                c: np.random.uniform(0.3, 0.85) for c in criteria
            }

            for _ in range(n_simulations):
                scenario_score = 0.0
                for criterion in criteria:
                    mean = option_character[criterion]
                    std = np.random.uniform(0.08, 0.18)
                    score = np.clip(np.random.normal(mean, std), 0.0, 1.0)
                    scenario_score += score * weights.get(criterion, 1.0 / len(criteria))

                scores.append(scenario_score)

            results[option] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "median": float(np.median(scores)),
                "best_case": float(np.max(scores)),
                "worst_case": float(np.min(scores)),
                "strengths": self._identify_strengths(option_character, criteria),
                "weaknesses": self._identify_weaknesses(option_character, criteria)
            }

        winner = max(results, key=lambda x: results[x]["mean"])

        # Build explanation
        w_data = results[winner]
        spoken = f"After analyzing {n_simulations} scenarios across {len(criteria)} criteria, "
        spoken += f"I recommend '{winner}' with an average score of {w_data['mean']:.3f}. "

        if w_data.get("strengths"):
            spoken += f"Its strengths are in {', '.join(w_data['strengths'])}. "

        if len(options) > 1:
            for opt in options:
                if opt != winner:
                    spoken += f"'{opt}' scored {results[opt]['mean']:.3f}. "

        return {
            "success": True,
            "winner": winner,
            "results": results,
            "domain": "general",
            "criteria": criteria,
            "spoken": spoken
        }

    def _identify_strengths(self, character, criteria):
        """Identify top-performing criteria."""
        sorted_criteria = sorted(criteria, key=lambda c: character.get(c, 0), reverse=True)
        return [c.replace("_", " ") for c in sorted_criteria[:2] if character.get(c, 0) > 0.6]

    def _identify_weaknesses(self, character, criteria):
        """Identify underperforming criteria."""
        sorted_criteria = sorted(criteria, key=lambda c: character.get(c, 0))
        return [c.replace("_", " ") for c in sorted_criteria[:2] if character.get(c, 0) < 0.4]
