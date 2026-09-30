"""Repeatable full-archive benchmark, including native simulation and indexed storage."""

import argparse
import ctypes
import json
import platform
from contextlib import closing
from pathlib import Path

import numba
import numpy as np

from .config import Scenario
from .engine import generate
from .store import Archive


def peak_rss_bytes():
    if platform.system() == "Windows":

        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "peak_rss",
                    "rss",
                    "peak_paged",
                    "paged",
                    "peak_nonpaged",
                    "nonpaged",
                    "pagefile",
                    "peak_pagefile",
                    "private",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        current = ctypes.windll.kernel32.GetCurrentProcess
        current.restype = ctypes.c_void_p
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        if query(current(), ctypes.byref(counters), counters.cb):
            return counters.peak_rss
        return None
    import resource

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if platform.system() == "Darwin" else value * 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--population", type=int, default=1_000_000)
    parser.add_argument("--places", type=int, default=500)
    parser.add_argument("--years", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--backend", choices=["compiled", "reference"], default="compiled")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = generate(
        Scenario(
            initial_population=args.population,
            virtual_settlements=args.places,
            years=args.years,
            seed=args.seed,
            backend=args.backend,
        ),
        args.output,
    )
    with closing(Archive(args.output).connect()) as db:
        checks = {
            "quick_check": db.execute("PRAGMA quick_check").fetchone()[0],
            "places": db.execute("SELECT count(*) FROM settlements").fetchone()[0],
            "invalid_parent_order": db.execute(
                "SELECT count(*) FROM people WHERE father>=id OR mother>=id"
            ).fetchone()[0],
            "census_balance": db.execute(
                "SELECT count(*) FROM census c WHERE population != "
                "(SELECT sum(population) FROM settlement_census s WHERE s.year=c.year)"
            ).fetchone()[0],
        }
    result = {
        "summary": summary,
        "peak_rss_bytes": peak_rss_bytes(),
        "checks": checks,
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "numba": numba.__version__,
            "platform": platform.platform(),
        },
    }
    args.output.with_suffix(".benchmark.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
