# Prow Audit Agent - Technical Overview

## Architecture

The tool implements a two-phase analysis pipeline with sophisticated context management and database-driven aggregation.

### Core Components

1. **Log Parser** - Discovers and streams Prow log files
2. **Audit Agent** - Orchestrates the analysis pipeline
3. **SQLite Database** - Persistent storage for analysis results
4. **MCP Server** - Database query interface for aggregation and interactive querying
5. **Report Generator** - Markdown report generation

### Technology Stack

- **LLM Integration**: DSPy + OpenAI SDK for LLM interactions
- **Database**: SQLAlchemy + SQLite for structured storage

---

## Log Processing Detail

### Directory Structure

Prow logs follow this structure:

```
<JOB_NAME>/
  <BUILD_NUMBER>/
    finished.json              # Run-level metadata
    artifacts/
      <STAGE_NAME>/
        finished.json          # Stage-level metadata
        <STEP_NAME>/
          build-log.txt        # Step logs
          finished.json        # Step-level metadata
          sidecar-logs.json    # Optional sidecar logs
```

### LLM Analysis

Each failed step is analyzed using DSPy's ChainOfThought module. The LLM receives the sampled log context and returns a structured analysis containing:

- **Status**: FAILURE, ERROR, TIMEOUT, etc.
- **Analysis**: Natural language explanation of what went wrong
- **Root Cause**: Concise statement of the fundamental issue
- **Error Category**: network, resource, compilation, runtime, etc.
- **Failure Type**: build, test, timeout, infrastructure, configuration
- **Confidence**: 0.0-1.0 score representing analysis certainty
- **Needs Search**: Boolean indicating if web search would help

The output is normalized to a standardized taxonomy and stored in the database.

---

## MCP Server Architecture

The MCP server serves two purposes:

### 1. Internal Query Interface (Phase 2)

During report generation, the MCP server is used to query the database for aggregated statistics. The available query functions retrieve specific data:

- `get_root_cause_distribution` - Retrieve top failure root causes with occurrence counts (with optional semantic clustering)
- `get_error_category_breakdown` - Get failure distribution by category
- `get_step_failure_analysis` - Find which steps fail most frequently
- `get_stage_statistics` - Stage-level success/failure rates

These queries provide aggregated insights from the step-level analyses stored during Phase 1, enabling comprehensive reporting without re-analyzing logs.

### 2. External Interactive Interface (Post-Analysis)

After the audit completes, users can configure MCP clients to query the database interactively by adding the MCP server to their client configuration. This enables ad-hoc queries like "Show me all timeout failures in the e2e-tests stage" without re-running the analysis.

### MCP Server Tools

The `DatabaseAnalyticsServer` exposes these analytical methods:

| Tool | Purpose | Returns |
|------|---------|---------|
| `get_root_cause_distribution` | Distribution of root causes | Cause frequencies (with optional semantic clustering) |
| `get_error_category_breakdown` | Breakdown by error category | Category percentages |
| `get_step_failure_analysis` | Most frequently failing steps | Steps with root cause details |
| `get_stage_statistics` | Per-stage success/failure rates | Stage-level aggregations |
| `get_run_details` | Detailed run information | Full run breakdown |
| `find_similar_failures` | Find steps with similar characteristics | Matching step analyses |
| `analyze_trends` | Temporal failure rate analysis | Failure rates over time |
| `correlate_failures` | Find co-occurring failures | Failure correlations |

---

## Semantic Clustering

The tool supports semantic clustering to group similar root causes. For example, three different descriptions like "DNS resolution failed for api.ci.openshift.org" (330 occurrences), "Cannot resolve DNS for api server" (98 occurrences), and "DNS lookup timeout for API endpoint" (49 occurrences) can be clustered into a single group "DNS resolution failures affecting API servers" (477 total occurrences).

This uses sentence-transformers to compute embeddings and clusters via cosine similarity, reducing noise and highlighting true patterns. The clustering threshold (default 0.65) controls how similar root causes must be to group together.

This feature is controlled via CLI flags `--semantic-clustering` / `--no-semantic-clustering` and `--similarity-threshold`.

---


## Data Flow Diagram

```
┌──────────────┐
│  Prow Logs   │
│ (File System)│
└──────┬───────┘
       │
       │ ProwStructureParser
       │ (discovers runs/stages/steps)
       ▼
┌──────────────────┐
│ Run/Stage/Step   │  LogStreamParser
│   Metadata       │  (streams logs)
└────────┬─────────┘         │
         │                   │
         │                   ▼
         │          ┌─────────────────┐
         │          │  Log Context    │
         │          │ (head/tail/     │
         │          │  errors/samples)│
         │          └────────┬────────┘
         │                   │
         └──────┬────────────┘
                │
                │ DSPy ChainOfThought
                │ (LLM analysis)
                ▼
        ┌───────────────┐
        │  SQLite DB    │
        │               │
        │ • Runs        │
        │ • Stages      │
        │ • Steps       │◄──────┐
        │ • Analyses    │       │
        └───────┬───────┘       │
                │               │ Statistical queries
                │               │ (aggregation)
                ▼               │
        ┌───────────────┐       │
        │  MCP Server   │───────┘
        │ (Analytics)   │
        └───────┬───────┘
                │
                │ Aggregated statistics
                ▼
        ┌──────────────────┐
        │ Report Generator │
        │ • audit_report.md│
        │ • usage_report.md│
        └──────────────────┘
```
