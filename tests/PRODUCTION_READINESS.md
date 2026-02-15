# Production Readiness Checklist

**If all tests in `tests/` pass, the following production requirements are covered by the test suite.**

## What the tests guarantee

| Area | Tests | Meaning |
|------|--------|--------|
| **Security** | `test_production_security.py`, `test_user_isolation.py`, `test_safety.py` | User isolation (every query scoped to `user_id`), destructive actions require confirmation, rate limiting, no tool definitions in user-facing templates, user message in separate role (prompt injection protection) |
| **Task limit** | `test_production_task_limit.py`, `test_config.py` | `MAX_TASKS_PER_USER` is defined and can be enforced by `create_task` |
| **Error handling** | `test_production_orchestrator_errors.py`, `test_tool_executor*.py` | Unknown tool → error dict; orchestrator returns string (no crash); max iterations → friendly message |
| **DB** | `test_db_database.py`, `test_db_models.py`, `test_production_db_ttl.py` | CRUD, conversation context, history, jobs; TTL index on history (30 days) |
| **Entry point** | `test_production_main_wiring.py`, `test_main.py` | `src.main` and `main()` exist; config loads from env |
| **Bot wiring** | `test_production_bot_wiring.py` | Orchestrator has `handle_message(user_id, message)`; `create_bot(token, orchestrator)`; `/start` uses static welcome (no LLM) |
| **Tools & ReAct** | `test_tools/*`, `test_orchestrator.py`, `test_state_manager.py`, `test_tool_registry.py` | All tools registered; tools and state save/resume behave as specified |

## Before going to production (not fully testable by unit/integration tests)

1. **E2E**: Run `pytest -m e2e` with real LLM and test MongoDB (create task, query, complete, delete with confirmation).
2. **Docker**: `docker-compose up` and send `/start` and a few messages from Telegram; confirm bot responds.
3. **Secrets**: Ensure `TELEGRAM_BOT_TOKEN` and any LLM API keys are in `.env` only, never committed.
4. **MongoDB**: In production, enable MongoDB authentication and use a non-default `MONGO_URI`.
5. **Rate limit**: Confirm middleware or orchestrator calls `safety.check_rate_limit` before handling each message and returns the rate-limit template when over limit.

## Running the full suite

```bash
# All tests (exclude E2E by default)
pytest tests/ -v

# Exclude only E2E placeholders
pytest tests/ -v -m "not e2e"
```

**Conclusion: Passing the full test suite (excluding optional E2E) means the Telegram bot logic, security, and wiring are ready for production, provided the steps above are also done before deploy.**
