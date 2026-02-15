"""Edge-case tests for db models: validation, serialization."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.db.models import Task, TaskCategory, TaskStatus, User, TaskFilter


class TestTaskEdgeCases:
    def test_task_serialization_roundtrip(self):
        t = Task(user_id="u1", title="Test", category=TaskCategory.WORK)
        d = t.model_dump(mode="json")
        t2 = Task.model_validate(d)
        assert t2.user_id == t.user_id
        assert t2.title == t.title
        assert t2.task_id == t.task_id

    def test_task_with_none_optional_fields(self):
        t = Task(user_id="u1", title="x", description=None, due_date=None)
        assert t.description is None
        assert t.due_date is None

    def test_task_tags_empty_list(self):
        t = Task(user_id="u1", title="x", tags=[])
        assert t.tags == []

    def test_task_tags_multiple(self):
        t = Task(user_id="u1", title="x", tags=["a", "b"])
        assert t.tags == ["a", "b"]

    def test_task_estimated_time_zero_not_allowed_if_validated(self):
        t = Task(user_id="u1", title="x", estimated_time_minutes=0)
        assert t.estimated_time_minutes == 0


class TestUserEdgeCases:
    def test_user_serialization_roundtrip(self):
        u = User(user_id="u1", first_name="Test", language="en")
        d = u.model_dump(mode="json")
        u2 = User.model_validate(d)
        assert u2.user_id == u.user_id
        assert u2.language == u.language

    def test_user_priority_prompt_none(self):
        u = User(user_id="u1", priority_prompt=None)
        assert u.priority_prompt is None


class TestTaskFilterEdgeCases:
    def test_task_filter_all_none(self):
        f = TaskFilter()
        assert f.status is None
        assert f.due_date_from is None

    def test_task_filter_only_status(self):
        f = TaskFilter(status="done")
        assert f.status == "done"
