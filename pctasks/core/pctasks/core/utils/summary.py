"""summary.py

Module for generating summaries from JSON objects.
Useful for generating Collection "summaries" and "item-assets" fields.
"""


from abc import abstractmethod
from enum import Enum
from functools import reduce
from typing import Any, Dict, List, Optional, Set, Union, cast

from pydantic import BaseModel, Field

from pctasks.core.utils import map_opt


class SummarySettings(BaseModel):
    max_mixed_summary_samples = 4
    max_mixed_value_samples = 4
    max_mixed_object_list_samples = 3
    max_mixed_key_sets = 5


class ValueTypes(str, Enum):
    BOOLEAN = "boolean"
    INT = "numeric-int"
    FLOAT = "numeric-float"
    STRING = "string"
    LIST = "list"
    NULL = "null"


class SummaryTypes(str, Enum):
    DISTINCT = "distinct"
    INT_RANGE = "int-range"
    FLOAT_RANGE = "float-range"
    OBJECT_LIST = "object-list"
    MIXED_VALUE = "mixed-value"
    MIXED_OBJECT_LIST = "mixed-object-list"
    MIXED_SUMMARIES = "mixed-summaries"


def is_value_type(v: Any) -> bool:
    return isinstance(v, (bool, str, float, int))


class ValueCount(BaseModel):
    type: str
    count: int

    def add_count(self, other: "ValueCount") -> None:
        self.count += other.count


class BoolValueCount(ValueCount):
    type: str = Field(default=ValueTypes.BOOLEAN, const=True)
    value: bool


class IntValueCount(ValueCount):
    type: str = Field(default=ValueTypes.INT, const=True)
    value: int


class FloatValueCount(ValueCount):
    type: str = Field(default=ValueTypes.FLOAT, const=True)
    value: float


class StringValueCount(ValueCount):
    type: str = Field(default=ValueTypes.STRING, const=True)
    value: str


class NullValueCount(ValueCount):
    type: str = Field(default=ValueTypes.NULL, const=True)
    value: Optional[str] = Field(default=None, const=True)


class ListValueCount(ValueCount):
    type: str = Field(default=ValueTypes.LIST, const=True)
    value: List[Any]


class PropertySummary(BaseModel):
    type: str
    count_with: int
    count_without: int

    @abstractmethod
    def merge(
        self, other: "PropertySummary", settings: SummarySettings
    ) -> "PropertySummary":
        ...


ValueCountList = List[
    Union[
        BoolValueCount,
        IntValueCount,
        FloatValueCount,
        StringValueCount,
        ListValueCount,
        NullValueCount,
    ]
]

ValueCountAndRangeList = List[
    Union[
        BoolValueCount,
        IntValueCount,
        FloatValueCount,
        StringValueCount,
        ListValueCount,
        NullValueCount,
        "IntRangeSummary",
        "FloatRangeSummary",
    ]
]


class DistinctValueSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.DISTINCT, const=True)
    values: ValueCountList

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one."""
        if isinstance(other, (MixedValueSummary, IntRangeSummary, FloatRangeSummary)):
            return other.merge(self, settings=settings)

        if not isinstance(other, DistinctValueSummary):
            return MixedSummary.create(self, other, settings=settings)

        values: List[ValueCount] = []
        indexed_other = {
            v.value: v for v in other.values if not isinstance(v, ListValueCount)
        }
        list_values_other: List[ListValueCount] = [
            v for v in other.values if isinstance(v, ListValueCount)
        ]
        list_values_self: List[ListValueCount] = []

        # Handle non-lists
        for v in self.values:
            if isinstance(v, ListValueCount):
                list_values_self.append(v)
            else:
                if v.value in indexed_other:
                    v.add_count(indexed_other[v.value])
                    del indexed_other[v.value]
                values.append(v)

        for v in indexed_other.values():
            values.append(v)

        # Handle lists
        for v in list_values_self:
            found = False
            for i, other_v in enumerate(list_values_other):
                if v.value == other_v.value:
                    v.add_count(other_v)
                    list_values_other.pop(i)
                    values.append(v)
                    found = True
                    break
            if not found:
                values.append(v)
        values.extend(list_values_other)

        # Check if we have too many values
        if len(values) > settings.max_mixed_value_samples:
            data_types = set(v.type for v in values)
            if data_types == {ValueTypes.INT}:
                int_values = [v.value for v in values if isinstance(v, IntValueCount)]
                return IntRangeSummary(
                    count_with=self.count_with + other.count_with,
                    count_without=self.count_without + other.count_without,
                    min=min(v for v in int_values),
                    max=max(v for v in int_values),
                )
            if data_types == {ValueTypes.FLOAT}:
                float_values = [
                    v.value for v in values if isinstance(v, FloatValueCount)
                ]
                return FloatRangeSummary(
                    count_with=self.count_with + other.count_with,
                    count_without=self.count_without + other.count_without,
                    min=min(v for v in float_values),
                    max=max(v for v in float_values),
                )
            return MixedValueSummary(
                count_with=self.count_with + other.count_with,
                count_without=self.count_without + other.count_without,
                data_types=set(v.type for v in values),
                sample=cast(
                    ValueCountAndRangeList,
                    [x for x in values[: settings.max_mixed_value_samples]],
                ),
            )
        else:
            return DistinctValueSummary(
                count_with=self.count_with + other.count_with,
                count_without=self.count_without + other.count_without,
                values=cast(ValueCountList, values),
            )


class IntRangeSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.INT_RANGE, const=True)
    min: int
    max: int

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        if isinstance(other, DistinctValueSummary):
            data_types = set(v.type for v in other.values)
            if data_types == {ValueTypes.INT}:
                int_values = [
                    v.value for v in other.values if isinstance(v, IntValueCount)
                ]
                self.count_with += other.count_with
                self.count_without += other.count_without
                self.min = min(self.min, min(v for v in int_values))
                self.max = max(self.max, max(v for v in int_values))
                return self
            else:
                sample: ValueCountAndRangeList = [self]
                sample.extend(other.values[: settings.max_mixed_value_samples])
                return MixedValueSummary(
                    count_with=self.count_with + other.count_with,
                    count_without=self.count_without + other.count_without,
                    data_types={ValueTypes.INT, other.type},
                    sample=sample,
                )

        if not isinstance(other, IntRangeSummary):
            return MixedSummary.create(self, other, settings=settings)

        self.count_with += other.count_with
        self.count_without += other.count_without
        self.min = min(self.min, other.min)
        self.max = max(self.max, other.max)

        return self


class FloatRangeSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.FLOAT_RANGE, const=True)
    min: float
    max: float

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        if isinstance(other, DistinctValueSummary):
            data_types = set(v.type for v in other.values)
            if data_types == {ValueTypes.FLOAT}:
                float_values = [
                    v.value for v in other.values if isinstance(v, FloatValueCount)
                ]
                self.count_with += other.count_with
                self.count_without += other.count_without
                self.min = min(self.min, min(v for v in float_values))
                self.max = max(self.max, max(v for v in float_values))
                return self
            else:
                sample: ValueCountAndRangeList = [self]
                sample.extend(other.values[: settings.max_mixed_value_samples])
                return MixedValueSummary(
                    count_with=self.count_with + other.count_with,
                    count_without=self.count_without + other.count_without,
                    data_types={ValueTypes.FLOAT, other.type},
                    sample=sample,
                )

        if not isinstance(other, FloatRangeSummary):
            return MixedSummary.create(self, other, settings=settings)

        self.count_with += other.count_with
        self.count_without += other.count_without
        self.min = min(self.min, other.min)
        self.max = max(self.max, other.max)

        return self


class ObjectPropertySummary(PropertySummary):
    type: str = Field(default="object", const=True)
    summary: "ObjectSummary"

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        if not isinstance(other, ObjectPropertySummary):
            return MixedSummary.create(self, other, settings=settings)

        self.summary.count += other.summary.count
        self.summary.key_sets = self.summary.key_sets.merge(
            other.summary.key_sets, settings=settings
        )

        count_with = self.count_with

        self_keys = set(self.summary.keys)
        other_keys = set(other.summary.keys)
        shared_keys = self_keys & other_keys

        for k in shared_keys:
            self.summary.keys[k] = cast(
                SummaryType,
                self.summary.keys[k].merge(other.summary.keys[k], settings=settings),
            )

        for k in other_keys - shared_keys:
            self.summary.keys[k] = other.summary.keys[k]
            self.summary.keys[k].count_without += count_with

        for k in self_keys - shared_keys:
            self.summary.keys[k].count_without += other.count_with

        self.count_with += other.count_with
        self.count_without += other.count_without

        return self


class ObjectListSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.OBJECT_LIST, const=True)
    values: List["ObjectSummary"]

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        if isinstance(other, MixedObjectListSummary):
            return other.merge(self, settings=settings)

        if not isinstance(other, ObjectListSummary):
            return MixedSummary.create(self, other, settings=settings)

        if len(self.values) != len(other.values):
            return MixedObjectListSummary(
                count_with=self.count_with + other.count_with,
                count_without=self.count_without + other.count_without,
                lengths={len(self.values), len(other.values)},
                sample=[self.values, other.values],
            )
        for i, v in enumerate(self.values):
            self.values[i] = v.merge(other.values[i], settings=settings)

        self.count_with += other.count_with
        self.count_without += other.count_without
        return self


class MixedObjectListSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.MIXED_OBJECT_LIST, const=True)
    lengths: Set[int]
    sample: List[List["ObjectSummary"]]

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        if isinstance(other, ObjectListSummary):
            self.count_with += other.count_with
            self.count_without += other.count_without
            self.lengths.add(len(other.values))
            if len(self.sample) < settings.max_mixed_object_list_samples:
                self.sample.append(other.values)
            return self

        if not isinstance(other, MixedObjectListSummary):
            return MixedSummary.create(self, other, settings=settings)

        self.count_with += other.count_with
        self.count_without += other.count_without
        self.lengths.update(other.lengths)
        self.sample = (self.sample + other.sample)[
            : settings.max_mixed_object_list_samples
        ]

        return self


class MixedValueSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.MIXED_VALUE, const=True)
    data_types: Set[str]
    sample: ValueCountAndRangeList

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        if isinstance(other, DistinctValueSummary):
            self.count_with += other.count_with
            self.count_without += other.count_without
            self.data_types.update(v.type for v in other.values)
            return self

        if isinstance(other, IntRangeSummary):
            self.count_with += other.count_with
            self.count_without += other.count_without
            self.data_types.add(ValueTypes.INT)
            return self

        if isinstance(other, FloatRangeSummary):
            self.count_with += other.count_with
            self.count_without += other.count_without
            self.data_types.add(ValueTypes.FLOAT)
            return self

        if not isinstance(other, MixedValueSummary):
            return MixedSummary.create(self, other, settings=settings)

        self.count_with += other.count_with
        self.count_without += other.count_without
        self.data_types.update(other.data_types)

        return self


class MixedSummary(PropertySummary):
    type: str = Field(default=SummaryTypes.MIXED_SUMMARIES, const=True)
    summary_types: Set[str]
    sample: List[PropertySummary]

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        return self

    @classmethod
    def create(
        cls, *summaries: PropertySummary, settings: SummarySettings
    ) -> "MixedSummary":
        result = MixedSummary(
            summary_types=set(), sample=[], count_with=0, count_without=0
        )
        for summary in summaries:
            result.count_with += summary.count_with
            result.count_without += summary.count_without
            if isinstance(summary, MixedSummary):
                result.summary_types = result.summary_types | summary.summary_types
                result.sample = (result.sample + summary.sample)[
                    : settings.max_mixed_summary_samples
                ]
            else:
                result.summary_types.add(summary.type)
                if len(result.sample) < settings.max_mixed_value_samples:
                    result.sample.append(summary)
        return result


SummaryType = Union[
    DistinctValueSummary,
    IntRangeSummary,
    FloatRangeSummary,
    ObjectPropertySummary,
    ObjectListSummary,
    MixedValueSummary,
    MixedSummary,
    MixedObjectListSummary,
]


class KeySetsType(str, Enum):
    DISTINCT = "distinct"
    MIXED = "mixed"


class KeySet(BaseModel):
    keys: Set[str]
    count_with: int


class DistinctKeySets(BaseModel):
    type: KeySetsType = Field(default=KeySetsType.DISTINCT, const=True)
    values: List[KeySet]

    def merge(self, other: "KeySetType", settings: SummarySettings) -> "KeySetType":
        if isinstance(other, MixedKeySets):
            return other.merge(self, settings=settings)
        new_key_sets: List[KeySet] = []
        for ks in self.values:
            for i, other_ks in enumerate(other.values):
                if ks.keys == other_ks.keys:
                    ks.count_with += other_ks.count_with
                    other.values.pop(i)
                    break
            new_key_sets.append(ks)
        for ks in other.values:
            new_key_sets.append(ks)
        if len(new_key_sets) > settings.max_mixed_key_sets:
            return MixedKeySets(
                sample_values=sorted(
                    new_key_sets[: settings.max_mixed_key_sets],
                    key=lambda k: k.count_with,
                    reverse=True,
                )
            )

        else:
            return DistinctKeySets(values=new_key_sets)


class MixedKeySets(BaseModel):
    type: KeySetsType = Field(default=KeySetsType.MIXED, const=True)
    sample_values: List[KeySet]

    def merge(self, other: "KeySetType", settings: SummarySettings) -> "KeySetType":
        new_key_sets = self.sample_values
        if isinstance(other, MixedKeySets):
            new_key_sets.extend(other.sample_values)
        else:
            new_key_sets.extend(other.values)

        return MixedKeySets(
            sample_values=sorted(
                new_key_sets[: settings.max_mixed_key_sets],
                key=lambda k: k.count_with,
                reverse=True,
            )
        )


KeySetType = Union[DistinctKeySets, MixedKeySets]


class ObjectSummary(BaseModel):
    count: int
    keys: Dict[
        str,
        SummaryType,
    ]
    key_sets: Union[DistinctKeySets, MixedKeySets]

    @classmethod
    def summarize_dict(
        cls, d: Dict[str, Any], include_keys: Optional[List[str]] = None
    ) -> "ObjectSummary":
        summary = cls(
            count=1,
            keys={},
            key_sets=DistinctKeySets(values=[KeySet(keys=set(d.keys()), count_with=1)]),
        )

        # Allow for '.' separated keys to be included.
        # Create an index of current level keys to a list of subkeys,
        # or None if all subkeys should be included.
        indexed_keys: Optional[Dict[str, Optional[str]]] = None
        if include_keys:
            indexed_keys = {}
            for key in include_keys:
                split = key.split(".")
                indexed_keys[split[0]] = map_opt(
                    lambda l: ".".join(l), split[1:] or None
                )

        # If 'include_keys' is set and the current key isn't
        # included, skip it. If there are sub-keys, ensure
        # they get forwarded to the next recursive calls.
        sub_include_keys: Optional[List[str]] = None
        for key, value in d.items():
            if indexed_keys:
                if key not in indexed_keys:
                    continue
                sub_include_keys = map_opt(lambda x: [x], indexed_keys.get(key))

            if value is None:
                summary.keys[key] = DistinctValueSummary(
                    count_with=1, count_without=0, values=[NullValueCount(count=1)]
                )
            elif isinstance(value, bool):
                summary.keys[key] = DistinctValueSummary(
                    count_with=1,
                    count_without=0,
                    values=[BoolValueCount(value=value, count=1)],
                )
            elif isinstance(value, str):
                summary.keys[key] = DistinctValueSummary(
                    count_with=1,
                    count_without=0,
                    values=[StringValueCount(value=value, count=1)],
                )
            elif isinstance(value, int):
                summary.keys[key] = DistinctValueSummary(
                    count_with=1,
                    count_without=0,
                    values=[IntValueCount(value=value, count=1)],
                )
            elif isinstance(value, float):
                summary.keys[key] = DistinctValueSummary(
                    count_with=1,
                    count_without=0,
                    values=[FloatValueCount(value=value, count=1)],
                )
            elif isinstance(value, list):
                if all(isinstance(v, dict) for v in value):
                    summary.keys[key] = ObjectListSummary(
                        count_with=1,
                        count_without=0,
                        values=[
                            cls.summarize_dict(v, include_keys=sub_include_keys)
                            for v in value
                        ],
                    )
                else:
                    summary.keys[key] = DistinctValueSummary(
                        count_with=1,
                        count_without=0,
                        values=[ListValueCount(value=value, count=1)],
                    )

            elif isinstance(value, dict):
                summary.keys[key] = ObjectPropertySummary(
                    count_with=1,
                    count_without=0,
                    summary=cls.summarize_dict(value, include_keys=sub_include_keys),
                )
            else:
                raise ValueError(f"unknown type: {type(value)}")

        return summary

    def merge(
        self, other: "ObjectSummary", settings: SummarySettings = SummarySettings()
    ) -> "ObjectSummary":
        summary = ObjectSummary(
            count=self.count + other.count,
            keys={},
            key_sets=self.key_sets.merge(other.key_sets, settings),
        )
        for key, value in other.keys.items():
            if key not in self.keys:
                value.count_without += self.count
                summary.keys[key] = value
            else:
                # Requires union type for pydantic de-serialization
                summary.keys[key] = cast(
                    SummaryType,
                    self.keys[key].merge(value, settings),
                )

        return summary

    @classmethod
    def summarize(
        cls,
        *data: Dict[str, Any],
        include_keys: Optional[List[str]] = None,
        settings: SummarySettings = SummarySettings(),
    ) -> "ObjectSummary":
        if not data:
            raise ValueError("No values: can not summarize empty list of objects")
        return reduce(
            lambda a, b: a.merge(b, settings),
            [cls.summarize_dict(d, include_keys=include_keys) for d in data],
        )


ObjectListSummary.update_forward_refs()
ObjectPropertySummary.update_forward_refs()
MixedObjectListSummary.update_forward_refs()
