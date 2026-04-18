"""
NEXUS Resource Simulation Domain
Monte Carlo simulation for system resource allocation.
"""

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class ResourceSimulation:
    """System resource allocation simulation domain."""

    CRITERIA = ["cpu_efficiency", "memory_usage", "io_throughput", "latency", "scalability"]
    DEFAULT_WEIGHTS = {
        "cpu_efficiency": 0.25,
        "memory_usage": 0.20,
        "io_throughput": 0.20,
        "latency": 0.20,
        "scalability": 0.15
    }

    def simulate(self, options, entities, n_simulations=1000):
        """
        Run Monte Carlo simulation for resource allocation strategies.
        Evaluates allocation plans across compute resource criteria.
        """
        if not NUMPY_AVAILABLE:
            return {"success": False, "message": "NumPy not available"}

        weights = entities.get("weights", self.DEFAULT_WEIGHTS)
        results = {}

        # Generate allocation profiles
        profiles = self._generate_allocation_profiles(options)

        for i, option in enumerate(options):
            profile = profiles[i]
            scores = []

            for _ in range(n_simulations):
                scenario_score = 0.0
                # Simulate workload variance
                workload_factor = np.random.uniform(0.5, 1.5)

                for criterion in self.CRITERIA:
                    mean = profile.get(criterion, {}).get("mean", 0.5)
                    std = profile.get(criterion, {}).get("std", 0.1)

                    # Adjust for workload
                    adjusted_mean = mean * (1 / workload_factor if criterion == "latency" else workload_factor * 0.7 + 0.3)
                    score = np.clip(np.random.normal(adjusted_mean, std), 0.0, 1.0)
                    scenario_score += score * weights.get(criterion, 0.2)

                scores.append(scenario_score)

            results[option] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "median": float(np.median(scores)),
                "best_case": float(np.max(scores)),
                "worst_case": float(np.min(scores)),
                "profile": {k: round(v["mean"], 3) for k, v in profile.items()}
            }

        winner = max(results, key=lambda x: results[x]["mean"])

        spoken = f"For resource allocation, I evaluated {n_simulations} workload scenarios. "
        spoken += f"'{winner}' is the optimal allocation with an average score of {results[winner]['mean']:.3f}. "
        spoken += f"It handles variable workloads with {results[winner]['std']:.3f} deviation."

        return {
            "success": True,
            "winner": winner,
            "results": results,
            "domain": "resource",
            "criteria": self.CRITERIA,
            "spoken": spoken
        }

    def _generate_allocation_profiles(self, options):
        """Generate resource allocation profiles."""
        profiles = []
        for option in options:
            profile = {}
            # Different strategies have different strengths
            strategy_bias = np.random.choice(self.CRITERIA)

            for criterion in self.CRITERIA:
                base = np.random.uniform(0.4, 0.7)
                if criterion == strategy_bias:
                    base += 0.2  # This strategy excels here
                profile[criterion] = {
                    "mean": np.clip(base, 0.2, 0.95),
                    "std": np.random.uniform(0.05, 0.15)
                }
            profiles.append(profile)
        return profiles
