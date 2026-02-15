"""Test that conversation fixture YAML files exist and have expected structure."""
import os

import pytest


def test_fixtures_dir_exists():
    assert os.path.isdir(os.path.join(os.path.dirname(__file__), "fixtures"))


def test_create_task_flow_yaml_exists():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "create_task_flow.yaml")
    assert os.path.isfile(path)
    with open(path) as f:
        content = f.read()
    assert "user_messages" in content or "expected" in content


def test_query_tasks_flow_yaml_exists():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "query_tasks_flow.yaml")
    assert os.path.isfile(path)


def test_delete_with_confirmation_yaml_exists():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "delete_with_confirmation.yaml")
    assert os.path.isfile(path)


def test_fixture_yaml_loadable():
    """Fixtures can be loaded as YAML (if PyYAML available)."""
    pytest.importorskip("yaml")
    import yaml
    path = os.path.join(os.path.dirname(__file__), "fixtures", "create_task_flow.yaml")
    with open(path) as f:
        data = yaml.safe_load(f)
    assert data is None or isinstance(data, dict)
