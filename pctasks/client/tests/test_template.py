from pathlib import Path

import yaml

from pctasks.client.workflow.template import LocalTemplater
from pctasks.ingest.models import IngestCollectionsInput

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

    data = IngestCollectionsInput.model_validate(templated_dict)

    assert data.collections
    assert data.collections[0]["id"] == "test-collection"
