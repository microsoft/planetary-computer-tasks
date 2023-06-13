from dataclasses import dataclass
import os.path


@dataclass
class ErrorRecord:
    record_id: str
    reason: str


@dataclass
class CogifyError(ErrorRecord):
    item_id: str
    path: str

    @classmethod
    def create(cls, item_id: str, path: str) -> "CogifyError":
        return cls(
            record_id=f"COGIFY_ERROR-{item_id}",
            item_id=item_id,
            path=path,
            reason="COGIFY_ERROR",
        )


@dataclass
class OpenFileError(ErrorRecord):
    path: str
    segfault: bool

    @classmethod
    def create(cls, path: str, segfault: bool) -> "OpenFileError":
        return cls(
            record_id=f"HDFPY_OPEN_ERROR-{path}",
            path=path,
            segfault=segfault,
            reason="HDFPY_OPEN_ERROR",
        )


@dataclass
class InvalidGeometryError(ErrorRecord):
    path: str

    @classmethod
    def create(cls, path: str) -> "InvalidGeometryError":
        return cls(
            record_id=f"BAD_GEOM_ERROR-{path}",
            path=path,
            reason="BAD_GEOM_ERROR",
        )


@dataclass
class MissingExtent(ErrorRecord):
    path: str

    @classmethod
    def create(cls, path: str) -> "MissingExtent":
        id = os.path.splitext(os.path.basename(path))[0]
        return cls(
            record_id=f"GOES_MISSING_EXTENT-{id}",
            path=path,
            reason="GOES_MISSING_EXTENT",
        )


@dataclass
class MissingKey(ErrorRecord):
    path: str
    error: str

    @classmethod
    def create(cls, path: str, e: KeyError) -> "MissingKey":
        id = os.path.splitext(os.path.basename(path))[0]
        return cls(
            record_id=f"GOES_MISSING_KEY-{id}",
            path=path,
            reason="GOES_MISSING_EXTENT",
            error=str(e),
        )
