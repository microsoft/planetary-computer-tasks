from dataclasses import dataclass
from typing import Any, Dict, List, Optional, OrderedDict, Type, TypeVar, cast

import strictyaml
from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorList

T = TypeVar("T", bound=BaseModel)


@dataclass
class YamlValidationErrorInfo:
    pydantic_error: ErrorList
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    path: Optional[str] = None


class SectionDoesNotExist(Exception):
    pass


class YamlValidationError(ValidationError):
    def __init__(
        self,
        yml_text: str,
        errors: List[YamlValidationErrorInfo],
        model: Any,
    ) -> None:
        self.yaml_ext = yml_text
        self.yaml_errors = errors
        super().__init__([e.pydantic_error for e in errors], model)

    def __str__(self) -> str:
        result = "\nValidation errors while parsing YAML:\n"

        def str_for_error(e: YamlValidationErrorInfo) -> str:
            err_d = cast(Dict[str, Any], e.pydantic_error)
            loc_str = " -> ".join([str(x) for x in err_d["loc"]])
            msg = f"{loc_str}: {err_d['msg']}"
            return f"{msg}"

        start_lines = set(
            [e.start_line for e in self.yaml_errors if e.start_line is not None]
        )
        errors_with_lines = sorted(
            [error for error in self.yaml_errors if error.end_line is not None],
            key=lambda e: e.end_line or 0,
        )
        errors_without_lines = [
            error for error in self.yaml_errors if error.start_line is None
        ]

        if errors_with_lines:
            lines = self.yaml_ext.split("\n")
            for i, line in enumerate(lines):
                if i in start_lines:
                    result += "*\n" + "*" + line + "\n"
                else:
                    result += " " + line + "\n"
                if errors_with_lines and i == errors_with_lines[0].start_line:
                    result += f"* {str_for_error(errors_with_lines.pop(0))}\n"

        for error in errors_without_lines:
            result += str_for_error(error) + "\n"

        return result


def model_from_yaml(
    model: Type[T], yaml_txt: str, section: Optional[str], path: Optional[str] = None
) -> T:
    """Loads YAML from text and returns a model object.

    If this config is scoped to a section, and the section does not exist,
    this method will return None.

    Raises:
        YamlValidationError: If the YAML is invalid.
    """
    yml: strictyaml.YAML = strictyaml.load(yaml_txt)
    data = cast(OrderedDict[str, Any], yml.data)
    if section:
        if section not in data:
            raise SectionDoesNotExist(f"Section {section} does not exist.")

        data = data[section]
    try:
        return model(**data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            _yml_section: Optional[strictyaml.YAML] = yml
            for loc in error["loc"]:
                if _yml_section is not None:
                    if loc not in _yml_section:
                        _yml_section = None
                        break
                    else:
                        _yml_section = _yml_section[loc]
            start_line: Optional[int] = None
            end_line: Optional[int] = None
            if _yml_section is not None:
                start_line = _yml_section.start_line
                end_line = _yml_section.end_line

            errors.append(
                YamlValidationErrorInfo(
                    start_line=start_line,
                    end_line=end_line,
                    path=path,
                    pydantic_error=cast(ErrorList, error),
                ),
            )

        raise YamlValidationError(yml_text=yaml_txt, errors=errors, model=model)
