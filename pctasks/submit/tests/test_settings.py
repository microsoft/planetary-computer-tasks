from pathlib import Path
from tempfile import TemporaryDirectory

from pctasks.submit.settings import SubmitSettings


def test_image_keys():
    yaml = """
submit:
    queue_name: inbox
    account_url: name
    account_key: key
    image_keys:
        ingest:
            image: pctasks-ingest:latest
        ingest-prod:
            image: pctasks-ingest:v1
"""
    with TemporaryDirectory() as tmp_dir:
        settings_file = Path(tmp_dir) / "settings.yaml"
        with open(settings_file, "w") as f:
            f.write(yaml)
        settings = SubmitSettings.get(settings_file=str(settings_file))

    assert "ingest-prod" in settings.image_keys
    assert settings.image_keys["ingest-prod"].image == "pctasks-ingest:v1"
