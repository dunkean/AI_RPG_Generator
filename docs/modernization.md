# TTRPG Content Generator — Modernization Document

## Table of Contents

- [Part 1: Current State Analysis](#part-1-current-state-analysis)
  - [1.1 Project Overview](#11-project-overview)
  - [1.2 Dual Codebase Situation](#12-dual-codebase-situation)
  - [1.3 Generation Pipeline](#13-generation-pipeline)
  - [1.4 LLM Layer](#14-llm-layer)
  - [1.5 Prompt System](#15-prompt-system)
  - [1.6 Parsing and Validation](#16-parsing-and-validation)
  - [1.7 Procedural Generation](#17-procedural-generation)
  - [1.8 Name Generation](#18-name-generation)
  - [1.9 Image Generation](#19-image-generation)
  - [1.10 Output System](#110-output-system)
  - [1.11 Data Model](#111-data-model)
  - [1.12 Configuration](#112-configuration)
  - [1.13 Known Bugs and Issues](#113-known-bugs-and-issues)
  - [1.14 Code Quality Assessment](#114-code-quality-assessment)
- [Part 2: Modernization Recommendations](#part-2-modernization-recommendations)
  - [2.1 LLM Layer Modernization](#21-llm-layer-modernization)
  - [2.2 Image Generation Modernization](#22-image-generation-modernization)
  - [2.3 Data Model and Validation](#23-data-model-and-validation)
  - [2.4 Configuration Management](#24-configuration-management)
  - [2.5 Async Support](#25-async-support)
  - [2.6 Caching System](#26-caching-system)
  - [2.7 Error Handling and Logging](#27-error-handling-and-logging)
  - [2.8 Testing Strategy](#28-testing-strategy)
  - [2.9 Dependency Management](#29-dependency-management)
- [Part 3: Phased Implementation Plan](#part-3-phased-implementation-plan)
  - [Phase 0 — Make It Run](#phase-0--make-it-run)
  - [Phase 1 — Make It Whole](#phase-1--make-it-whole)
  - [Phase 2 — Make It Clean](#phase-2--make-it-clean)
  - [Phase 3 — Make It Fast and Beautiful](#phase-3--make-it-fast-and-beautiful)
  - [Phase 4 — Make It Reliable](#phase-4--make-it-reliable)
- [Part 4: Technology Decision Tables](#part-4-technology-decision-tables)
  - [4.1 LLM Provider Comparison](#41-llm-provider-comparison)
  - [4.2 Image Generator Comparison](#42-image-generator-comparison)
  - [4.3 Content Dict vs Dataclasses](#43-content-dict-vs-dataclasses)
- [Part 5: Target File Organization](#part-5-target-file-organization)

---

## Part 1: Current State Analysis

### 1.1 Project Overview

The TTRPG Content Generator is a Python tool that procedurally generates rich content for tabletop RPGs — communities, NPCs, factions, workplaces, architecture — by combining LLM queries (OpenAI GPT) with algorithmic population generation and AI image generation (Stable Diffusion). The final output is an HTML document with NPC portraits, building illustrations, and detailed narrative, exportable to PDF.

The core idea is sound and the pipeline design is elegant: a central `content` dictionary accumulates data through sequential `query()` (LLM) and `generate()` (procedural) steps, each adding a new layer of detail. The prompts are well-crafted, the procedural population system uses realistic statistical distributions, and the output templates are functional.

However, the project is in a **broken mid-refactoring state** with outdated dependencies and significant incomplete work.

### 1.2 Dual Codebase Situation

Two parallel codebases exist, neither fully functional on its own:

**Legacy pipeline** (complete but outdated):
- `prompt.py` — all 11 prompt functions, fully working
- `query.py` — `LLM_Query` class with caching and retry logic
- `generator.py` — sophisticated procedural generation (571 lines)
- `data_formatter.py` — response formatting and content bootstrapping
- Executed via `generator.ipynb` notebook

**Clean/refactored pipeline** (incomplete):
- `clean_generation.py` — main entry point, 11-step pipeline defined but broken
- `clean_prompt.py` — only 5 of 11 prompts implemented (rest commented out)
- `clean_procedural.py` — simplified procedural generation (lost sophistication from legacy)
- `clean_query_manager.py` — ~90% commented out, `query()` and `generate()` don't exist
- `validator.py` — only 5 of 11 validators implemented
- `responses.py` — hardcoded example responses (useful for testing)

The clean pipeline cannot run: `query()` and `generate()` functions are undefined, the LLM is never initialized (commented out), and most prompts/validators are missing.

### 1.3 Generation Pipeline

The pipeline runs sequentially, building up the `content` dict through 11 stages:

```
Step  1: Bootstrap (LLM)         → name, keywords, structure, culture, customs, goals, resources, etc.
Step  2: Details x6 (LLM)       → expanded text for customs, resources, history, timeline, sites, anecdotes
Step  3: External Influences (LLM) → neighboring factions/entities with relationships
Step  4: Workplaces (LLM, table) → activity groups as markdown table (name, type, population, etc.)
Step  5: Population (procedural) → social groups + NPC generation with weighted distributions
Step  6: Population Details (LLM) → enriches each group's members with traits, descriptions
Step  7: Employees (procedural)  → assignment of NPCs to workplaces
Step  8: Employee Details (LLM)  → enriches workplace roles with job descriptions
Step  9: Workplace Details (LLM) → site descriptions, customs, internal plots
Step 10: Architecture (LLM)      → visual/architectural descriptions of locations
Step 11: Key Figures (LLM)       → detailed bios for important NPCs
      -------
Step 12: Portrait generation (Stable Diffusion) — commented out
Step 13: Building generation (Stable Diffusion) — commented out
Step 14: HTML rendering (Jinja2) — commented out
Step 15: PDF export — commented out
```

**Core pattern:**
- `query(name, content, prompts, parser, validator)` — sends prompt(s) to LLM, parses response (JSON or table), validates, and patches into `content`
- `generate(name, content, generator_func)` — runs procedural generation function and patches results into `content`
- `update_dict(original, update)` — recursive deep merge of patches into content dict

This pattern is clean and should be preserved.

### 1.4 LLM Layer

**`llm.py`** — LLM wrapper:
- Uses **deprecated** `openai.ChatCompletion.create()` API (pre-1.0 openai library)
- Default model: **`gpt-3.5-turbo`** (now significantly outclassed)
- Parameters: temperature=0.9, presence_penalty=0.6, top_p=1
- No retry logic, basic `except Exception` that prints and returns `None`
- Has a commented-out `@backoff` decorator suggesting retry was planned

**`query.py`** (legacy) — query management:
- `LLM_Query` class with dual-layer caching:
  - **Hash cache**: MD5 hash of prompt text → cached response file
  - **Project cache**: `{project_id}_{query_type}_{timestamp}` → human-readable cache with most-recent retrieval
- Retry logic: up to 3 retries with 15-second delays if parsing fails
- Cache stored in `cache/gpt-3.5-turbo/` as plain text files

**`clean_query_manager.py`** (clean) — entirely non-functional:
- `query()` and `generate()` are commented out (~90 lines)
- Only `update_dict()` and `update_list()` work (recursive dict merging)
- Design included threading/queue worker but was never completed

**`cache.py`** — non-functional stub:
- `hasCache()` returns `None` (just `pass`)
- `getCache()` and `setCache()` are commented out

### 1.5 Prompt System

**`clean_prompt.py`** (clean, partially implemented):

| Prompt | Status | Description |
|--------|--------|-------------|
| `bootstrap()` | Implemented | Generates name, keywords, structure, culture, etc. |
| `detail()` | Implemented | Expands category keywords into long-form titled paragraphs |
| `description()` | Implemented | Creates short (50-word) and long descriptions |
| `external_influences()` | Implemented | Generates neighboring factions with relationships |
| `activity_groups()` | Implemented | Generates workplaces as markdown table |
| `population()` | **Missing** | Commented out (~40 lines) |
| `employees()` | **Missing** | Commented out |
| `workplace_details()` | **Missing** | Commented out |
| `architecture_and_poi()` | **Missing** | Commented out |
| `workplace_sites()` | **Missing** | Commented out |
| `key_figure()` | **Missing** | Commented out |

All 11 prompts exist in legacy `prompt.py` and work. The clean versions add a smart `context_json()` helper that selectively includes only relevant prior generation results (via a `categories_to_keep` mapping), minimizing token usage.

Prompts request JSON or markdown table output. Some include inline comment syntax (`// description`) which requires the custom `strip_json_comments()` parser.

**`prompt.py`** (legacy, complete):
- All 11 prompts fully functional
- Includes `prompt_people_in_groups()`, `prompt_workplace_employees()`, `prompt_workplace_details()`, `prompt_architecture_and_sites()`, `prompt_sites()`, `prompt_member_details()`
- Some procedural generation functions are mixed in (code organization issue)

### 1.6 Parsing and Validation

**`parsers.py`** — two parsers for LLM responses:

- `parse_json(raw_data)`: strips `//` and `/* */` comments via regex, extracts first `{` to last `}`, tries `json.loads()`, falls back to `ast.literal_eval()`, returns `None` on failure (silent)
- `parse_table(raw_data)`: splits markdown tables on `|`, extracts headers and values, attempts int/float conversion and recursive JSON parsing in cells, returns `None` on failure (silent)
- `strip_json_comments(json_text)`: regex-based comment removal preserving quoted strings

Both parsers **silently swallow errors** — they catch exceptions, print them, and return `None`. This makes debugging extremely difficult.

**`validator.py`** — transforms parsed responses into "patches":

| Validator | Status | What it does |
|-----------|--------|-------------|
| `bootstrap()` | Implemented | Extracts setting keywords, normalizes category format |
| `descriptions()` | Implemented | Adds ordering, wraps in `details` key |
| `detail()` | Implemented | Wraps values in `{"descriptions": v}` |
| `external_influences()` | Implemented | Creates shortuuid-keyed groups with hierarchical structure |
| `activity_groups()` | Implemented | Normalizes population (scales to match target), filters groups with pop <= 3 |
| Population validators | **Missing** | — |
| Employee validators | **Missing** | — |
| Workplace validators | **Missing** | — |
| Architecture validators | **Missing** | — |
| Key figure validators | **Missing** | — |

### 1.7 Procedural Generation

**`clean_procedural.py`** (clean, simplified):
- `population(content)`: generates social groups using weighted random choices across 7 types (family, friends, colleagues, allies, strangers, common goal, common status)
- `populate(content, group, group_id)`: creates individual NPCs with race, gender, position, beauty, IQ
- Uses Gumbel distribution for group sizes (realistic long tail)
- Group type weights differ for local vs foreign NPCs (families dominant locally)
- `activity_members()`: stub with TODO comments about BERT embeddings — never implemented
- No seed initialization despite TODO comment

**`generator.py`** (legacy, sophisticated — 571 lines):
- `family_distribution()`: Gumbel distribution with loc=7, scale=3 for family sizes
- `outsiders_distribution()`: Gumbel with loc=2, scale=1 for smaller outsider groups
- `get_family_members()` / `get_outsider_members()`: detailed member generation with age-appropriate positions and pool depletion
- `preferential_group_selection()` / `preferential_individual_selection()`: sophisticated weighted selection considering composition (natives/mix/outsiders), type, ages, and structure preference
- `age_weights_per_situations`: ~60 situation-to-age-category mappings (e.g., "father" weights toward mid/old, "son" toward young)
- **This sophistication was lost in the clean rewrite** — should be ported back

### 1.8 Name Generation

**`name_generator.py`** (clean — 10 lines):
- Thin wrapper around generic `names` library
- Returns plain English names regardless of race
- No fantasy naming support

**Legacy** (in `generator.py`):
- Uses `pynames` library with specific generators per race:
  - Human: `CaspianMidlunderSuleseFullnameGenerator`
  - Elf: `DnDNamesGenerator`
  - Dwarf: `DwarfFullnameGenerator`
  - Halfling: `ThurianMorridaneFullnameGenerator`
  - Gnome: `IossanNyssFullnameGenerator`
- Gender-aware name generation via `GENDER.MALE`/`GENDER.FEMALE`

The clean pipeline lost race-appropriate fantasy names — a significant quality regression.

### 1.9 Image Generation

**`openpose_db/poses_generator.py`** — portrait generator:
- Uses `webuiapi` library connecting to Stable Diffusion WebUI at `127.0.0.1:7860`
- Model: **`dreamlikeDiffusion10_10.ckpt`** (Stable Diffusion 1.5 era, circa 2022)
- Resolution: 512x768 (portrait format)
- Sampler: DPM++ 2S a Karras, CFG=6, 15 steps, batch_size=5
- Generates combinatorial portraits: 3 heights x 4 weights x 4 races x 9 ages x 2 genders = 864 base variations
- Prompt template: `"fine art painting, heroic fantasy, full body, frontal view of a ((single)) {race} {gender}, {height}, ({age}) and {weight}, simple dark outfit, casual pose, white gradient background, realistic"`
- Has commented-out ControlNet/OpenPose support
- **Completely disconnected from main pipeline** (runs standalone)

**`render.py`** — contains a single hardcoded SD prompt string, not used anywhere.

Output from prior runs exists in `output/Enclave/portraits/` (~60 JPGs) and `output/Enclave/sites/` (~20 JPGs), confirming the system worked at some point.

### 1.10 Output System

**HTML templates** (in `templates/`):
- `place.html` / `pdf.html`: Jinja2 templates rendering the content dict to rich HTML
- Features: side navigation, NPC grid with portraits (576x768), workplace sections with site images (1024x768), group membership lists
- `index.html`: overview page linking to multiple generated places with image slideshows
- `style.css`: shared styles (also duplicated inline in templates)
- Templates reference `npc.img_path`, `site_value.img_path` — expect image paths in content dict

**Generated output** (from prior runs in `output/Enclave/`):
- `global.json`, `web.json`: full content data
- `index.html`, `local_index.html`: rendered HTML
- Large PDFs (5-50 MB): `Aurwyn's Sanctuary.pdf`, `Avalon's Watch.pdf`, `Crystalhold.pdf`

### 1.11 Data Model

**`template.py`** — aspirational dataclass model:
- `Entity`, `Group`, `Person`, `Lore`, `Description` dataclasses
- Enums: `EnumType` (Individual, Community, Work Group...), `EnumStructure` (hierarchy, democracy...), `EnumRelation`, `EnumScale`
- Supports relationships, hierarchical nesting, descriptions with keywords
- **Not used anywhere in the pipeline** — entirely disconnected

**Actual data model**: nested `content` dict accumulated through pipeline stages:
```python
{
    "project_id": "...",
    "generation": {"seed": 42, "instruction": "..."},
    "setting": {"description": "...", "type": "...", "keywords": [...]},
    "details": {
        "type": "...", "scale": "...", "population": N,
        "name": "...", "keywords": [...], "structure": "...",
        "culture": {"keywords": [...], "descriptions": {...}},
        "external_influences": {"keywords": [...], "groups": {uuid: {...}}},
        ...
    },
    "groups": {
        "activity": {uuid: {"name": "...", "population": N, ...}},
        "social": {uuid: {"origin": "...", "type": "...", "members": [uuid, ...]}}
    },
    "npcs": {uuid: {"full_name": "...", "race": "...", "gender": "...", ...}}
}
```

### 1.12 Configuration

All configuration is hardcoded at the top of `clean_generation.py`:
```python
PROJECT_ID = "Enclave"
LORE = """Medieval fantasy world..."""
GROUP_DESCRIPTION = """Deep within mountains..."""
WORLD_TYPE = "Medieval fantasy"
SCALE = "local"
TYPE = "small community"
POPULATION = 80
SEED = 42
RACE_RATIO = {"human": 0.6, "half-elf": 0.15, "elf": 0.05, "dwarf": 0.15, "halfling": 0.025, "gnome": 0.025}
```

Constants in `defines.py`:
```python
LLM_QUERY_DELAY = 30  # seconds between queries
MEAN_GROUP_SIZE = 7
GROUP_CATEGORIES = ["culture", "customs", "goals", "resources", "history", ...]
```

No configuration file system exists. Changing generation parameters requires editing Python source code.

### 1.13 Known Bugs and Issues

1. **Folder creation bug** (`clean_generation.py` line 57): `Path(os.path.join(folder, PROJECT_ID, folder))` creates paths like `output/Enclave/output` instead of `output/Enclave`
2. **Cache is non-functional**: `cache.py` has `hasCache()` that returns `None`, all other functions commented out
3. **LLM never initialized**: `clean_generation.py` lines 64-65 are commented out — pipeline has no LLM
4. **`query()` and `generate()` don't exist**: `clean_query_manager.py` has them entirely commented out — pipeline crashes immediately with `NameError`
5. **Content key mismatch**: `clean_prompt.py:bootstrap()` references `setting["description"]` but `clean_generation.py` initializes it as `setting["bootstrap_description"]`
6. **Duplicate dict keys**: `clean_procedural.py` position pools have duplicate keys (e.g., `"grandfather": 0.2` twice) — Python silently uses last value
7. **Silent parser failures**: both `parse_json` and `parse_table` catch all exceptions and return `None` without logging

### 1.14 Code Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Functionality | 2/10 | Cannot run: missing functions, LLM not initialized, broken imports |
| Architecture | 6/10 | Good separation of concerns, clean pipeline pattern, but incomplete |
| Prompt Quality | 7/10 | Well-structured prompts with good context management |
| Procedural Gen | 7/10 | Realistic distributions (legacy), but simplified in clean version |
| Error Handling | 2/10 | Silent failures, bare `except`, no logging |
| Testing | 0/10 | No test suite at all |
| Documentation | 3/10 | Some comments and TODOs, `CLAUDE.md` exists |
| Code Reuse | 3/10 | Significant duplication between legacy and clean |
| Type Safety | 2/10 | `template.py` defines types but pipeline ignores them |
| Dependencies | 2/10 | No `requirements.txt` or `pyproject.toml`, deprecated APIs |

---

## Part 2: Modernization Recommendations

### 2.1 LLM Layer Modernization

**Problem**: Uses deprecated `openai.ChatCompletion.create()` with `gpt-3.5-turbo` — a 2023-era API and model that is vastly outperformed by current options at lower cost.

**Recommendation**: Multi-provider abstraction with OpenAI GPT-4o-mini as default.

**Why GPT-4o-mini as default:**
- Cheaper than GPT-3.5-turbo was ($0.15/1M input tokens vs $1.50)
- Significantly better at structured output (JSON mode, tool use)
- Better prompt following, fewer parsing failures
- Estimated cost for full community generation (~80 NPCs): $0.05-0.15 per run

**Implementation:**

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class LLMProvider(ABC):
    @abstractmethod
    async def query(self, system: str, prompt: str,
                    response_model: type[BaseModel] | None = None) -> str | BaseModel:
        ...

class OpenAIProvider(LLMProvider):
    # Uses openai>=1.0: client.chat.completions.create()
    # Supports response_format={"type": "json_object"}
    # Supports structured output via tool use / function calling

class AnthropicProvider(LLMProvider):
    # Claude API — excellent for creative writing (key figure bios, descriptions)

class OllamaProvider(LLMProvider):
    # Local models (llama3, mistral) — free, offline, good for dev/testing
```

**Structured output strategy:**
- Use OpenAI's JSON mode for all JSON-format steps (bootstrap, details, external influences, workplace details, architecture, key figures)
- Define Pydantic models for expected response schemas — use as both validation and documentation
- Migrate table-format prompts (workplaces, population details, employee details) to JSON — tables are fragile and unnecessary with modern models
- Keep `parse_table()` as a legacy fallback only

**Retry strategy:**
- Use `tenacity` library: exponential backoff, 3 retries, random jitter
- Replace the legacy 15-second flat sleep (wasteful)

### 2.2 Image Generation Modernization

**Problem**: Stable Diffusion 1.5 with `dreamlikeDiffusion10_10.ckpt` at 512x768 produces dated, inconsistent results. The `webuiapi` library ties the project to A1111 WebUI.

**Recommendation**: ComfyUI backend with Flux.1-dev model.

**Why Flux.1-dev:**
- Generational leap over SD 1.5 in coherence, anatomy, and prompt following
- Native 1024x1536 resolution (4x the pixel count)
- Much better face generation — critical for NPC portraits
- Free and open source (non-commercial license for dev, schnell variant is Apache 2.0)
- Active development by Black Forest Labs

**Why ComfyUI over WebUI:**
- Node-based workflow system — workflows are JSON files, easy to version and parameterize
- Better programmatic API for automation
- More actively maintained for modern models (Flux, SD3, etc.)
- Supports ControlNet, IP-Adapter, and other consistency tools natively

**Implementation approach:**
1. Create a `ComfyUIClient` class that submits workflow JSONs via REST API and retrieves results
2. Design template workflows as ComfyUI-exported JSON files (`portrait_workflow.json`, `building_workflow.json`)
3. Parameterize workflows dynamically: swap prompts, seeds, model references
4. Build portrait prompts from NPC attributes (race, age, gender, build, occupation, personality)
5. Use IP-Adapter for visual consistency within families/factions

**Portrait prompt improvement** (current → proposed):
```
# Current (generic, hardcoded)
"fine art painting, heroic fantasy, full body, frontal view of a ((single)) {race} {gender},
{height}, ({age}) and {weight}, simple dark outfit, casual pose, white gradient background"

# Proposed (dynamic, attribute-driven)
"Portrait of {name}, a {age_desc} {race} {gender}, {build_desc}. {occupation} in {community_name}.
{personality_visual_cues}. {clothing_style} appropriate for {setting_type}.
Painterly style, warm lighting, detailed face, fantasy illustration."
```

### 2.3 Data Model and Validation

**Problem**: `template.py` defines a full dataclass model that's never used. The pipeline operates on untyped nested dicts with no validation. LLM responses are parsed but never validated for completeness or correctness.

**Recommendation**: Hybrid approach — keep content dict as pipeline accumulator, add Pydantic models at I/O boundaries.

**Why not replace the content dict entirely:**
- The `update_dict()` patch-based pattern works well for incremental accumulation
- Full object-graph migration mid-refactoring is high risk for little immediate gain
- Pydantic at boundaries gives 80% of the benefit at 20% of the effort

**Where to add Pydantic models:**
1. **LLM response validation**: define a model per pipeline step, validate immediately after parsing
2. **Configuration validation**: project config, provider config
3. **Final output**: serialize content dict to validated model before rendering

```python
class BootstrapResponse(BaseModel):
    name: str
    keywords: list[str] = Field(min_length=5, max_length=15)
    structure: Literal["despotism", "hierarchy", "democracy", "anarchy", "autonomous groups"]
    prosperity: Literal["poor", "low", "medium", "high", "wealthy"]
    culture: list[str] = Field(min_length=3)
    customs: list[str] = Field(min_length=3)
    goals: list[str] = Field(min_length=3)
    resources: list[str] = Field(min_length=3)
    history: list[str] = Field(min_length=3)
    timeline: list[str] = Field(min_length=3)
    sites: list[str] = Field(min_length=3)
    anecdotes: list[str] = Field(min_length=3)
    races: dict[str, float]  # Must sum to ~1.0
    member_bonds: dict[str, float]

class NPC(BaseModel):
    full_name: str
    first_name: str
    last_name: str
    race: str
    gender: Literal["male", "female"]
    age_category: Literal["infant", "child", "teenager", "young_adult", "adult", "middle_aged", "senior", "elderly", "ancient"]
    position: str
    beauty: float = Field(ge=0, le=10)
    iq: float = Field(ge=0, le=10)
```

### 2.4 Configuration Management

**Problem**: All generation parameters are hardcoded in `clean_generation.py`. Changing anything requires editing Python source.

**Recommendation**: YAML configuration files with Pydantic validation.

**Why YAML:**
- Human-readable and supports comments (unlike JSON)
- Natural for RPG-adjacent configuration (lore blocks, race ratios)
- Standard in Python ecosystem for configuration

**Proposed structure:**
```
config/
    default.yaml            # Default generation parameters
    projects/
        enclave.yaml        # Project-specific overrides
        rust_riders.yaml
    providers/
        openai.yaml         # LLM provider config (model, temperature, etc.)
        comfyui.yaml        # Image gen config (host, workflows, etc.)
```

**Example project config:**
```yaml
project_id: "Enclave"
seed: 42

setting:
  type: "Medieval fantasy"
  lore: |
    A medieval fantasy world where magic is rare but present.
    Various races coexist in scattered settlements.

community:
  type: "small community"
  scale: "local"
  population: 80
  description: |
    Deep within the heart of the Ironspine Mountains lies a secluded
    dwarven mining community, hidden from the outside world...
  races:
    human: 0.6
    half-elf: 0.15
    elf: 0.05
    dwarf: 0.15
    halfling: 0.025
    gnome: 0.025

generation:
  llm_provider: "openai"
  llm_model: "gpt-4o-mini"
  image_provider: "comfyui"
  image_model: "flux1-dev"
  temperature: 0.9
  max_retries: 3
```

### 2.5 Async Support

**Problem**: The pipeline makes many independent LLM calls sequentially with a 30-second delay between each. Generating 6 detail categories, N workplace details, and N employee details takes a very long time.

**Recommendation**: `async`/`await` for LLM calls, sync for procedural generation.

**Where async helps most:**
- Step 2 (Details): 6 independent LLM calls → `asyncio.gather()` with semaphore
- Step 6 (Population Details): N groups, each needing an LLM call
- Step 8 (Employee Details): N workplaces, each needing an LLM call
- Step 9 (Workplace Details): N workplaces
- Step 11 (Key Figures): N key NPCs

**Expected speedup**: 5-10x for LLM-heavy steps (from sequential to parallel with rate limiting).

**Procedural generation stays synchronous** — it's CPU-bound, completes in milliseconds, and doesn't benefit from async.

### 2.6 Caching System

**Problem**: Clean pipeline has no working cache. Legacy has a working dual-layer cache that should be adapted.

**Recommendation**: Rebuild file-based caching with clear directory structure.

```
cache/
    {project_id}/
        {step_name}/
            {hash}.json       # Cached LLM response
            {hash}.meta.json  # Prompt hash, timestamp, model, temperature
```

- Cache key: MD5 of `(prompt_text + model_name + temperature)`
- Support cache invalidation per step or per project
- Add `--no-cache` CLI flag for forced re-generation
- Cache hits should log a message so users know when cached data is used

### 2.7 Error Handling and Logging

**Problem**: Silent failures throughout (parsers return `None`, LLM errors print and continue), no structured logging.

**Recommendation:**
- Replace all `print()` with Python `logging` module (or `rich` for console output)
- Parsers should raise specific exceptions (`ParseError`, `ValidationError`) instead of returning `None`
- LLM calls should use `tenacity` retry with structured error reporting
- Each pipeline step should log: step name, start/end time, cache hit/miss, token usage, success/failure
- Add `rich` progress bars for long-running steps

### 2.8 Testing Strategy

**Problem**: Zero tests exist. LLM-dependent code is expensive and non-deterministic to test.

**Recommendation**: Layered testing with mocked LLM responses.

| Layer | What | How |
|-------|------|-----|
| Unit | Parsers, validators, procedural gen, name gen, config loading | Fixed inputs, deterministic (set seed) |
| Integration | Full pipeline with mocked LLM | Use `responses.py` data as fixtures, mock `LLMProvider.query()` |
| Snapshot | Content structure after each step | Compare against known-good JSON snapshots |
| E2E (optional) | Full pipeline with real LLM | Small population (5 NPCs), run manually |

**Framework**: `pytest` with `pytest-asyncio` for async tests.

### 2.9 Dependency Management

**Problem**: No `requirements.txt` or `pyproject.toml`. Dependencies are implicit.

**Recommendation**: `pyproject.toml` with dependency groups.

```toml
[project]
name = "ttrpg-content-generator"
version = "0.2.0"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
    "pydantic>=2.0",
    "numpy>=1.24",
    "pynames>=0.4",
    "shortuuid>=1.0",
    "jinja2>=3.1",
    "pyyaml>=6.0",
    "tenacity>=8.0",
    "httpx>=0.25",
    "rich>=13.0",
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.30"]
image = ["Pillow>=10.0", "requests>=2.31"]
fow = ["opencv-python>=4.8", "keyboard>=0.13"]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "ruff>=0.1"]
```

---

## Part 3: Phased Implementation Plan

### Phase 0 — Make It Run

> Get the existing pipeline running end-to-end with modern dependencies, without changing architecture.

**Tasks:**
1. Create `pyproject.toml` with all dependencies
2. Fix the 7 known bugs (Section 1.13)
3. Upgrade `llm.py` from deprecated `openai.ChatCompletion.create()` to openai v1.x (`client.chat.completions.create()`)
4. Switch default model from `gpt-3.5-turbo` to `gpt-4o-mini`
5. Implement a simple synchronous `query()` and `generate()` in `clean_query_manager.py` (remove threading/queue complexity)
6. Implement basic file-based `cache.py` based on the legacy `query.py` pattern
7. Verify the pipeline produces valid `content.json` output for the first 4 steps (bootstrap → details → external influences → workplaces)

**Key files:**
- `llm.py` — OpenAI v1.x migration
- `clean_query_manager.py` — implement working `query()` / `generate()`
- `cache.py` — implement file-based caching
- `clean_generation.py` — fix bugs, uncomment LLM init

**Exit criteria:** Pipeline runs steps 1-4 and produces valid JSON output.

### Phase 1 — Make It Whole

> Complete all missing prompts and validators. Consolidate the two codebases into one. Full end-to-end generation.

**Tasks:**
1. Port remaining 6 prompts from `prompt.py` to `clean_prompt.py`:
   - `population` (people in groups)
   - `employees` (workplace employees)
   - `workplace_details` (site descriptions, customs, plots)
   - `architecture_and_poi` (visual/architectural descriptions)
   - `workplace_sites` (individual site details)
   - `key_figure` (detailed NPC bios)
2. Implement remaining validators in `validator.py`
3. Replace `name_generator.py` with `pynames`-based implementation (port race-specific generators from legacy `generator.py`)
4. Port the sophisticated procedural generation from legacy `generator.py` to `clean_procedural.py`:
   - `preferential_group_selection()` / `preferential_individual_selection()`
   - Age-weight system (`age_weights_per_situations`)
   - Family distribution with proper position pools
5. Integrate HTML rendering (Jinja2 templates) into the pipeline
6. Verify full end-to-end generation matches or exceeds legacy output quality
7. Delete legacy files (`prompt.py`, `query.py`, `generator.py`, `data_formatter.py`)

**Exit criteria:** Full pipeline runs steps 1-15, generates HTML with content, images can be added manually.

### Phase 2 — Make It Clean

> Introduce proper architecture patterns, configuration system, types, and error handling.

**Tasks:**
1. **Configuration system:**
   - Create `config/` directory structure with YAML files
   - Create Pydantic config models with validation
   - Move all hardcoded values from `clean_generation.py` to config files
2. **LLM abstraction layer:**
   - Create provider architecture (`LLMProvider` ABC + `OpenAIProvider`)
   - Add `AnthropicProvider` and `OllamaProvider`
   - Provider selection via configuration
3. **Structured output:**
   - Define Pydantic response models for each pipeline step
   - Use OpenAI JSON mode / structured output
   - Replace fragile `parse_json` + `parse_table` with Pydantic validation
   - Convert table-format prompts to JSON format
4. **Error handling:**
   - Replace silent `None` returns with proper exceptions
   - Add `tenacity` retry with exponential backoff
   - Structured logging with `logging` module (replace `print()`)
   - Add `rich` progress display
5. **Data models:**
   - Create Pydantic models for NPC, Group, Workplace, Community
   - Validate content dict at pipeline checkpoints (after each step)

**Exit criteria:** Pipeline uses config files, structured output, proper logging, retries on failure.

### Phase 3 — Make It Fast and Beautiful

> Add async processing, modern image generation, CLI, and quality improvements.

**Tasks:**
1. **Async LLM queries:**
   - Make `LLMProvider.query()` async
   - Implement batch query with `asyncio.gather()` + semaphore for rate limiting
   - Per-provider rate limiting
2. **Image generation:**
   - Create `ComfyUIClient` class
   - Design Flux.1-dev workflow templates (portrait, building)
   - Dynamic prompt construction from NPC attributes
   - Batch image generation with queue management
   - IP-Adapter integration for family consistency
3. **Prompt quality improvements:**
   - Add few-shot examples in prompts (using `responses.py` data)
   - Chain-of-thought for complex generation (key figures, workplace plots)
   - Temperature tuning per step (lower for structured data, higher for creative content)
   - Model selection per step (e.g., use a stronger model for key figures)
4. **CLI interface:**
   - Create `cli.py` with argparse or click
   - Commands: `generate`, `resume` (from checkpoint), `render`, `cache-clear`
   - Progress bars with `rich`

**Exit criteria:** Pipeline generates full content with images, 5-10x faster for LLM steps, CLI-driven.

### Phase 4 — Make It Reliable

> Add tests, documentation, and polish.

**Tasks:**
1. **Test suite:**
   - Unit tests for parsers, validators, procedural generation, name generation
   - Integration tests with mocked LLM responses
   - Snapshot tests for content structure
   - CI with GitHub Actions
2. **Documentation:**
   - Updated README with installation, usage, configuration guide
   - Architecture diagram
   - Prompt engineering guide (how to customize for different settings)
3. **Output improvements:**
   - Modernize HTML templates (better CSS, responsive design)
   - Extract inline CSS to shared stylesheet
   - Better PDF generation (consider `weasyprint`)
   - JSON export for VTT integration (Foundry VTT, Roll20)
4. **Cleanup:**
   - Remove all commented-out code
   - Remove unused files
   - Move `responses.py` to test fixtures
   - Type hints throughout codebase

**Exit criteria:** Tests pass, documentation complete, clean codebase with no dead code.

---

## Part 4: Technology Decision Tables

### 4.1 LLM Provider Comparison

| Criterion | OpenAI GPT-4o-mini | OpenAI GPT-4o | Claude 3.5 Sonnet | Ollama (local) |
|-----------|-------------------|---------------|-------------------|----------------|
| Quality | Very good | Excellent | Excellent (best prose) | Good |
| Structured Output | Native JSON mode | Native JSON mode | Tool use | Varies |
| Cost / 1M input | ~$0.15 | ~$2.50 | ~$3.00 | Free |
| Speed | Fast | Moderate | Fast | Hardware-dependent |
| Offline | No | No | No | Yes |
| Rate Limits | Generous | Moderate | Moderate | None |
| **Best for** | **Default workhorse** | **Key figures, complex** | **Creative writing** | **Dev/testing** |

**Estimated cost per full generation** (~80 NPCs, ~10 workplaces, ~30 LLM calls):
- GPT-4o-mini: $0.05 - $0.15
- GPT-4o: $0.50 - $2.00
- Claude 3.5 Sonnet: $1.00 - $3.00

### 4.2 Image Generator Comparison

| Criterion | Flux.1-dev + ComfyUI | SDXL + ComfyUI | Flux.1-schnell + ComfyUI | Cloud API (fal.ai) |
|-----------|---------------------|----------------|--------------------------|---------------------|
| Image Quality | Excellent | Very good | Good | Excellent |
| Face Coherence | Excellent | Good | Good | Excellent |
| Resolution | 1024x1536 native | 1024x1536 | 1024x1536 | Varies |
| VRAM Required | 12GB+ | 8GB+ | 8GB+ | None |
| Speed per Image | ~15s | ~8s | ~4s | ~5s |
| Cost | Free (electricity) | Free (electricity) | Free (electricity) | ~$0.003-0.05 |
| ControlNet | Emerging | Mature | Limited | Via API |
| Setup | Moderate | Easy | Easy | Trivial |
| **Best for** | **Production quality** | **Fast iteration** | **Bulk generation** | **No-GPU fallback** |

**Recommendation:** Flux.1-dev for final output quality, with SDXL or Flux.1-schnell as fast alternatives during development.

### 4.3 Content Dict vs Dataclasses

| Approach | Pros | Cons |
|----------|------|------|
| **Keep content dict** (current) | Flexible, easy patching via `update_dict()`, trivial serialization | No type safety, no IDE completion, easy to introduce key typos |
| **Full dataclass migration** | Type safety, IDE support, clear API | Major rewrite risk, breaks patch pattern, rigid structure |
| **Hybrid (recommended)** | Type safety at boundaries, flexible core, incremental | Slight complexity of maintaining both |

**Recommendation:** Hybrid. Keep the content dict as the pipeline accumulator (it works). Add Pydantic models for:
- LLM response validation (immediately after parsing)
- Configuration (project settings, provider config)
- Final output serialization (before rendering to HTML)

This gives 80% of the type safety benefits at 20% of the migration risk.

---

## Part 5: Target File Organization

```
ttrpg_content_generator/
    pyproject.toml
    README.md
    CLAUDE.md
    config/
        default.yaml
        projects/
            example_medieval.yaml
        providers/
            openai.yaml
            comfyui.yaml
    src/
        __init__.py
        cli.py                      # Entry point (argparse/click)
        pipeline.py                 # Pipeline orchestration (was clean_generation.py)
        config.py                   # Configuration loading + Pydantic models
        models/
            __init__.py
            schemas.py              # Pydantic response schemas (per step)
            content.py              # Content dict type annotations
        providers/
            __init__.py
            base.py                 # LLMProvider ABC
            openai_provider.py
            anthropic_provider.py
            ollama_provider.py
        prompts/
            __init__.py
            bootstrap.py
            details.py
            population.py
            workplaces.py
            architecture.py
            key_figures.py
        procedural/
            __init__.py
            population.py          # Social group generation
            names.py               # Fantasy name generation (pynames)
            distributions.py       # Statistical distributions
        parsers/
            __init__.py
            json_parser.py
            table_parser.py         # Legacy fallback
        validators/
            __init__.py
            bootstrap.py
            details.py
            population.py
            workplaces.py
        image/
            __init__.py
            comfyui_client.py
            portrait_generator.py
            building_generator.py
            workflows/
                portrait.json       # ComfyUI workflow template
                building.json
        output/
            __init__.py
            renderer.py            # Jinja2 HTML rendering
            pdf_exporter.py
            json_exporter.py
        cache/
            __init__.py
            file_cache.py
        logging.py
    templates/
        place.html
        pdf.html
        index.html
        style.css
    tests/
        __init__.py
        fixtures/
            mock_responses.py      # From responses.py
            sample_config.yaml
        test_parsers.py
        test_validators.py
        test_procedural.py
        test_pipeline.py
    tools/
        fow.py                     # Fog of war (standalone tool)
    docs/
        modernization.md           # This document
```
