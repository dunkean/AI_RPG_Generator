# Rewrite from Scratch vs. Refactor In-Place

## The Question

Should we archive everything into `/archive` and start a clean repo, reusing only the logic, prompts, and data model? Or should we incrementally refactor the existing codebase?

---

## What's Actually Worth Keeping

Before comparing approaches, let's be honest about what has real value in this project and what doesn't.

**High value — must be preserved regardless of approach:**
- The **pipeline logic** (the 11-step sequential generation concept, the `query`/`generate` pattern, the content-dict accumulation). This is the core intellectual property of the project. It works as a design, and rewriting it from memory would mean reinventing decisions that were already solved.
- The **prompt texts** — they encode months of iteration on what works with LLMs for RPG content. The phrasing, the JSON schemas requested, the context selection (`categories_to_keep`). These are portable: they're just strings, easily copy-pasted into any new structure.
- The **procedural generation algorithms** in `generator.py` — the Gumbel distributions, preferential selection, age-weight mappings, position pools. This is ~300 lines of genuinely sophisticated math that would be painful to reinvent.
- The **data model concepts** from `template.py` — the entity hierarchy, enums, relationship model. Not the code itself (it's 100 lines of basic dataclasses), but the *thinking* behind it.
- The **HTML templates** — functional Jinja2 templates that already render the content dict correctly. Templates are layout, not code; they transfer trivially.
- The **example responses** in `responses.py` — excellent test fixtures.

**Low value — not worth preserving as code:**
- `llm.py` (27 lines of working code, all using a deprecated API — faster to rewrite from scratch)
- `cache.py` (non-functional stub — nothing to preserve)
- `clean_query_manager.py` (90% commented out — essentially blank)
- `name_generator.py` (10 lines wrapping a generic library — trivial to redo)
- `data_formatter.py` (40 lines of dict manipulation — will be replaced by Pydantic)
- `logger.py` (26 lines — `logging` module does this better out of the box)
- `defines.py` (15 lines of constants — will move to config)

**Actively harmful — should be deleted regardless:**
- Hundreds of lines of commented-out code in `clean_prompt.py`, `clean_query_manager.py`, `clean_generation.py`
- The dual codebase (`clean_*` vs legacy) — maintaining both is confusing and neither works alone
- The broken `cache.py` stub that gives the illusion of caching

---

## Option A: Archive and Rewrite

Archive everything into `/archive`. Start fresh with a clean `src/` structure, `pyproject.toml`, modern Python patterns. Port the valuable pieces listed above into the new structure.

### Pros

- **Clean mental model.** No dead code, no "is this the legacy or clean version?", no commented-out blocks. Every file exists because it's needed.
- **Modern foundations from day one.** `pyproject.toml`, proper package structure, `async`/`await`, Pydantic, type hints — baked in rather than retrofitted.
- **No migration tax.** You won't spend time figuring out which version of `query()` to fix, or whether `clean_prompt.py` or `prompt.py` is the source of truth. In a refactor, half the work is untangling the old before you can build the new.
- **The "reusable" parts are small.** The prompts are strings (~200 lines of actual content across both files). The procedural algorithms are ~300 lines. The data model is ~100 lines. The templates are already separate. Total material to port: maybe 600-700 lines of meaningful code, out of 2,885 total lines (most of which are comments, dead code, or broken stubs).
- **Easier to onboard.** If you ever want someone else (or future-you in 2 years) to understand this project, a clean codebase is dramatically easier than one with archaeological layers.

### Cons

- **Risk of losing implicit knowledge.** Some of the "why" behind decisions is embedded in code comments, variable names, and structure. When you rewrite, you might forget edge cases that the original code handled (e.g., the population normalization in `activity_groups`, the filtering of groups with pop <= 3).
- **Temporary productivity dip.** For the first few days, you're building scaffolding (config system, provider abstraction, pipeline orchestrator) before you can generate any content. With a refactor, you could theoretically get *something* running faster.
- **Temptation to over-engineer.** A blank slate invites "let's do it right this time" thinking, which can spiral into building frameworks instead of generating RPG content.

### Risk Mitigation

- Keep `/archive` as a reference, not a graveyard. You'll actively read from it while building the new code.
- Write a `PORTING_CHECKLIST.md` before starting: every algorithm, every prompt, every edge case that must survive the rewrite.
- Set a hard rule: no abstractions until you need them. Build the OpenAI provider first. Add the provider abstraction *when* you actually add a second provider.

---

## Option B: Incremental Refactor

Work within the existing codebase. Fix bugs, complete the clean pipeline, delete legacy files, modernize dependencies one at a time.

### Pros

- **Something runs sooner.** You could fix the 7 known bugs, uncomment the LLM init, implement `query()`, and have the first 4 pipeline steps working within a day.
- **Lower risk of losing edge cases.** You're modifying code that (once) worked, so implicit behaviors are preserved.
- **No context switch.** You stay in the same files, same patterns, same variable names.

### Cons

- **The existing code fights you.** The clean pipeline is ~40% complete and internally inconsistent (key mismatches, missing functions, broken imports). "Completing" it means debugging someone else's half-finished refactor — which is often harder than starting fresh.
- **Commented-out code is cognitive poison.** `clean_prompt.py` is 572 lines of which 411 are comments/blanks. `clean_query_manager.py` is 90% dead code. You'll constantly wonder "should I uncomment this or rewrite it?" — and the answer is almost always rewrite.
- **You inherit architectural debt.** The threading model in `clean_query_manager.py` (global mutable `patches`, `threads`, `lock`, `stop_queue`) is a bad pattern. Refactoring it into async is harder than writing async from scratch.
- **You'll end up rewriting most of it anyway.** The LLM layer must be rewritten (deprecated API). The cache must be rewritten (non-functional). The query manager must be rewritten (commented out). The name generator must be rewritten (wrong library). 6 prompts must be rewritten (commented out). That's... almost everything.
- **Dual codebase confusion persists.** Until you delete all legacy files, every `grep` returns two results, every concept has two implementations, and the mental overhead is real.

---

## My Recommendation: Archive and Rewrite

Here's my honest assessment as someone who's just read every line of this codebase:

**This is a ~2,900-line project where ~1,800 lines are dead, broken, or duplicated.** The living, valuable code is roughly:
- ~200 lines of prompt text (portable strings)
- ~300 lines of procedural algorithms (pure math, no dependencies on broken infrastructure)
- ~100 lines of data model concepts (will be rewritten as Pydantic anyway)
- ~100 lines of HTML templates (already separate)
- ~50 lines of parser logic (worth preserving)

That's ~750 lines of real value. Everything else — the LLM wrapper, the cache, the query manager, the generation orchestrator, the config, the logging — needs to be rewritten regardless of which approach you choose, because the underlying technologies have changed (openai v1.x, async, Pydantic, Flux/ComfyUI).

**The question isn't "rewrite vs refactor." It's "rewrite while staring at the old code, or rewrite while tripping over the old code."** Archiving gives you the former. Refactoring gives you the latter.

### Suggested Approach

```
1. mkdir /archive && mv *.py /archive/ && mv templates/ /archive/
   (keep .git history intact — the old code is always recoverable via git)

2. Create clean project structure:
   pyproject.toml
   config/default.yaml
   src/pipeline.py          # Port the 11-step logic from clean_generation.py
   src/providers/openai.py  # Fresh openai v1.x, ~50 lines
   src/prompts/             # Copy prompt strings from clean_prompt.py + prompt.py
   src/procedural/          # Port algorithms from generator.py
   src/models/              # Pydantic models inspired by template.py
   src/image/               # New ComfyUI + Flux.1 integration
   templates/               # Copy back from archive unchanged

3. Build incrementally:
   - Get bootstrap → details → workplaces running first (3-4 prompts, pure LLM)
   - Add procedural population (port the Gumbel/preferential logic)
   - Add remaining LLM steps one by one
   - Add image generation last (requires ComfyUI setup)
```

### Key Principle: Port, Don't Reinvent

The rewrite doesn't mean "forget everything and start from zero." It means "build a clean house and move the good furniture in." Every prompt, every algorithm, every template gets deliberately evaluated and ported. The difference is you're putting them into a structure that works, instead of trying to fix a structure that was abandoned mid-construction.

### One Caveat

If you have very limited time and just want to *generate some content now* with better models, there's a pragmatic middle ground: fix the 7 bugs, swap `gpt-3.5-turbo` for `gpt-4o-mini`, update the openai import, and implement a minimal `query()` function. That's maybe 2 hours of work and gets you running (steps 1-4 at least). You could do this *before* the rewrite to validate that the prompts still produce good output with modern models, then archive and rewrite with confidence.

---

## Summary Table

| Factor | Archive + Rewrite | Incremental Refactor |
|--------|-------------------|---------------------|
| Time to first output | Longer (days) | Shorter (hours) |
| Time to full modernization | **Shorter** | Longer (fighting old code) |
| Risk of losing edge cases | Moderate (mitigated by /archive) | Low |
| Risk of over-engineering | Moderate | Low |
| Final code quality | **High** | Medium (archaeological layers) |
| Mental overhead | **Low** (clean slate) | High (dual codebases, dead code) |
| Motivation/momentum | **High** (fresh start energy) | Low (debugging old code is draining) |
| Amount of actual reuse | ~750 lines ported | ~750 lines kept + ~2,000 lines deleted |

**Bottom line:** The project is small enough that a rewrite is cheap, and broken enough that a refactor is expensive. Archive and rewrite.
