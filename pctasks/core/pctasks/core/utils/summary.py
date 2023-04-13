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
    max_distinct_values = 4
    """The max number of distinct values to collect in a distinct value summary.

    If there are more values collected than this settings, the DistinctValueSummary
    will be converted into a MixedValueSummary.
    """

    max_distinct_key_sets = 5
    """The max number of distinct values to collect in a distinct key sets.

    If there are more values collected than this setting, the DistinctKeySets
    will be converted to a MixedKeySets.
    """

    max_mixed_object_list_samples = 3
    """The max number of distinct samples to include in a mixed object list summary."""

    max_mixed_summary_samples = 4
    """The max number of distinct samples to include in a mixed summary."""


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


# Value Counts


class ValueCount(BaseModel):
    """Represents a count of a specific value type.

    This model is tagged with a 'type' field, overridden by subclasses
    with a literal value, which allows for proper serialization/deserialization.
    """

    type: str
    count: int

    def merge(self, other: "ValueCount") -> None:
        self.count += other.count


class BoolValueCount(ValueCount):
    """Count of boolean values."""

    type: str = Field(default=ValueTypes.BOOLEAN, const=True)
    value: bool


class IntValueCount(ValueCount):
    """Count of integer values."""

    type: str = Field(default=ValueTypes.INT, const=True)
    value: int


class FloatValueCount(ValueCount):
    """Count of float values."""

    type: str = Field(default=ValueTypes.FLOAT, const=True)
    value: float


class StringValueCount(ValueCount):
    """Count of string values."""

    type: str = Field(default=ValueTypes.STRING, const=True)
    value: str


class NullValueCount(ValueCount):
    """Count of null values."""

    type: str = Field(default=ValueTypes.NULL, const=True)
    value: Optional[str] = Field(default=None, const=True)


class ListValueCount(ValueCount):
    """Count of list values."""

    type: str = Field(default=ValueTypes.LIST, const=True)
    value: List[Any]


# Property Summaries


