"""Generate, query or browse spatial genealogy without credentials or live services."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_scenario
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
        if args.command == "generate":
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

            result = generate(config, args.output, None if args.quiet else progress)
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
