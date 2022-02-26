from pctasks.core.yaml import model_from_yaml
from pctasks.ingest.settings import SECTION_NAME, IngestSettings


def test_image_keys():
    yaml = """
submit:
  account_name: pctrxetlrobrxetlsa
  queue_name: inbox
  image_keys:
    - key: ingest
      image: pctasks-ingest:lastest
      environment:
        - DB_CONNECTION_STR= ${ secrets.DB_CONNECTION_STR }

ingest:
  image_keys:
    default: ingest
    targets:
        prod: ingest-prod
        staging: ingest-staging
"""

    settings = model_from_yaml(IngestSettings, yaml, section=SECTION_NAME)
    assert settings.image_keys.default == "ingest"
    assert settings.image_keys.targets
    assert settings.image_keys.targets["prod"] == "ingest-prod"
