# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Telegram bot framework for creating training scenarios, currently implementing SPIN sales methodology training. The bot uses LLM providers (OpenAI/Anthropic) to generate training cases, analyze questions, and provide feedback. The key design principle is **domain logic is externalized into scenario configs** - new training bots can be created without code changes.

## Commands

### Development
```bash
# Install dependencies (use Python 3.11)
pip install -r REQUIREMENTS.txt

# Run locally
python bot.py

# Restart bot (Unix)
./restart_bot.sh

# Stop bot (Unix)
./stop_bot.sh
```

### Docker
```bash
# Build
docker build -t spin-bot:v3.0 .

# Run
docker run -d --env-file .env spin-bot:v3.0
```

### Deployment
- **Railway**: Configured via `railway.json`
- Current production uses `versions/v3.0/` as build context
- Health check endpoint available on port 8080 (`/health`)

## Architecture

### Service Layer Pattern
The bot uses a service-oriented architecture with clear separation of concerns:

```
bot.py                      # Telegram handlers only, no business logic
├─ services/
│  ├─ llm_service.py        # LLM provider orchestration (OpenAI/Anthropic)
│  ├─ training_service.py   # Training session coordinator
│  ├─ user_service.py       # User data and statistics
│  └─ achievement_service.py # Badge/achievement logic
├─ engine/
│  ├─ scenario_loader.py    # Load & validate scenario configs
│  ├─ case_generator.py     # Generate training cases (direct, no LLM)
│  ├─ question_analyzer.py  # Classify question types, calculate clarity
│  └─ report_generator.py   # Generate final reports with badges
├─ infrastructure/
│  └─ health_server.py      # HTTP health check server
└─ scenarios/
   ├─ spin_sales/           # Production SPIN scenario
   └─ template/             # Template for new scenarios
```

### LLM Service Architecture
- **Single HTTP/2 client**: Uses `httpx.AsyncClient` with connection pooling for all providers
- **Single OpenAI client**: Reuses the httpx client to avoid connection overhead
- **Three pipelines**: Each has primary + fallback provider:
  - `response`: Client responses during training (gpt-4o-mini → claude-haiku)
  - `feedback`: Mentor feedback (gpt-5-mini → claude-sonnet)
  - `classification`: Question classification (gpt-4o-mini → gpt-4o-mini)
- **Streaming**: Enabled for GPT-4 series and Anthropic; disabled for GPT-5 (per requirements)
- **TTL cache**: Feedback responses cached to prevent duplicate "ДА" (yes) acknowledgments

### Training Flow
1. User starts training → `case_generator` creates case **instantly** (no LLM, uses templates from config)
2. User asks question → `llm_service` generates client response
3. `question_analyzer` classifies question type and calculates clarity points
4. `llm_service` generates mentor feedback (with streaming if supported)
5. After completion → `report_generator` creates final report with badges

### Configuration System
- **Secrets in .env**: Only `BOT_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ADMIN_USER_IDS`
- **App config in code**: `config.py` contains all provider/model routing
- **Domain logic in JSON**: `scenarios/{name}/config.json` contains all training logic

## Scenario Configuration

Scenarios are defined in `scenarios/{scenario_name}/config.json` with these sections:

- `scenario_info`: Metadata (name, version, description)
- `case_variants`: Template data for generating cases (positions, companies, products, problems)
- `messages`: All user-facing text (welcome, progress, completion, errors)
- `prompts`: System prompts for LLM (case generation, client responses, feedback)
- `question_types`: Question classification rules (keywords, clarity points, score multipliers)
- `game_rules`: Session rules (max questions, target clarity, etc.)
- `scoring`: Badge thresholds and names
- `ui`: Progress format, command aliases

**To create a new scenario**: Copy `scenarios/template/`, edit `config.json`, update `config.py` to point to it, restart bot.

## Version Management

- `versions/v1.0/`, `versions/v2.0/`, `versions/v3.0/`: Archived versions (read-only)
- **Active development**: Root directory contains current working code
- Railway deploys from versioned directories (see `railway.json`)

When working on new versions:
1. Make changes in root directory
2. Test locally
3. Update `CHANGELOG.md` and `VERSIONS.md`
4. When ready for production, archive to `versions/vX.Y/`
5. Update `railway.json` build context

## Environment Variables

Required in `.env`:
```bash
BOT_TOKEN=...              # Telegram bot token
OPENAI_API_KEY=...         # Required
ANTHROPIC_API_KEY=...      # Optional (for fallback)
ADMIN_USER_IDS=...         # Optional (comma-separated Telegram IDs for /validate)
```

All other configuration (ports, timeouts, models, providers) is hardcoded in `config.py`.

## Key Implementation Details

### Case Generation
- **v3.0 approach**: Cases generated **instantly** using templates from `case_variants`
- No LLM call needed - randomly combines position, company type, product, and problem
- Recent cases tracked by hash to avoid repetition within 5 cases

### Anti-Duplication
- "ДА" (yes) responses are deduplicated using TTL cache
- Prevents user from spamming acknowledgments for points

### Model Warmup
- On startup, bot preloads LLM connections to reduce first-response latency

### Admin Commands
- `/validate` is restricted to users in `ADMIN_USER_IDS`
- Checks: Uses `update.effective_user.id in config.ADMIN_USER_IDS`

## Telegram Bot Commands

User commands:
- `/start`, `/help`: Welcome and instructions
- `/stats`: User statistics
- `/rank`: Leaderboard
- `/caseinfo`: Current scenario info
- `/author`: Bot author info
- Text commands: "начать", "старт" (start training), "завершить" (complete), "ДА" (yes/acknowledge)

Admin commands:
- `/validate`: Validate scenario configuration (admin-only)

## Common Patterns

### Adding a New Telegram Command
1. Add handler in `bot.py` (async function)
2. Register with `application.add_handler(CommandHandler(...))`
3. Coordinate via `training_service` or `user_service` - **no business logic in bot.py**

### Changing LLM Models
1. Edit `config.py` provider/model constants
2. No code changes needed elsewhere (abstracted by `llm_service`)

### Modifying Training Logic
1. Edit `scenarios/{name}/config.json`
2. Restart bot - no code changes needed

### Adding a New Question Type
1. Add entry to `question_types` array in scenario config
2. Specify: `id`, `name`, `emoji`, `keywords`, `clarity_points`, `score_multiplier`
3. `question_analyzer` uses keywords for classification

## Logging and Monitoring

- Logging via Python `logging` module (INFO level)
- Health check: HTTP server on port 8080 (`/health` endpoint)
- PID file: `bot.pid` created on startup, removed on shutdown

## Notes

- Bot text is in Russian (scenarios, messages, comments)
- Uses `python-telegram-bot==20.7` (async API)
- HTTP/2 enabled for all LLM calls via httpx
- Connection pooling: max 10 connections, 10 keepalive
- Timeout: 30 seconds for LLM calls (configurable in `config.py`)
