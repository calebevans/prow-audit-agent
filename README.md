## Features

- **Automated Log Analysis**: Uses LLMs to analyze step logs and identify failure root causes
- **Semantic Clustering**: Groups similar root causes together to identify dominant failure patterns
- **Multi-Provider LLM Support**: Works with OpenAI, Anthropic, Ollama, and other LLM providers
- **Web Search Integration**: Uses DuckDuckGo to research unfamiliar errors
- **MCP Database Server**: Provides an MCP server for interactive querying of audit results
- **Comprehensive Reports**: Generates detailed markdown reports with statistics and insights
- **Usage Tracking**: Tracks LLM usage, token consumption, and estimated costs
- **Docker Support**: Runs in containers for consistent deployment

## Architecture

The tool implements a streamlined analysis pipeline:

### Phase 0: Pre-filtering
- Scans all runs and identifies failures by checking `finished.json` files
- Filters to analyze only failed runs (efficiency optimization)

### Phase 1: Log Processing
- Uses LLM to analyze each failed step
- Optionally enriches analysis with web search
- Stores results in SQLite database

### Phase 2: Report Generation
- Queries database for aggregated statistics
- Gets root cause distribution with optional semantic clustering
- Gets error category breakdown and step failure analysis
- Creates comprehensive markdown reports
- Produces usage tracking reports
- Packages everything in a tarball

## Installation

### Prerequisites

- Python 3.11 or higher
- Podman or Docker (optional, for containerized deployment)

### Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd prow-audit-agent

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks (for development)
pre-commit install
```

### Container Installation

```bash
# Build the audit agent image
podman build -t prow-audit-agent .
```

## Configuration

### Environment Variables

The tool requires the following environment variables:

```bash
# Required
export LLM_PROVIDER=openai          # openai, anthropic, azure, ollama, etc.
export LLM_API_KEY=your-api-key     # API key for the provider
export LLM_MODEL=gpt-4              # Model name (e.g., gpt-4, claude-3-5-sonnet)

# Optional
export LLM_BASE_URL=http://...      # For local/custom LLM endpoints
export LLM_TEMPERATURE=0.1          # Temperature setting (default: 0.1)
export LLM_MAX_TOKENS=4000          # Max tokens per response (default: 4000)
```

### Supported LLM Providers

- **OpenAI**: gpt-4, gpt-3.5-turbo, etc.
- **Anthropic**: claude-3-5-sonnet, claude-3-opus, etc.
- **Azure OpenAI**: Compatible with OpenAI models on Azure
- **Ollama**: For local models (llama2, mistral, etc.)
- **OpenRouter**: Access to multiple models
- **Custom**: Any OpenAI-compatible API

## Usage

### Basic Usage

```bash
# Analyze all stages
prow-audit --log-path /path/to/logs --output-path ./results

# Analyze specific stage
prow-audit --log-path /path/to/logs --stage appstudio-e2e-tests

# Custom database location
prow-audit --log-path /path/to/logs --database ./audit.db
```

### Container Usage

```bash
# Using podman-compose
export LLM_PROVIDER=openai
export LLM_API_KEY=your-key
export LLM_MODEL=gpt-4
export LOG_PATH=/path/to/logs
export OUTPUT_PATH=./results

podman-compose up

# Using podman directly
podman run -v /path/to/logs:/data/logs:ro \
           -v ./results:/data/results \
           -e LLM_PROVIDER=openai \
           -e LLM_API_KEY=your-key \
           -e LLM_MODEL=gpt-4 \
           prow-audit-agent \
           --log-path /data/logs \
           --output-path /data/results
```

### CLI Options

```
Options:
  --log-path PATH                      Path to the directory containing Prow logs [required]
  --output-path PATH                   Path to store analysis results (default: ./results)
  --stage TEXT                         Optional: Specific stage name to analyze
  --database PATH                      Path to SQLite database file
  --report-only                        Only regenerate reports from existing database
  --semantic-clustering / --no-semantic-clustering
                                       Use semantic similarity to group related failures (default: enabled)
  --similarity-threshold FLOAT         Cosine similarity threshold for clustering (default: 0.65)
  --version                            Show version and exit
  --help                               Show help message and exit
```

## Directory Structure

The tool expects Prow logs in the following structure:

```
logs/
├── <PR #>/
│   └── <JOB NAME>/
│       └── <BUILD #>/
│           ├── finished.json (run-level)
│           └── artifacts/
│               └── <STAGE NAME>/
│                   ├── finished.json (stage-level)
│                   └── <STEP NAME>/
│                       ├── build-log.txt
│                       ├── finished.json
│                       └── sidecar-logs.json (optional)
```

## Output

The tool generates the following outputs:

### 1. Audit Report (`audit_report.md`)
- Executive summary
- Overall statistics
- Top root causes (with semantic clustering)
- Error category breakdown
- Most frequently failing steps

### 2. Usage Report (`usage_report.md`)
- LLM call statistics
- Token usage
- Cost estimates
- Tool usage (web searches)

### 3. SQLite Database (`prow_audit.db`)
- Runs, stages, and steps
- Step analyses with root causes
- Audit metadata for statistics

### 4. Tarball (`prow_audit_results.tar.gz`)
- Contains all outputs for easy distribution

## MCP Server for Interactive Queries (Optional)

After running an audit, you can optionally set up an MCP server to interactively query the audit database using Cursor or Claude Desktop. **This is not required to run audits** - the audit tool generates complete reports automatically.

### Available Tools

- `get_root_cause_distribution`: Get distribution of root causes with optional semantic clustering
- `get_error_category_breakdown`: Get failure distribution by category
- `get_step_failure_analysis`: Find which steps fail most frequently
- `get_stage_statistics`: Per-stage success/failure rates
- `get_run_details`: Detailed information about specific runs
- `find_similar_failures`: Find steps with similar characteristics
- `analyze_trends`: Temporal analysis of failure rates
- `correlate_failures`: Find co-occurring failures
- `export_data`: Export filtered data

### Setup

#### Option 1: Container (Recommended)

This is the easiest and most portable setup method. Works with Podman or Docker.

**1. Build the MCP server image:**

```bash
make build-mcp
```

**2. Configure Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "prow-audit-db": {
      "command": "podman",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/absolute/path/to/prow_audit.db:/data/prow_audit.db:ro",
        "prow-audit-mcp:latest",
        "--database",
        "/data/prow_audit.db"
      ]
    }
  }
}
```

#### Option 2: Local Python

If you prefer not to use containers:

**1. Install dependencies:**

```bash
cd /path/to/prow-audit-agent
pip install -r requirements.txt
```

**2. Configure Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "prow-audit-db": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp.database_server",
        "--database",
        "/absolute/path/to/prow_audit.db"
      ],
      "cwd": "/absolute/path/to/prow-audit-agent",
      "env": {
        "PYTHONPATH": "/absolute/path/to/prow-audit-agent"
      }
    }
  }
}
```
