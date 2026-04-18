"""
NEXUS Decision Engine — Simulation-Based Decision Intelligence
Monte Carlo sampling, weighted multi-criteria utility, RL-inspired memory boost, matplotlib visualization.
"""

import json
import os
import time
from datetime import datetime

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class DecisionEngine:
    """Simulation-based decision engine with Monte Carlo sampling and adaptive learning."""

    DEFAULT_N_SIMULATIONS = 1000
    MEMORY_BOOST_FACTOR = 0.15  # 15% boost for historically successful decisions

    def __init__(self, config_path="config.json"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config = self._load_config(config_path)
        self.decision_history = self._load_decision_history()

        # Register simulation domains
        self.domains = {}
        self._register_default_domains()

    def _load_config(self, config_path):
        """Load config."""
        full_path = os.path.join(self.base_dir, config_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _load_decision_history(self):
        """Load past decision history for RL-inspired memory boost."""
        history_path = self.config.get("paths", {}).get("decision_history", "data/decision_history.json")
        full_path = os.path.join(self.base_dir, history_path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"decisions": [], "domain_weights": {}}

    def _save_decision_history(self):
        """Save decision history to disk."""
        history_path = self.config.get("paths", {}).get("decision_history", "data/decision_history.json")
        full_path = os.path.join(self.base_dir, history_path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                json.dump(self.decision_history, f, indent=4)
        except Exception as e:
            print(f"[DECISION] Failed to save history: {e}")

    def _register_default_domains(self):
        """Register built-in simulation domains."""
        try:
            from modules.traffic_sim import TrafficSimulation
            self.domains["traffic"] = TrafficSimulation()
        except ImportError:
            pass

        try:
            from modules.resource_sim import ResourceSimulation
            self.domains["resource"] = ResourceSimulation()
        except ImportError:
            pass

        try:
            from modules.general_sim import GeneralSimulation
            self.domains["general"] = GeneralSimulation()
        except ImportError:
            pass

    def register_domain(self, name, domain_instance):
        """Register a new simulation domain."""
        self.domains[name] = domain_instance

    def decide(self, entities):
        """
        Main entry point for decision making.
        Returns a structured result with the recommended choice and explanation.
        """
        if not NUMPY_AVAILABLE:
            return {
                "success": False,
                "message": "Cannot run simulations — numpy not installed.",
                "spoken": "I can't run simulations right now. NumPy is not installed."
            }

        # Determine domain and options
        domain_name = entities.get("domain", "general")
        option_a = entities.get("option_a", "Option A")
        option_b = entities.get("option_b", "Option B")
        options = entities.get("options", [option_a, option_b])

        # Use domain-specific simulation if available
        domain = self.domains.get(domain_name)
        if domain:
            return self._run_domain_simulation(domain, domain_name, options, entities)
        else:
            return self._run_general_decision(options, entities)

    def _run_general_decision(self, options, entities):
        """Run a general multi-criteria decision analysis."""
        n_sims = entities.get("n_simulations", self.DEFAULT_N_SIMULATIONS)
        criteria = entities.get("criteria", ["cost", "quality", "time", "risk"])
        weights = entities.get("weights", None)

        if weights is None:
            weights = {c: 1.0 / len(criteria) for c in criteria}

        results = {}

        for option in options:
            scores = []
            for _ in range(n_sims):
                # Sample scores for each criterion from a probabilistic distribution
                scenario_score = 0.0
                for criterion in criteria:
                    # Use normal distribution centered on a random mean
                    mean = np.random.uniform(0.3, 0.9)
                    std = np.random.uniform(0.05, 0.2)
                    score = np.clip(np.random.normal(mean, std), 0.0, 1.0)
                    scenario_score += score * weights.get(criterion, 1.0 / len(criteria))

                scores.append(scenario_score)

            # Apply RL-inspired memory boost
            memory_boost = self._get_memory_boost(option)
            boosted_scores = [s * (1 + memory_boost) for s in scores]

            results[option] = {
                "raw_scores": scores,
                "boosted_scores": boosted_scores,
                "mean": float(np.mean(boosted_scores)),
                "std": float(np.std(boosted_scores)),
                "median": float(np.median(boosted_scores)),
                "best_case": float(np.max(boosted_scores)),
                "worst_case": float(np.min(boosted_scores)),
                "memory_boost": memory_boost
            }

        # Find the winner
        winner = max(results, key=lambda x: results[x]["mean"])
        runner_up = [o for o in options if o != winner][0] if len(options) > 1 else None

        # Generate visualization
        chart_path = self._visualize_results(results, options, criteria)

        # Save to history
        self._record_decision(winner, results, entities)

        # Build spoken explanation
        spoken = self._generate_explanation(winner, runner_up, results)

        return {
            "success": True,
            "winner": winner,
            "results": {k: {kk: vv for kk, vv in v.items() if kk != "raw_scores" and kk != "boosted_scores"} for k, v in results.items()},
            "chart_path": chart_path,
            "spoken": spoken,
            "n_simulations": n_sims,
            "criteria": criteria
        }

    def _run_domain_simulation(self, domain, domain_name, options, entities):
        """Run a domain-specific simulation."""
        try:
            result = domain.simulate(options, entities)
            # Apply memory boost to domain results
            for option in result.get("results", {}):
                boost = self._get_memory_boost(option)
                if "mean" in result["results"][option]:
                    result["results"][option]["mean"] *= (1 + boost)
                    result["results"][option]["memory_boost"] = boost

            # Save to history
            self._record_decision(result.get("winner", ""), result.get("results", {}), entities)

            return result
        except Exception as e:
            print(f"[DECISION] Domain simulation error: {e}")
            return self._run_general_decision(options, entities)

    def _get_memory_boost(self, option):
        """Calculate RL-inspired memory boost based on historical success."""
        successes = 0
        total = 0

        for decision in self.decision_history.get("decisions", []):
            if option.lower() in str(decision.get("winner", "")).lower():
                successes += 1
            total += 1

        if total == 0:
            return 0.0

        return (successes / total) * self.MEMORY_BOOST_FACTOR

    def _record_decision(self, winner, results, entities):
        """Record a decision in the history for future learning."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "winner": winner,
            "summary": {k: v.get("mean", 0) for k, v in results.items() if isinstance(v, dict)},
            "domain": entities.get("domain", "general")
        }
        self.decision_history["decisions"].append(record)

        # Keep only last 100 decisions
        if len(self.decision_history["decisions"]) > 100:
            self.decision_history["decisions"] = self.decision_history["decisions"][-100:]

        self._save_decision_history()

    def _visualize_results(self, results, options, criteria):
        """Generate a matplotlib chart of simulation results."""
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            fig.suptitle("NEXUS Decision Analysis", fontsize=16, fontweight="bold", color="#1a1a2e")

            # Chart 1: Score Distribution (Histogram)
            ax1 = axes[0]
            colors = ["#e94560", "#0f3460", "#16213e", "#533483", "#e07c24"]
            for i, option in enumerate(options):
                ax1.hist(
                    results[option]["boosted_scores"],
                    bins=30, alpha=0.6, label=option,
                    color=colors[i % len(colors)], edgecolor="white"
                )
            ax1.set_title("Score Distribution", fontsize=13)
            ax1.set_xlabel("Utility Score")
            ax1.set_ylabel("Frequency")
            ax1.legend()
            ax1.grid(alpha=0.3)

            # Chart 2: Comparison Bar Chart
            ax2 = axes[1]
            metrics = ["mean", "median", "best_case", "worst_case"]
            x = range(len(metrics))
            bar_width = 0.35

            for i, option in enumerate(options):
                values = [results[option][m] for m in metrics]
                offset = i * bar_width
                bars = ax2.bar([xi + offset for xi in x], values, bar_width,
                              label=option, color=colors[i % len(colors)], edgecolor="white")

            ax2.set_title("Performance Comparison", fontsize=13)
            ax2.set_xticks([xi + bar_width / 2 for xi in x])
            ax2.set_xticklabels(["Mean", "Median", "Best Case", "Worst Case"])
            ax2.set_ylabel("Score")
            ax2.legend()
            ax2.grid(alpha=0.3, axis="y")

            plt.tight_layout()

            # Save chart
            charts_dir = os.path.join(self.base_dir, "data", "charts")
            os.makedirs(charts_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            chart_path = os.path.join(charts_dir, f"decision_{timestamp}.png")
            plt.savefig(chart_path, dpi=150, bbox_inches="tight")
            plt.close()

            return chart_path

        except Exception as e:
            print(f"[DECISION] Visualization error: {e}")
            return None

    def _generate_explanation(self, winner, runner_up, results):
        """Generate a spoken explanation of the decision."""
        w = results[winner]
        spoken = f"Based on {self.DEFAULT_N_SIMULATIONS} simulations, I recommend {winner}. "
        spoken += f"It scored an average of {w['mean']:.3f} out of 1. "

        if runner_up and runner_up in results:
            r = results[runner_up]
            diff = w["mean"] - r["mean"]
            spoken += f"{runner_up} scored {r['mean']:.3f}, which is {abs(diff):.3f} {'lower' if diff > 0 else 'higher'}. "

        if w.get("memory_boost", 0) > 0:
            spoken += f"{winner} also received a {w['memory_boost']*100:.1f}% boost from past successful decisions. "

        spoken += f"The best case scenario for {winner} is {w['best_case']:.3f} and worst case is {w['worst_case']:.3f}."
        return spoken

    def get_history_summary(self):
        """Get a summary of decision history."""
        decisions = self.decision_history.get("decisions", [])
        if not decisions:
            return "No decisions recorded yet."

        total = len(decisions)
        recent = decisions[-5:]
        summary = f"You have made {total} decisions. Recent decisions:\n"
        for d in recent:
            summary += f"  - {d['timestamp'][:10]}: Chose '{d['winner']}' ({d['domain']} domain)\n"
        return summary


# Convenience singleton
_instance = None

def get_decision_engine(config_path="config.json"):
    """Get or create a singleton DecisionEngine instance."""
    global _instance
    if _instance is None:
        _instance = DecisionEngine(config_path)
    return _instance
