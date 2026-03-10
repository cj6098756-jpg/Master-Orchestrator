# Master Orchestrator

A multi-agent orchestration system powered by the Claude Agent SDK. Decomposes complex objectives into specialist agent tasks, iteratively refines results using Ralph Wiggum loops, and executes actionable findings through a worker agent pool.

## Architecture

```
User Input (CLI / Dashboard)
      |
      v
 MasterOrchestrator (Tier 0)
      |
      +-- Phase 1: ANALYSIS (Ralph Wiggum Loop)
      |     |
      |     +-- TaskParser ---- decomposes objective into subtasks
      |     +-- Tier 1 Dispatch -- 8 specialist agents (research, engineering, etc.)
      |     +-- Evaluate -------- check confidence, identify gaps
      |     +-- Tier 2 Dispatch -- 8 niche specialists (security, API design, etc.)
      |     +-- Synthesize ------ combine findings into 10-section report
      |     +-- Iterate --------- feed synthesis back, refine until complete
      |     +-- Output: OrchestrationResult (structured analysis)
      |
      +-- Phase 2: EXECUTION (new)
            |
            +-- ExecutionPlanner -- converts recommended_next_steps into WorkerTasks
            +-- AgentPool --------- concurrent worker dispatch (semaphore-controlled)
            +-- ExecutionEngine --- wave-based execution with dependency tracking
            +-- Output: ExecutionPlan with completed task results
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/cj6098756-jpg/Master-Orchestrator.git
cd Master-Orchestrator
pip install -e ".[dashboard]"

# Run an analysis
orchestrate run "Build a REST API for task management"

# Full pipeline: analyze + execute
orchestrate execute "Build a user authentication system" --auto

# Launch the dashboard
streamlit run dashboard/app.py
```

### Prerequisites

- Python 3.10+
- Claude Code CLI installed
- `ANTHROPIC_API_KEY` environment variable set

## CLI Commands

| Command | Description |
|---------|-------------|
| `orchestrate run "objective"` | Run analysis only (Ralph Wiggum loop) |
| `orchestrate execute "objective"` | Analyze + plan + execute tasks |
| `orchestrate resume <session-id>` | Resume a previous session |
| `orchestrate sessions` | List saved sessions |
| `orchestrate agents --tier 1` | List available agents |
| `orchestrate status` | Check system configuration |

### CLI Flags

```bash
orchestrate run "objective" \
  --max-iterations 5 \       # Max Ralph Wiggum loop iterations
  --model opus \              # Model override (opus/sonnet/haiku)
  --completion-promise "DONE" # Exact string match to stop loop
  --output-format json \      # Output format (markdown/json)
  --cwd /path/to/project \    # Working directory for agents
  --verbose                   # Enable verbose logging

orchestrate execute "objective" \
  --auto \                    # Auto-approve execution plan
  --max-iterations 3 \        # Analysis iterations
  --model sonnet              # Model override
```

## Agent Catalog

### Tier 1 -- Specialists (8 agents)

| Key | Name | Use Case |
|-----|------|----------|
| `research` | Research Specialist | Web research, evidence synthesis |
| `data_analyst` | Data Analyst | Statistical analysis, pattern identification |
| `product_strategy` | Product Strategist | Product design, market analysis |
| `systems_architect` | Systems Architect | Architecture, system design |
| `engineering` | Engineering Lead | Implementation planning, code design |
| `risk_analyst` | Risk Analyst | Risk assessment, threat modeling |
| `workflow` | Workflow Specialist | Process design, automation |
| `synthesis` | Synthesis Specialist | Cross-domain integration |

### Tier 2 -- Niche Specialists (8 agents)

| Key | Name | Escalated From |
|-----|------|----------------|
| `api_design` | API Design Specialist | systems_architect, engineering |
| `security` | Security Specialist | risk_analyst, engineering |
| `frontend_arch` | Frontend Architect | systems_architect |
| `database_schema` | Database Designer | systems_architect, data_analyst |
| `prompt_engineering` | Prompt Engineer | research, synthesis |
| `devops` | DevOps Specialist | engineering, workflow |
| `testing` | Testing Specialist | engineering |
| `documentation` | Documentation Specialist | synthesis |

## How It Works

### Phase 1: Analysis (Ralph Wiggum Loop)

1. **Parse**: Decomposes objective into a TaskPlan with agent assignments
2. **Dispatch Tier 1**: Sends subtasks to specialist agents via Claude Agent SDK
3. **Evaluate**: Checks confidence levels and escalation signals
4. **Dispatch Tier 2**: Escalates to niche specialists where gaps exist
5. **Synthesize**: Combines all findings into a 10-section structured report
6. **Check Completion**: Stops when quality threshold met or max iterations reached
7. **Iterate**: Feeds synthesis back as context for next refinement pass

### Phase 2: Execution

1. **Plan**: Converts `recommended_next_steps` from the analysis into structured `WorkerTask` objects
2. **Assign**: Maps each task to the most appropriate agent using keyword matching or Claude-powered assignment
3. **Execute**: Dispatches tasks in waves, respecting dependency ordering and concurrency limits
4. **Track**: Monitors completion, handles failures, cancels blocked tasks

### Escalation Routing

Agents report confidence levels (0.0-1.0) and can flag `escalation_used=true`. When confidence drops below the threshold (default 0.8), the system automatically routes to Tier 2 specialists via the `escalation_from` mapping in `agents.toml`.

The P0 bug fix ensures escalation routing uses canonical registry keys (`agent_key`) rather than display names (`agent_name`), with a 3-strategy resolution: direct key match, display name lookup, and fuzzy containment.

## Configuration

### `config/default.toml`

```toml
[models]
primary = "sonnet"       # Tier 0 orchestrator
tier1   = "sonnet"       # Tier 1 specialists
tier2   = "haiku"        # Tier 2 niche specialists

[ralph_loop]
max_iterations    = 5
quality_threshold = 0.8

[execution]
max_concurrent_tasks = 3
max_waves            = 10
worker_max_turns     = 15
```

### `config/agents.toml`

Define custom agents with TOML configuration. Each agent specifies a name, description, prompt, tools, and escalation routing.

## Dashboard

A Streamlit-based UI for visual orchestration management.

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

**Pages:**
- **Run Orchestration** -- Text input, config controls, run button
- **Session Explorer** -- Browse and resume saved sessions
- **Agent Registry** -- View all agents with escalation maps
- **System Status** -- Config display, connection checks

## Project Structure

```
src/master_orchestrator/
  orchestrator/       # Core loop, synthesizer, task parser
  agents/             # Registry, factory, dispatch
  execution/          # Planner, pool, engine (NEW)
  models/             # AgentReport, OrchestrationResult, WorkerTask
  prompts/            # System prompt templates
  session/            # Save/load/resume sessions
  logging/            # Structured logging
  hooks/              # SDK hooks for observation
  cli.py              # CLI entry point
  config.py           # TOML config loading

config/
  default.toml        # Default settings
  agents.toml         # Agent definitions (Tier 1 + Tier 2)

dashboard/            # Streamlit UI
tests/                # Test suite (56 tests)
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT
