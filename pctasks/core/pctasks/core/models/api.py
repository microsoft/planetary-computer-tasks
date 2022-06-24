"""Models for requests and responses to the PCTask API."""

from pydantic import BaseModel


class UploadCodeResult(BaseModel):
    uri: str
