---
name: tech-docs
description: "Author and refactor technical documentation (README, SPEC, AGENTS.md, architecture blueprints, and operational runbooks) with result-first structure, Diataxis scope discipline, single-source-of-truth file:// links, and executable commands. Trigger with /tech-docs."
---

# Technical Documentation & Runbook Standard (`/tech-docs`)

Goal: produce dense, maintainable engineering documentation where every page has one clear job, commands execute cleanly in the target shell, and implementation facts link to source files rather than duplicating them.

## 1. Scope & Document Classification (Diataxis)
Before drafting or editing a markdown file, identify the reader and classify the page's single responsibility:
1. **Runbook / How-To**: Ordered, copy-pasteable shell commands to finish a build, test, deployment, or operational task, paired with expected verification output.
2. **Architecture Blueprint / Explanation**: Module boundary contracts, data flow, ownership/lifetime rules, and explicit trade-offs (for example, `~/.gemini/config/skills/cxx-tdd-loop/references/cxx23-cmake-blueprint.md` or `~/.gemini/config/skills/pyspark-tdd-loop/references/pyspark-conda-blueprint.md`).
3. **Reference Specification**: Exhaustive CLI flags, configuration keys, data schemas, or API tables (`~/.gemini/GEMINI.md`, `AGENTS.md`).
4. **Tutorial / Quickstart**: Minimal end-to-end onboarding steps to get a repository running for the first time.

Do not mix introductory tutorials, architecture rationales, and reference tables in the same section. Look for an existing document first and update it in place instead of creating a parallel file.

## 2. Structural & Prose Rules
1. **Result-First Opening**:
   - State what the system or procedure accomplishes in the first 1 to 2 sentences.
   - Omit conversational preambles ("This document describes...", "Welcome to...").
   - Write in active voice, present tense, and second person ("Run X", not "We will run X").
2. **Executable Commands Over Prose**:
   - Show the exact `python3`, `python`, `uv`, `pytest`, `npm`, `cmake`, `ctest`, or `conda` command block rather than describing flags in paragraphs.
   - Include expected output or pass criteria next to non-trivial verification commands.
   - Use paths and shell invocations matching the target environment (native Linux paths in `bash` for WSL2/hybrid setups; native Windows paths in PowerShell for standalone Windows setups).
   - Put preconditions before the action: *"If the virtual environment does not exist, create it with:"* rather than *"Create the virtual environment if it does not exist."*
3. **Single Source of Truth**:
   - Link directly to source modules, schemas, build manifests, and scripts using clickable `file://` links.
   - Never copy volatile lists (flags, dependencies, schema fields, or version numbers) into multiple documents when a link to the authoritative source file suffices.
   - Delete stale text outright instead of leaving outdated sections with deprecation notes.
4. **Formatting Discipline**:
   - Use numbered lists only for sequential execution steps; use bullets for unordered lists.
   - Use tables when comparing 3 or more options across shared attributes.
   - Keep headings in concise title or sentence case without decorative emojis.

## 3. Verification & Hygiene Gate
1. **Reader Execution Check**:
   - Confirm a developer can finish the task using only the documented commands from the repository root without guessing working directories or active environments, and cut anything a reader can infer directly from source files.
2. **Sanitize & Validate**:
   - Apply `/humanize` to strip Unicode dashes (`U+2014`, `U+2013`), smart quotes, and banned AI filler phrases.
   - When editing inside `agent-toolkit`, run:
     ```bash
     python3 deploy/deploy.py --check --repo-only
     ```
     (or `python3 deploy/deploy.py --check` when verifying deployed targets) to verify frontmatter, typography, buzzwords, and repo/deployed links.
