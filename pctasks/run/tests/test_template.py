from typing import Any, Dict, List, Union

import pytest

from pctasks.core.models.base import ForeachConfig
from pctasks.core.utils.template import TemplateError
from pctasks.run.template import template_foreach


def test_template_foreach():
    foreach_config = ForeachConfig(items="${{ jobs.job1.tasks.task1.output.items }}")
    jobs_output = {"job1": {"tasks": {"task1": {"output": {"items": ["one", "two"]}}}}}

    templated = template_foreach(foreach_config, jobs_output, None)
    assert templated == ["one", "two"]


def test_template_foreach_missing():
    foreach_config = ForeachConfig(
        items="${{ jobs.job1.tasks.task1.output.items.foo }}"
    )
    jobs_output = {
        "job1": {"tasks": {"task1": {"output": {"items": [{"bar": "nope"}]}}}}
    }

    with pytest.raises(TemplateError):
        template_foreach(foreach_config, jobs_output, None)


def test_template_foreach_multilevel():
    foreach_config = ForeachConfig(items="${{ jobs.job1.tasks.task1.output.items }}")
    jobs_output: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {
        "job1": [
            {"tasks": {"task1": {"output": {"items": []}}}},
            {"tasks": {"task1": {"output": {"items": ["one"]}}}},
            {"tasks": {"task1": {"output": {"items": ["two", "three"]}}}},
        ]
    }

    templated = template_foreach(foreach_config, jobs_output, None)
    assert templated == ["one", "two", "three"]


def test_template_foreach_nested():
    foreach_config = ForeachConfig(
        items="${{ jobs.job1.tasks.task1.output.items }}", flatten=False
    )
    jobs_output: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {
        "job1": [
            {"tasks": {"task1": {"output": {"items": ["a", "b"]}}}},
            {"tasks": {"task1": {"output": {"items": ["c", "d"]}}}},
        ]
    }

    templated = template_foreach(foreach_config, jobs_output, None)
    assert templated == [["a", "b"], ["c", "d"]]
