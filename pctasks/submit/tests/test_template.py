from pathlib import Path

import pytest
import yaml

from pctasks.ingest.models import IngestCollectionsInput
from pctasks.submit.template import LocalTemplater

HERE = Path(__file__).parent
TEST_COLLECTION = HERE / "data-files" / "test_collection.json"


def test_local_file_template():
    yaml_str = (
        """
        type: Collections
        collections:
            - ${{ local.file("""
        + str(TEST_COLLECTION)
        + """) }}
    """
    )

    yaml_dict = yaml.safe_load(yaml_str)
    templated_dict = LocalTemplater().template_dict(yaml_dict)

    data = IngestCollectionsInput.parse_obj(templated_dict)

    assert data.collections
    assert data.collections[0]["id"] == "test-collection"

