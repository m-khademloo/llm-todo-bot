# Feature list → test coverage

Every feature from the docs is covered by at least one test. No rollback of existing tests; only additions.

## Commands (doc 06 – The Only Exceptions)

| Feature | Test file | Test(s) |
|--------|------------|--------|
| `/start` — universal reset, welcome | `test_features_commands.py`, `test_orchestrator.py`, `test_production_bot_wiring.py` | TestStartCommand, test_handle_message_start_*, test_start_command_does_not_require_llm |
| `/help` — show help text | `test_features_commands.py`, `test_i18n_templates_complete.py` | TestHelpCommand, required keys include "help" |
| `/tasks` — shortcut for list tasks | `test_features_commands.py` | TestTasksCommand (get_user_tasks in registry) |
| `/cancel` — cancel flow, clear context | `test_features_commands.py` | TestCancelCommand (clear_conversation_context) |

## Conversation flow patterns (doc 06)

| Feature | Test file | Test(s) |
|--------|------------|--------|
| Pattern 1: Single-turn task creation | `test_features_conversation_flows.py` | TestPattern1SingleTurnTaskCreation |
| Pattern 2: Multi-turn gathering (ask_user, max 3) | `test_features_conversation_flows.py`, `test_tools/test_conversation_tools.py` | TestPattern2MultiTurnGathering, ask_user returns question |
| Pattern 4: Disambiguation | `test_features_disambiguation_and_resume.py` | TestDisambiguation |
| Pattern 5: Confirmation for destructive | `test_features_conversation_flows.py`, `test_safety.py` | TestPattern5ConfirmationFlow |
| Pattern 6: Smalltalk & help | `test_features_conversation_flows.py` | TestPattern6SmalltalkAndHelp |
| Pattern 7: User configuration | `test_features_conversation_flows.py`, `test_tools/test_config_tools.py` | TestPattern7UserConfiguration |
| ReAct resume after ask_user | `test_features_disambiguation_and_resume.py`, `test_state_manager.py` | TestReActResume |

## Task lifecycle (doc 04)

| Feature | Test file | Test(s) |
|--------|------------|--------|
| create_task | `test_tools/test_task_tools.py`, `test_features_conversation_flows.py` | create_task_*, TestPattern1 |
| update_task | `test_tools/test_task_tools.py` | update_task_* |
| complete_task | `test_tools/test_task_tools.py`, `test_features_task_lifecycle.py` | complete_task_*, TestTaskCompletionFlow |
| delete / request_task_deletion (with confirmation) | `test_tools/test_task_tools.py`, `test_features_conversation_flows.py` | request_task_deletion_*, TestPattern5 |
| query_tasks: status pending/done/all, sort, category | `test_tools/test_task_tools.py`, `test_features_task_lifecycle.py` | TestTaskQueryFlow, get_user_tasks_* |
| No tasks message | `test_features_task_lifecycle.py`, `test_features_config_and_errors.py` | TestQueryResultFormatting, TestErrorAndConfusionHandling |
| Category system (6 categories) | `test_features_config_and_errors.py`, `test_db_models.py` | TestCategorySystem |

## Scheduling (doc 05)

| Feature | Test file | Test(s) |
|--------|------------|--------|
| set_reminder (one-shot) | `test_tools/test_scheduling_tools.py`, `test_features_scheduling.py` | TestReminderSystem |
| Due-date alert (job type) | `test_features_scheduling.py` | TestDueDateAlert |
| Recurring (daily, weekly, monthly) | `test_features_scheduling.py`, `test_scheduling_recurring.py` | TestRecurringTasks |
| Quiet hours | `test_features_scheduling.py`, `test_tools/test_config_tools.py`, `test_db_models.py` | TestQuietHours, test_update_user_config_quiet_hours |

## Config & i18n (doc 06)

| Feature | Test file | Test(s) |
|--------|------------|--------|
| Config fields: language, timezone, priority_prompt, default_category, notification_enabled, quiet_hours | `test_features_config_and_errors.py`, `test_tools/test_config_tools.py` | TestConfigFields |
| update_user_config key/value | `test_features_config_and_errors.py` | TestConfigFields |
| Error/confusion: error_generic, error_rate_limit, no_tasks | `test_features_config_and_errors.py`, `test_production_security.py` | TestErrorAndConfusionHandling |
| Templates fa/en, detect_language, PRIORITY_EMOJI | `test_utils_i18n.py`, `test_i18n_templates_complete.py` | various |

## Tools (doc 02 – Tool Registry)

| Tool | Test file |
|------|-----------|
| get_current_datetime | `test_tools/test_datetime_tools.py` |
| get_user_tasks | `test_tools/test_task_tools.py`, `test_features_task_lifecycle.py` |
| create_task | `test_tools/test_task_tools.py` |
| update_task | `test_tools/test_task_tools.py` |
| complete_task | `test_tools/test_task_tools.py` |
| request_task_deletion | `test_tools/test_task_tools.py`, `test_features_conversation_flows.py` |
| calculate_priority | `test_tools/test_priority_tools.py` |
| get_user_config | `test_tools/test_config_tools.py` |
| update_user_config | `test_tools/test_config_tools.py`, `test_features_config_and_errors.py` |
| set_reminder | `test_tools/test_scheduling_tools.py`, `test_features_scheduling.py` |
| ask_user | `test_tools/test_conversation_tools.py`, `test_features_conversation_flows.py`, `test_features_disambiguation_and_resume.py` |

## Security & production

| Feature | Test file |
|--------|-----------|
| User isolation, confirmation, rate limit, no secret leak, prompt injection | `test_production_security.py`, `test_user_isolation.py`, `test_safety.py` |
| Task limit, error handling, main/bot wiring, DB TTL | `test_production_*.py`, `test_db_*.py` |

All of the above are covered; no feature from the doc list is missing a test.
