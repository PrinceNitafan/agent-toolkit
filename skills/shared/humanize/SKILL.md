---
name: humanize
description: "Audit and sanitize documentation, commit messages, prose, and source code comments to strip synthetic AI phrasing, enforce strict ASCII typography, and remove redundant syntax narration. Trigger with /humanize."
---

# Engineering Prose & Comment Sanitizer (`/humanize`)

Goal: ensure all technical documentation, architecture blueprints, commit messages, non-technical prose, and source comments read as direct human-authored work with zero synthetic phrasing or forbidden Unicode punctuation.

## 1. Character & Typography Invariants
1. **ASCII Hyphen Only (`U+002D`)**:
   - Use only the standard ASCII hyphen-minus (`-`).
   - Strip all Unicode dash variants: em dash (`U+2014`), en dash (`U+2013`), figure dash (`U+2012`), horizontal bar (`U+2015`), and minus sign (`U+2212`).
   - Do not replace em dashes with spaced hyphens (` - `) as a drop-in habit. Restructure parenthetical clauses using commas, colons, parentheses, or separate sentences:
     - *Bad*: `The worker caches the token in memory - avoiding repeated disk reads - until the session expires.`
     - *Good*: `The worker caches the token in memory until the session expires, avoiding repeated disk reads.`
2. **Straight ASCII Quotes Only**:
   - Use straight double (`"`) and single (`'`) quotes across all markdown, code, and configuration files.
   - Strip smart/curly quotes (`U+2018`, `U+2019`, `U+201C`, `U+201D`).

## 2. Source Code Comment Discipline
1. **Delete Syntax Narration**:
   - Remove comments that restate what types, function signatures, or control flow already express (for example, `# loop through users`, `// return response`, or boilerplate docstrings/Doxygen blocks that repeat parameter names without adding constraints).
2. **Keep Only High-Signal Engineering Context**:
   - **General Software (Python, TypeScript, Go, Rust)**: Document non-obvious business invariants, API/protocol quirks, concurrency ordering, or why an alternative algorithm was rejected.
   - **Systems & C++23 / CMake**: Document ownership and lifetime preconditions (why a `std::span` or reference remains valid), alignment/ABI assumptions, `noexcept` / `std::expected` error contracts, or `SYSTEM` header isolation workarounds.
   - **Data Pipelines (PySpark / SQL)**: Document why a specific partition count, broadcast threshold, or Arrow `@pandas_udf` boundary was chosen, or why an upstream schema field requires explicit casting.
3. **Comment Formatting**:
   - Keep inline comments to 1 to 2 direct sentences. Never use Unicode dashes or conversational filler inside source files.

## 3. Prose Density & Vocabulary Rules
1. **Cut Synthetic Vocabulary**:
   - Remove banned filler words and transitions: `delve`, `delving`, `tapestry`, `testament`, `landscape`, `pivotal`, `beacon`, `foster`, `streamline`, `dive deep`, `diving deep`, `seamless`, `multifaceted`, `holistic`, `crucial`, `furthermore`, `moreover`, `it is important to note`, and `it is worth noting`.
2. **Lead with Concrete Mechanics**:
   - Replace vague claims ("provides high performance and clean modularity") with falsifiable facts ("avoids extra allocations via `std::span<const std::byte>`", "validates payloads at startup with Pydantic", or "pushes predicate filtering into the Catalyst plan").
3. **Break Formulaic Symmetry**:
   - Avoid giving every bullet point an identical sentence length or opening structure. Use tables for multi-dimensional comparisons, numbered lists for ordered procedures, and short paragraphs for explanations.
   - Cut introductory throat-clearing ("In this document, we will explore...") and summary paragraphs that repeat the top of the file.

## 4. Audit & Verification Workflow
When invoked on a file, diff, or directory:
1. **Scan & Rewrite**:
   - Replace forbidden Unicode dashes and curly quotes with ASCII equivalents.
   - Rewrite any prose containing banned vocabulary or repetitive bullet templates.
   - Strip redundant code comments while preserving invariant explanations.
2. **Verify Cleanliness**:
   - Run the bundled sanitizer script against the target file or directory in the active environment shell (WSL2 `bash` or Windows PowerShell):
     ```bash
     python3 ~/.gemini/config/skills/humanize/scripts/check_content.py <path> --fix
     ```
   - When working inside `agent-toolkit` itself, also run:
     ```bash
     python3 deploy/deploy.py --check --repo-only --fix
     ```
     (and `python3 deploy/deploy.py --check --sync-permissions` after deploying) to confirm zero content or drift violations before completing the task.
