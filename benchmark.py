"""
Benchmark Runner — runs every dispatch strategy × every scenario × N seeds.

Usage:
    python benchmark.py                   # 5 seeds, all strategies & scenarios
    python benchmark.py --seeds 20        # 20 seeds for full results
    python benchmark.py --strategy gbfs   # only GBFS
    python benchmark.py --scenario morning_rush  # only morning rush

Outputs:
    results/benchmark_results.csv   — full results table
    results/benchmark_summary.md    — formatted markdown summary
    Console: progress + final comparison table
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

# Resolve project root
_project_root = os.path.abspath(os.path.dirname(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.simulator.engine import SimulationEngine
from backend.dispatch import get_strategy_names
from backend.scenarios.traffic import get_scenario_names


# ═══════════════════════════════════════════════════════════════════════════
# Result fields
# ═══════════════════════════════════════════════════════════════════════════
RESULT_FIELDS = [
    "strategy",
    "scenario",
    "seed",
    "total_calls",
    "total_completed",
    "avg_wait_sec",
    "max_wait_sec",
    "sla_met",
    "sla_violation_pct",
    "total_distance",
    "capacity_rejections",
    "reoptimisations",
    "runtime_sec",
]


def run_single(
    config_path: str,
    strategy_name: str,
    scenario_name: str,
    seed: int,
) -> dict:
    """Run a single simulation and return the result row."""
    t0 = time.time()

    engine = SimulationEngine(
        config_path=config_path,
        strategy_name=strategy_name,
        scenario_name=scenario_name,
        seed=seed,
        quiet=True,
    )
    summary = engine.run_simulation()
    elapsed = time.time() - t0

    sla_target = summary.get("sla_target_sec", 45.0)
    avg_wait = summary.get("avg_wait_time_sec", 0.0)
    total_completed = summary.get("total_completed", 0)

    # Compute SLA violation percentage (% of completed trips above SLA)
    # We use average vs target as a proxy since we don't track individual
    sla_violation_pct = 0.0
    if total_completed > 0 and avg_wait > sla_target:
        sla_violation_pct = min(
            ((avg_wait - sla_target) / sla_target) * 100.0, 100.0
        )

    return {
        "strategy": strategy_name,
        "scenario": scenario_name,
        "seed": seed,
        "total_calls": summary.get("total_calls_generated", 0),
        "total_completed": total_completed,
        "avg_wait_sec": round(avg_wait, 2),
        "max_wait_sec": round(summary.get("max_wait_time_sec", 0.0), 2),
        "sla_met": summary.get("sla_met", False),
        "sla_violation_pct": round(sla_violation_pct, 2),
        "total_distance": summary.get("total_distance_floors", 0),
        "capacity_rejections": summary.get("capacity_rejections", 0),
        "reoptimisations": summary.get("total_reoptimisations", 0),
        "runtime_sec": round(elapsed, 2),
    }


def run_benchmark(
    config_path: str,
    strategies: list[str],
    scenarios: list[str],
    seeds: list[int],
) -> list[dict]:
    """Run the full benchmark matrix."""
    total_runs = len(strategies) * len(scenarios) * len(seeds)
    results: list[dict] = []
    run_idx = 0

    print("=" * 70)
    print("  ELEVATOR FLEET DISPATCHER — BENCHMARK")
    print("=" * 70)
    print(f"  Strategies : {', '.join(strategies)}")
    print(f"  Scenarios  : {', '.join(scenarios)}")
    print(f"  Seeds      : {len(seeds)} ({seeds[0]}..{seeds[-1]})")
    print(f"  Total runs : {total_runs}")
    print("=" * 70)
    print()

    for strategy in strategies:
        for scenario in scenarios:
            for seed in seeds:
                run_idx += 1
                tag = f"[{run_idx}/{total_runs}]"
                print(
                    f"  {tag:>12} {strategy:<14} × {scenario:<16} "
                    f"seed={seed}",
                    end=" ... ",
                    flush=True,
                )

                try:
                    result = run_single(config_path, strategy, scenario, seed)
                    results.append(result)
                    print(
                        f"avg_wait={result['avg_wait_sec']:>6.1f}s  "
                        f"completed={result['total_completed']:>4}  "
                        f"SLA={'Y' if result['sla_met'] else 'N'}  "
                        f"({result['runtime_sec']:.1f}s)"
                    )
                except Exception as exc:
                    print(f"ERROR: {exc}")
                    results.append({
                        "strategy": strategy,
                        "scenario": scenario,
                        "seed": seed,
                        "error": str(exc),
                    })

    return results


def save_results(results: list[dict], output_dir: str) -> tuple[str, str]:
    """Save results to CSV and markdown summary."""
    os.makedirs(output_dir, exist_ok=True)

    # --- CSV ---
    csv_path = os.path.join(output_dir, "benchmark_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            if "error" not in row:
                writer.writerow(row)
    print(f"\n  CSV saved to: {csv_path}")

    # --- Markdown summary ---
    md_path = os.path.join(output_dir, "benchmark_summary.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("# Benchmark Results\n\n")
        fh.write(f"Generated: {datetime.now().isoformat()}\n\n")

        # Aggregate by strategy × scenario
        agg: dict[tuple[str, str], list[dict]] = {}
        for r in results:
            if "error" in r:
                continue
            key = (r["strategy"], r["scenario"])
            agg.setdefault(key, []).append(r)

        # Summary table
        fh.write("## Summary (averaged across seeds)\n\n")
        fh.write(
            "| Strategy | Scenario | Avg Wait (s) | Max Wait (s) "
            "| SLA Met % | Distance | Completed |\n"
        )
        fh.write(
            "|---|---|---|---|---|---|---|\n"
        )

        for (strategy, scenario), runs in sorted(agg.items()):
            n = len(runs)
            avg_wait = sum(r["avg_wait_sec"] for r in runs) / n
            max_wait = max(r["max_wait_sec"] for r in runs)
            sla_pct = sum(1 for r in runs if r["sla_met"]) / n * 100
            total_dist = sum(r["total_distance"] for r in runs) / n
            completed = sum(r["total_completed"] for r in runs) / n

            fh.write(
                f"| {strategy} | {scenario} | {avg_wait:.1f} | {max_wait:.1f} "
                f"| {sla_pct:.0f}% | {total_dist:.0f} | {completed:.0f} |\n"
            )

        fh.write("\n")

    print(f"  Summary saved to: {md_path}")
    return csv_path, md_path


def print_comparison_table(results: list[dict]) -> None:
    """Print a compact comparison table to console."""
    # Aggregate by strategy
    by_strategy: dict[str, list[dict]] = {}
    for r in results:
        if "error" in r:
            continue
        by_strategy.setdefault(r["strategy"], []).append(r)

    print()
    print("=" * 70)
    print("  OVERALL COMPARISON (averaged across all scenarios and seeds)")
    print("=" * 70)
    print(
        f"  {'Strategy':<16} {'Avg Wait':>10} {'Max Wait':>10} "
        f"{'SLA Met':>8} {'Distance':>10} {'Completed':>10}"
    )
    print("  " + "-" * 64)

    for strategy in sorted(by_strategy.keys()):
        runs = by_strategy[strategy]
        n = len(runs)
        avg_wait = sum(r["avg_wait_sec"] for r in runs) / n
        max_wait = max(r["max_wait_sec"] for r in runs)
        sla_pct = sum(1 for r in runs if r["sla_met"]) / n * 100
        total_dist = sum(r["total_distance"] for r in runs) / n
        completed = sum(r["total_completed"] for r in runs) / n

        print(
            f"  {strategy:<16} {avg_wait:>9.1f}s {max_wait:>9.1f}s "
            f"{sla_pct:>7.0f}% {total_dist:>10.0f} {completed:>10.0f}"
        )

    print("=" * 70)
    print()


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark elevator dispatch strategies."
    )
    parser.add_argument(
        "--config",
        default=os.path.join(_project_root, "config.json"),
        help="Path to config.json",
    )
    parser.add_argument(
        "--seeds", type=int, default=5,
        help="Number of seeds to run per combination (default: 5)",
    )
    parser.add_argument(
        "--strategy",
        choices=get_strategy_names(),
        default=None,
        help="Run only this strategy (default: all)",
    )
    parser.add_argument(
        "--scenario",
        choices=get_scenario_names(),
        default=None,
        help="Run only this scenario (default: all)",
    )
    parser.add_argument(
        "--output", default=os.path.join(_project_root, "results"),
        help="Output directory for results",
    )
    args = parser.parse_args()

    strategies = (
        [args.strategy] if args.strategy else get_strategy_names()
    )
    scenarios = (
        [args.scenario] if args.scenario else get_scenario_names()
    )
    seeds = list(range(42, 42 + args.seeds))

    results = run_benchmark(args.config, strategies, scenarios, seeds)
    save_results(results, args.output)
    print_comparison_table(results)


if __name__ == "__main__":
    main()
