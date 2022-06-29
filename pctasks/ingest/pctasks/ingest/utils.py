import json
import os
from pathlib import Path
from typing import Any, Dict, Union

import marko
from jinja2 import StrictUndefined, Template

from pctasks.core.utils.stac import validate_stac


def template(values: Dict[str, Any], template_text: str) -> str:
    template = Template(template_text, undefined=StrictUndefined)
    return template.render(**values)


def generate_collection_json(
    template_dir: Union[Path, str], validate: bool = True
) -> Dict[str, Any]:
    template_file = os.path.join(template_dir, "template.json")
    description_file = os.path.join(template_dir, "description.md")

    values: Dict[str, Any] = {"collection": {}}

    with open(description_file) as f:
        markdown = f.read()
        markdown = markdown.replace("\n", "\\n")
        markdown = markdown.replace('"', '\\"')
        values["collection"]["description"] = markdown

    if validate:
        # Ensure valid markdown
        marko.convert(values["collection"]["description"])

    with open(template_file) as f:
        template_text = f.read()

    result_txt = template(values, template_text)
    result = json.loads(result_txt)

    if validate:
        validate_stac(result)

    return result
