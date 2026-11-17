# PySpark & Conda Reference Blueprint

Canonical `conda-forge` environment, explicit `StructType` schema module, Catalyst transformation, and local `SparkSession` fixture for WSL2 (`ext4`) or native local data pipelines.

## 1. Conda Environment Specification (`environment.yml`)

```yaml
name: spark-pipeline
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python=3.12
  - openjdk=17
  - pyspark=3.5.*
  - pyarrow>=15.0
  - pandas>=2.2
  - pytest>=8.0
  - ruff
  - mypy
```

## 2. Explicit Schema & Pure Transformation (`src/pipeline/telemetry.py`)

```python
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, LongType, StringType, StructField, StructType

TELEMETRY_INPUT_SCHEMA = StructType([
    StructField("device_id", StringType(), nullable=False),
    StructField("event_ts_ms", LongType(), nullable=False),
    StructField("latency_ms", DoubleType(), nullable=True),
])

TELEMETRY_SUMMARY_SCHEMA = StructType([
    StructField("device_id", StringType(), nullable=False),
    StructField("sample_count", LongType(), nullable=False),
    StructField("max_latency_ms", DoubleType(), nullable=False),
])


def summarize_valid_telemetry(raw_df: DataFrame, min_latency_ms: float = 0.0) -> DataFrame:
    # Filter in Catalyst before aggregation to drop corrupt negative readings early
    valid_df = raw_df.filter(
        F.col("latency_ms").isNotNull() & (F.col("latency_ms") >= F.lit(min_latency_ms))
    )
    return (
        valid_df.groupBy("device_id")
        .agg(
            F.count(F.lit(1)).cast(LongType()).alias("sample_count"),
            F.max("latency_ms").cast(DoubleType()).alias("max_latency_ms"),
        )
    )
```

## 3. Local `SparkSession` Fixture (`tests/conftest.py`)

```python
from collections.abc import Iterator
from pathlib import Path

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark(tmp_path_factory: pytest.TempPathFactory) -> Iterator[SparkSession]:
    scratch_dir: Path = tmp_path_factory.mktemp("spark_local")
    session = (
        SparkSession.builder.master("local[2]")
        .appName("pipeline-unit-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.local.dir", str(scratch_dir))
        .getOrCreate()
    )
    yield session
    session.stop()
```
