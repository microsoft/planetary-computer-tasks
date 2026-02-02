import pytest
import yaml

from pctasks.ingest.models import (
    IngestNdjsonInput,
    IngestTaskInput,
)


def test_ingest_task_input_model_validate_from_yaml() -> None:
    """Test model_validate from YAML input like glm.yaml ingest-items task."""
    yaml_content = """
content:
  type: Ndjson
  uris:
  - ${{tasks.create-items.output.ndjson_uri}}
options:
  insert_group_size: 5000
  insert_only: false
"""
    data = yaml.safe_load(yaml_content)
    input = IngestTaskInput.model_validate(data)

    assert isinstance(input.content, IngestNdjsonInput)
    assert input.content.type == "Ndjson"
    assert input.content.uris == ["${{tasks.create-items.output.ndjson_uri}}"]
    assert input.options.insert_group_size == 5000
    assert input.options.insert_only is False


def test_ingest_ndjson_input_requires_uris_or_folder() -> None:
    with pytest.raises(ValueError, match="Either ndjson_folder or uris must be"):
        IngestNdjsonInput(type="Ndjson")
