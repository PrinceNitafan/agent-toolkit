---
name: pyspark-tdd-loop
description: "Execute a 5-gate Red-Green-Refactor TDD loop for Conda and PySpark data pipelines using explicit StructType schemas, injected SparkSession fixtures, and Catalyst/Arrow transformations. Trigger with /pyspark-tdd-loop."
---

# Conda & PySpark TDD Execution Loop (`/pyspark-tdd-loop`)

Goal: deliver deterministic, testable PySpark transformations inside a tracked Conda environment through a 5-gate Red -> Green -> Catalyst Refactor loop ([pyspark-conda-blueprint.md](references/pyspark-conda-blueprint.md)).

## Core Conda & PySpark Invariants
- **Conda Environment Discipline**: Manage all Python runtimes, binary wheels, C-extensions, and JVM/Arrow toolchains through `conda` (or `mamba`) backed by a tracked `environment.yml` (`conda-forge`, `nodefaults`). Never install packages into the system Python or `base` Conda environment, and never mix ad-hoc `venv` directories into Conda-managed projects.
- **Explicit Schemas**: Define explicit `StructType` and `StructField` schemas for all data sources and outputs. Never rely on `inferSchema=True` in pipeline or test code.
- **Catalyst & Arrow Execution**: Express transformations with native `pyspark.sql.functions` and `Column` expressions so work stays inside the JVM/Catalyst optimizer. Use typed Arrow `@pandas_udf` functions only when custom vector logic is required; avoid row-by-row Python `@udf` or `.rdd` lambdas.
- **Explicit Session Injection**: Inject `SparkSession` or input `DataFrame` instances into pipeline stages rather than calling `SparkSession.builder.getOrCreate()` inside business logic.

## Gate 1: Verify Environment & Conda Boundaries
1. **Enforce Native Execution Boundaries**:
   - In WSL2/hybrid setups, confirm the repository and `spark.local.dir` scratch paths reside on native `ext4` (`/home/<username>/...`), translate any Windows host dataset paths (`C:\...` or `D:\...`) to `/mnt/c/...` or `/mnt/d/...`, and run `conda`, `python`, `pytest`, and `spark-submit` in WSL2 `bash`.
   - On standalone Windows, run commands in PowerShell inside the Conda environment (`HADOOP_HOME` / `winutils` required only when writing Parquet/Delta outputs locally).
2. **Verify Conda Environment**:
   - Inspect `environment.yml` (`file://` link) to identify the target Conda environment name and pinned `python`, `pyspark`, `pyarrow`, and `pytest` packages.
   - Run all test and linter commands via `conda run -n <env_name> ...`.

## Gate 2: Lock Explicit Schemas & Pure Transformation Contract (Red)
1. **Define Explicit `StructType` Contracts**:
   - Declare input and output `StructType` and `StructField` schemas with explicit nullability (`nullable=False` where required). Never use `inferSchema=True`.
2. **Define Dependency-Injected Transformation Signature**:
   - Accept `DataFrame` (or an explicitly injected `SparkSession` when reading sources) and configuration parameters directly. Never call `SparkSession.builder.getOrCreate()` inside domain transformation functions.
   - Add a minimal stub function so the test module imports cleanly.
3. **Write the Falsifiable `pytest` Case**:
   - Using a lightweight session-scoped local `SparkSession` fixture (`master("local[2]")`, `spark.sql.shuffle.partitions=2`, `spark.ui.enabled=false`), construct small in-memory input rows with explicit schema.
   - Assert exact schema and row equality on the output DataFrame, covering normal records, null/edge cases, and malformed inputs.
4. **Verify the Red State**:
   ```bash
   conda run -n <env_name> pytest -q <path_to_test_file.py> -k "<test_name>"
   ```
   Confirm the test fails on the expected assertion.

## Gate 3: Implement Surgical Catalyst / Arrow Transformation (Green)
1. **Write Catalyst-First Logic**:
   - Express filtering, projections, aggregations, and windowing with native `pyspark.sql.functions` and `Column` expressions.
   - When custom vector logic cannot be expressed in Catalyst SQL functions, use typed Arrow `@pandas_udf` functions rather than row-by-row Python `@udf` or `.rdd` lambdas.
   - Never call `.toPandas()` or `.collect()` inside transformation stages.
2. **Verify the Green State**:
   ```bash
   conda run -n <env_name> pytest -q <path_to_test_file.py>
   ```

## Gate 4: Execution Plan & Hygiene Audit (Refactor)
1. **Inspect Physical Plan & Partition Behavior**:
   - Check that column pruning, predicate pushdown, and join strategies avoid unnecessary full-table shuffles (`df.explain()`).
   - Eliminate intermediate `.cache()` calls unless a DataFrame is consumed by multiple downstream actions and `.unpersist()` is paired explicitly.
2. **Run Full Test Suite**:
   ```bash
   conda run -n <env_name> pytest
   ```

## Gate 5: Report Completion
Output a concise final report (under 8 lines):
- **Result**: Schema contracts and transformation functions implemented (with clickable `file://` links).
- **Verification**: Exact `conda run -n <env_name> pytest` command executed and pass count.
- **Open Decisions**: Any partition-sizing or upstream data-contract questions.
