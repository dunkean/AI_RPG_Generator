# Repository Guidelines

## Project Structure & Module Organization

This Python 3.11+ application generates tabletop RPG communities through an eleven-step pipeline combining LLM requests and procedural generation. `src/cli.py` exposes the CLI; `src/pipeline.py` orchestrates generation. Keep prompts, parsers, validators, Pydantic models, and procedural algorithms in their respective `src/` packages. LLM backends live in `src/providers/`; image backends and ComfyUI workflows live in `src/image/`. Rendering and caching reside in `src/output/` and `src/cache/`.

`config/default.yaml` supplies defaults; `config/projects/<name>.yaml` supplies project overrides. `templates/` contains Jinja2 HTML and CSS assets. Tests and mock responses live in `tests/` and `tests/fixtures/`. Consult `docs/` for design notes; treat `archive/` as historical reference.

## Build, Test, and Development Commands

Run commands from the repository root:

- `python -m pip install -e ".[dev]"`: install the application and development dependencies.
- `python -m src.cli enclave --no-images`: generate the example project without images; requires an OpenAI API key.
- `ttrpg-generate enclave --steps 1-4 --seed 123`: run selected steps with an explicit seed.
- `python -m pytest`: run the test suite.
- `python -m pytest tests/test_parsers.py -v`: run focused parser tests.
- `ruff check .`: lint Python code using the configuration in `pyproject.toml`.

## Coding Style & Naming Conventions

Use four-space indentation, snake_case for modules and functions, and PascalCase for classes. Follow existing type annotations and module docstrings. Ruff targets Python 3.11 with a 100-character line limit. Keep provider I/O asynchronous, validate parsed LLM responses before merging content, and place configurable generation parameters in YAML.

## Testing Guidelines

Use pytest and pytest-asyncio; asynchronous tests run with automatic asyncio mode. Name files `test_<module>.py` and functions `test_<behavior>`. Add regression tests for changed parsing, validation, configuration, or generation behavior. Use mock responses, mocked providers, fixed seeds, and `tmp_path` to avoid live services and persistent output. No coverage threshold is configured.

## Commit & Pull Request Guidelines

The short Git history uses descriptive messages such as `Preparing refactoring`; no strict commit format is established. Write concise, action-oriented subjects. PRs should explain the behavior change, link relevant issues, and report validation commands and results. Include screenshots when changing rendered templates.

## Security & Configuration

Keep `OPENAI_API_KEY` and optional `HF_TOKEN` in the ignored `.env` file. Never commit credentials or generated output. Configure ComfyUI endpoints and model filenames through YAML.
