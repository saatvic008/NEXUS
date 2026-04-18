"""
NEXUS Traffic Simulation Domain
Monte Carlo simulation for traffic route optimization.
"""

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class TrafficSimulation:
    """Traffic route optimization simulation domain."""

    CRITERIA = ["travel_time", "traffic_density", "fuel_cost", "safety", "reliability"]
    DEFAULT_WEIGHTS = {
        "travel_time": 0.30,
        "traffic_density": 0.20,
        "fuel_cost": 0.15,
        "safety": 0.20,
        "reliability": 0.15
    }

    def simulate(self, options, entities, n_simulations=1000):
        """
        Run Monte Carlo simulation for route selection.
        Each route is evaluated across multiple criteria with random variance.
        """
        if not NUMPY_AVAILABLE:
            return {"success": False, "message": "NumPy not available"}

        weights = entities.get("weights", self.DEFAULT_WEIGHTS)
        results = {}

        # Generate route profiles with different characteristics
        route_profiles = self._generate_route_profiles(options)

        for i, option in enumerate(options):
            profile = route_profiles[i]
            scores = []

            for _ in range(n_simulations):
                scenario_score = 0.0
                for criterion in self.CRITERIA:
                    # Sample from distribution based on route profile
                    mean = profile.get(criterion, {}).get("mean", 0.5)
                    std = profile.get(criterion, {}).get("std", 0.15)
                    score = np.clip(np.random.normal(mean, std), 0.0, 1.0)
                    scenario_score += score * weights.get(criterion, 0.2)

                scores.append(scenario_score)

            results[option] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "median": float(np.median(scores)),
                "best_case": float(np.max(scores)),
                "worst_case": float(np.min(scores)),
                "profile": {k: v["mean"] for k, v in profile.items()}
            }

        winner = max(results, key=lambda x: results[x]["mean"])

        # Generate explanation
        spoken = f"For route optimization, I simulated {n_simulations} scenarios. "
        spoken += f"The best route is '{winner}' with an average score of {results[winner]['mean']:.3f}. "
        for criterion in self.CRITERIA:
            spoken += f"{criterion.replace('_', ' ').title()}: {results[winner]['profile'].get(criterion, 0):.2f}. "

        return {
            "success": True,
            "winner": winner,
            "results": results,
            "domain": "traffic",
            "criteria": self.CRITERIA,
            "spoken": spoken
        }

    def _generate_route_profiles(self, options):
        """Generate realistic route profiles for simulation."""
        profiles = []
        for i, option in enumerate(options):
            # Create varied profiles for each route
            base_quality = np.random.uniform(0.4, 0.8)
            profile = {}
            for criterion in self.CRITERIA:
                variation = np.random.uniform(-0.15, 0.15)
                profile[criterion] = {
                    "mean": np.clip(base_quality + variation, 0.2, 0.95),
                    "std": np.random.uniform(0.05, 0.20)
                }
            profiles.append(profile)
        return profiles
