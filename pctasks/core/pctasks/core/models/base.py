from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import yaml
from pydantic import BaseModel

from pctasks.core.yaml import model_from_yaml

T = TypeVar("T", bound=BaseModel)


class PCBaseModel(BaseModel):
    """Base model that uses different defaults for serialization."""

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().dict(**kwargs)

    def json(self, **kwargs: Any) -> str:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().json(**kwargs)

    def to_json(self, *args: Any, **kwargs: Any) -> str:
        """Passed through to .json()

        Allows for better integration with Azure Durable Functions.
        """
        return self.json(*args, **kwargs)

    def to_yaml(self, *args: Any, **kwargs: Any) -> str:
        """Return this model as a YAML string.

        Any arguments are passed to the underlying .json() call.
        """

        # Attempt to sort properties based on their order in the schema.
        def _prop_sort(field_order: List[str], d: Dict[str, Any]) -> Dict[str, Any]:
            _len = len(field_order)
            return dict(
                sorted(
                    d.items(),
                    key=lambda x: field_order.index(x[0])
                    if x[0] in field_order
                    else _len,
                )
            )

        return yaml.dump(
            _prop_sort(
                list(self.__annotations__.keys()),
                yaml.safe_load(self.json(*args, **kwargs)),
            ),
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls: Type[T], yaml_str: str, section: Optional[str] = None) -> T:
        return model_from_yaml(cls, yaml_str, section=section)

    class Config:
        exclude_none = True


class RunRecordId(PCBaseModel):
    run_id: str
    dataset_id: Optional[str] = None
    group_id: Optional[str] = None
    job_id: Optional[str] = None
    task_id: Optional[str] = None

    def __str__(self) -> str:
        s = f"{self.run_id}"
        if self.dataset_id:
            s += f"_d_{self.dataset_id}"
        if self.job_id:
            s += f"_j_{self.job_id}"
        if self.task_id:
            s += f"_t_{self.task_id}"
        return s

    def update(
        self,
        dataset_id: Optional[str] = None,
        group_id: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> "RunRecordId":
        return RunRecordId(
            run_id=self.run_id,
            dataset_id=dataset_id or self.dataset_id,
            group_id=group_id or self.group_id,
            job_id=job_id or self.job_id,
            task_id=task_id or self.task_id,
        )


class ForeachConfig(PCBaseModel):
    """
    Configuration for foreach blocks in workflows.

    Parameters
    ----------
    items: string or list of objects
    flatten: bool, default True
        Whether to flatten lists nested objects to a single flat list.
    """
    items: Union[str, List[Any]]
    flatten: bool = True