class PropertySummary(BaseModel):
    """Represents a summary of a single property in a JSON object.

    PropertySummaries are merged together through
    the merging of ObjectSummary instances. The merge function
    can produce a different PropertySummary type depending on the
    the type it's being merged with or by rules that transform types.

    See the individual merge function docs for the rules that apply.
    """

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
    """Represents a property that has a set of distinct values.

    Each of the values is represented by a ValueCount instance.
    The values can be bool, int, float, string, list, or null.
    """

    type: str = Field(default=SummaryTypes.DISTINCT, const=True)
    values: ValueCountList

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If other is a MixedValueSummary, IntRangeSummary, FloatRangeSummary,
        this method will defer to the merge function of the other summary.

        If other is not one of the above, and is not a DistinctValueSummary,
        it will return a MixedSummary.

        If other is a DistinctValueSummary, this method will merge the values
        of the other summary into this one. If the number of distinct values
        exceeds the max_distinct_values setting, this method will return a
        MixedValueSummary.
        """
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
                    v.merge(indexed_other[v.value])
                    del indexed_other[v.value]
                values.append(v)

        for v in indexed_other.values():
            values.append(v)

        # Handle lists
        for v in list_values_self:
            found = False
            for i, other_v in enumerate(list_values_other):
                if v.value == other_v.value:
                    v.merge(other_v)
                    list_values_other.pop(i)
                    values.append(v)
                    found = True
                    break
            if not found:
                values.append(v)
        values.extend(list_values_other)

        # Check if we have too many values
        if len(values) > settings.max_distinct_values:
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
                    [x for x in values[: settings.max_distinct_values]],
                ),
            )
        else:
            return DistinctValueSummary(
                count_with=self.count_with + other.count_with,
                count_without=self.count_without + other.count_without,
                values=cast(ValueCountList, values),
            )


class IntRangeSummary(PropertySummary):
    """Represents a property that is an integer in a specific range."""

    type: str = Field(default=SummaryTypes.INT_RANGE, const=True)
    min: int
    max: int

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If the other is a DistinctValueSummary with integer values,
        the range will be expanded to include those values.
        If the other is a DistinctValueSummary with non-integer values,
        or if the other is not a IntRangeSummary itself,
        a MixedSummary will be returned.
        If the other is an IntRangeSummary, the range will be expanded to include
        the other range.
        """
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
                sample.extend(other.values[: settings.max_distinct_values])
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
    """Represents a property that is an float in a specific range."""

    type: str = Field(default=SummaryTypes.FLOAT_RANGE, const=True)
    min: float
    max: float

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If the other is a DistinctValueSummary with float values,
        the range will be expanded to include those values.
        If the other is a DistinctValueSummary with non-float values,
        or if the other is not a FloatRangeSummary itself,
        a MixedSummary will be returned.
        If the other is an FloatRangeSummary, the range will be expanded to include
        the other range.
        """
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
                sample.extend(other.values[: settings.max_distinct_values])
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
    """Represents a property that is an JSON Object."""

    type: str = Field(default="object", const=True)
    summary: "ObjectSummary"

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If the other is not an ObjectPropertySummary, a MixedSummary will be returned.
        If the other is an ObjectPropertySummary, the respective
        PropertySummaries will be merged and this summary will be returned.
        """
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
    """Represents a property that is a list of JSON Objects."""

    type: str = Field(default=SummaryTypes.OBJECT_LIST, const=True)
    values: List["ObjectSummary"]

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If other is a MixedObjectListSummary, this method will defer to the
        other's merge method. If the other is not an ObjectListSummary, a
        MixedObjectListSummary will be created.
        Otherwise, if the lengths of the lists are equal, the respective
        objects from the two lists will be merged and this summary will be returned.
        Otherwise, a MixedObjectListSummary will be created.
        """
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
    """Represents a property that is a non-uniform list of JSON Objects."""

    type: str = Field(default=SummaryTypes.MIXED_OBJECT_LIST, const=True)
    lengths: Set[int]
    sample: List[List["ObjectSummary"]]

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If other is an ObjectListSummary or MixedObjectListSummary, the
        summary values of other
        will be merged into this summary and this summary will be returned.
        Otherwise, if the other is not a MixedObjectListSummary, a
        MixedSummary will be returned.
        """
        if isinstance(other, ObjectListSummary):
            self.count_with += other.count_with
            self.count_without += other.count_without
            self.lengths.add(len(other.values))
            if len(self.sample) < settings.max_mixed_object_list_samples:
                self.sample.append(
                    other.values[
                        : settings.max_mixed_object_list_samples - len(self.sample)
                    ]
                )
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
    """Represents a property that has values with distinct values
    exceeding the max_mixed_value_samples setting.

    This summary applies to properties that, if they were all
    the same type, would have been represented by a DistinctValueSummary.
    RangeSummaries will also be merged into a MixedValueSummary, but will
    not be represented in the samples.
    """

    type: str = Field(default=SummaryTypes.MIXED_VALUE, const=True)
    data_types: Set[str]
    sample: ValueCountAndRangeList

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another PropertySummary into this one.

        If other is a DistinctValueSummary, MixedValueSummary, IntegerRangeSummary,
        or FloatRangeSummary, merge the summary values of other into this summmary
        and return this summary. Otherwise return a MixedSummary.
        """
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
    """Represents a property that is represented by a mix of summary types."""

    type: str = Field(default=SummaryTypes.MIXED_SUMMARIES, const=True)
    summary_types: Set[str]
    sample: List[PropertySummary]

    def merge(
        self, other: PropertySummary, settings: SummarySettings
    ) -> PropertySummary:
        """Merge another summary into this one.

        This will simply add the other summary type to the set of summary types"""
        self.summary_types.add(other.type)
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
                if len(result.sample) < settings.max_distinct_values:
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

# Key Sets


class KeySetsType(str, Enum):
    DISTINCT = "distinct"
    MIXED = "mixed"


class KeySet(BaseModel):
    """Represents a set of keys that are present in objects."""

    keys: Set[str]
    """The distinct set of keys that are present in an object."""
    count_with: int
    """The number of objects that have this set of keys."""


class DistinctKeySets(BaseModel):
    """Represents a set of distinct key sets."""

    type: KeySetsType = Field(default=KeySetsType.DISTINCT, const=True)
    values: List[KeySet]

    def merge(self, other: "KeySetType", settings: SummarySettings) -> "KeySetType":
        """Merges another KeySetType into this one.

        If the other key set is a MixedKeySets, the result will be a MixedKeySets.
        If the merging of this and the other key sets creates more values than
        the max_distinct_key_sets setting, the result will be a MixedKeySets.
        """
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
        if len(new_key_sets) > settings.max_distinct_key_sets:
            return MixedKeySets(
                sample_values=sorted(
                    new_key_sets[: settings.max_distinct_key_sets],
                    key=lambda k: k.count_with,
                    reverse=True,
                )
            )

        else:
            return DistinctKeySets(values=new_key_sets)


class MixedKeySets(BaseModel):
    """Represents a mixed set of keys that are present in objects.

    The number of samples present is limited by the max_mixed_key_sets setting.
    """

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
                new_key_sets[: settings.max_distinct_key_sets],
                key=lambda k: k.count_with,
                reverse=True,
            )
        )


KeySetType = Union[DistinctKeySets, MixedKeySets]


# Object Summary


class ObjectSummary(BaseModel):
    """An ObjectSummary represents summary information about a set of objects.

    This object is used to understand the structure and common properties of a set
    of objects, such as STAC Items. Summaries are generated for individual objects,
    and summaries can be merged together to create a single summary for a set of
    objects.
    """

    count: int
    keys: Dict[
        str,
        SummaryType,
    ]
    key_sets: Union[DistinctKeySets, MixedKeySets]

    @classmethod
    def summarize_dict(
        cls, document: Dict[str, Any], include_keys: Optional[List[str]] = None
    ) -> "ObjectSummary":
        """Create a summary of a JSON Document represented by 'document'."""

        summary = cls(
            count=1,
            keys={},
            key_sets=DistinctKeySets(
                values=[KeySet(keys=set(document.keys()), count_with=1)]
            ),
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
        for key, value in document.items():
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
        """Merge this summary with another summary."""
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
        """Summarize a sequence of JSON documents.

        This method generates a summary for each of the JSON documents
        and returns the merged summary.
        """
        if not data:
            raise ValueError("No values: can not summarize empty list of objects")
        return reduce(
            lambda a, b: a.merge(b, settings),
            [cls.summarize_dict(d, include_keys=include_keys) for d in data],
        )

    @classmethod
    def empty(cls) -> "ObjectSummary":
        return cls(count=0, keys={}, key_sets=DistinctKeySets(values=[]))


ObjectListSummary.update_forward_refs()
ObjectPropertySummary.update_forward_refs()
MixedObjectListSummary.update_forward_refs()


def make_collection(
    summary: ObjectSummary,
    collection_id: str,
    keywords: list[str] | None = None,
    stac_extensions: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
    title: str | None = None,
    description: str = "{{ collection.description }}",
    links: list[str] | None = [],
):
    asset_summary = summary.keys["assets"].summary

    item_assets = {}

    for k, asset_summary in summary.keys["assets"].summary.keys.items():
        # assuming we'll move these from description to title
        # TODO: assert one
        item_assets[k] = {
            # "title": asset_summary.summary.keys["description"].values[0].value,
            "type": asset_summary.summary.keys["type"].values[0].value,
            "roles": asset_summary.summary.keys["roles"].values[0].value,
        }

        if eo_bands := asset_summary.summary.keys.get("eo:bands"):
            print("x!")
            item_assets[k]["eo:bands"] = [
                {
                    "name": band.keys["name"].values[0].value,
                    "description": band.keys["description"].values[0].value,
                    "center_wavelength": band.keys["center_wavelength"].values[0].value,
                    "band_width": band.keys["band_width"].values[0].value,
                }
                for band in eo_bands.values
            ]

    collection = {
        "stac_version": "1.0.0",
        "id": collection_id,
        "type": "Collection",
        "description":description,
        "links": links or [],
        "title": title,
        "keywords": keywords or [],
        "stac_extensions": stac_extensions or [],
        "summaries": {},
        "item_assets": item_assets,
    }

    summary_keys = ["constellation", "platform", "instruments"]

    for key in summary_keys:
        print(key)
        summary_value = summary.keys["properties"].summary.keys[key]
        value = None
        # if key == "constellation":
            # breakpoint()
        if summary_value.type == "distinct":
            if summary_value.type == "string":
                value = summary_value.values[0]
                value = [value.value]
            else:
                value = [value.value for value in summary_value.values]
        else:
            value = [x.value for x in summary_value.values]

        collection["summaries"][key] = value

    collection.update(extra_fields or {})

    return collection

def make_collection(
    summary: ObjectSummary,
    collection_id: str,
    keywords: list[str] | None = None,
    stac_extensions: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
    title: str | None = None,
    description: str = "{{ collection.description }}",
    links: list[str] | None = [],
):
    asset_summary = summary.keys["assets"].summary

    item_assets = {}

    for k, asset_summary in summary.keys["assets"].summary.keys.items():
        # assuming we'll move these from description to title
        # TODO: assert one
        item_assets[k] = {
            # "title": asset_summary.summary.keys["description"].values[0].value,
            "type": asset_summary.summary.keys["type"].values[0].value,
            "roles": asset_summary.summary.keys["roles"].values[0].value,
        }

        if eo_bands := asset_summary.summary.keys.get("eo:bands"):
            print("x!")
            item_assets[k]["eo:bands"] = [
                {
                    "name": band.keys["name"].values[0].value,
                    "description": band.keys["description"].values[0].value,
                    "center_wavelength": band.keys["center_wavelength"].values[0].value,
                    "band_width": band.keys["band_width"].values[0].value,
                }
                for band in eo_bands.values
            ]

    collection = {
        "stac_version": "1.0.0",
        "id": collection_id,
        "type": "Collection",
        "description":description,
        "links": links or [],
        "title": title,
        "keywords": keywords or [],
        "stac_extensions": stac_extensions or [],
        "summaries": {},
        "item_assets": item_assets,
    }

    summary_keys = ["constellation", "platform", "instruments"]

    for key in summary_keys:
        print(key)
        summary_value = summary.keys["properties"].summary.keys[key]
        value = None
        # if key == "constellation":
            # breakpoint()
        if summary_value.type == "distinct":
            if summary_value.type == "string":
                value = summary_value.values[0]
                value = [value.value]
            else:
                value = [value.value for value in summary_value.values]
        else:
            value = [x.value for x in summary_value.values]

        collection["summaries"][key] = value

    collection.update(extra_fields or {})

    return collection
