"""Generate, query or browse spatial genealogy without credentials or live services."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Scenario, load_scenario
from .engine import generate
from .store import Archive


def main():
    parser = argparse.ArgumentParser(prog="ttrpg-population")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser(
        "generate", help="Simulate a YAML scenario into a new SQLite archive"
    )
    build.add_argument("scenario", type=Path)
    build.add_argument("--output", type=Path, default=Path("output/genealogy/world.sqlite"))
    build.add_argument("--seed", type=int)
    build.add_argument("--years", type=int)
    build.add_argument("--target", type=int)
    build.add_argument("--quiet", action="store_true")
    simulate = commands.add_parser(
        "simulate", help="Simulate exact binary histories in RAM; no writes"
    )
    simulate.add_argument("scenario", type=Path)
    simulate.add_argument("--seed", type=int)
    simulate.add_argument("--years", type=int)
    simulate.add_argument("--target", type=int)
    simulate.add_argument("--quiet", action="store_true")
    studio = commands.add_parser("studio", help="Start the in-memory studio without creating files")
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--scenario", type=Path)
    compact = commands.add_parser(
        "compact", help="Export exact life histories as packed binary arrays"
    )
    compact.add_argument("archive", type=Path)
    compact.add_argument("--output", type=Path, required=True)
    query = commands.add_parser("person", help="Inspect life, unions, migrations and ancestry")
    query.add_argument("archive", type=Path)
    query.add_argument("id", type=int)
    query.add_argument("--depth", type=int, default=4)
    query.add_argument("--direction", choices=["ancestors", "descendants"], default="ancestors")
    query.add_argument("--year", type=int)
    stats = commands.add_parser("stats")
    stats.add_argument("archive", type=Path)
    serve = commands.add_parser("explore", help="Start the local generation studio and explorer")
    serve.add_argument("archive", type=Path)
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        if args.command in {"generate", "simulate"}:
            config = load_scenario(args.scenario)
            overrides = {
                key: value
                for key, value in {
                    "seed": args.seed,
                    "years": args.years,
                    "target_population": args.target,
                }.items()
                if value is not None
            }
            config = type(config).model_validate({**config.model_dump(), **overrides})

            def progress(year, count):
                if (
                    year - config.start_year
                ) % 10 == 0 or year == config.start_year + config.duration:
                    print(f"{year}: {count:,} living", file=sys.stderr)

            result = generate(
                config,
                args.output if args.command == "generate" else None,
                None if args.quiet else progress,
            )
            if args.command == "simulate":
                result = result.summary
        elif args.command == "studio":
            from .server import serve

            config = (
                load_scenario(args.scenario)
                if args.scenario
                else Scenario(
                    initial_population=10000,
                    virtual_settlements=500,
                    years=10,
                    target_mode="report",
                )
            )
            serve(generate(config, None), args.port)
            return
        elif args.command == "compact":
            from .compact import export_compact

            result = export_compact(args.archive, args.output)
        elif args.command == "person":
            archive = Archive(args.archive)
            result = {
                "person": archive.person(args.id),
                "lineage": archive.lineage(
                    args.id,
                    args.depth,
                    args.direction,
                ),
            }
            if args.year is not None:
                result["residence"] = archive.residence(args.id, args.year)
        elif args.command == "stats":
            result = Archive(args.archive).overview()
        else:
            from .server import serve

            serve(args.archive, args.port)
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, FileNotFoundError, FileExistsError) as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    main()
