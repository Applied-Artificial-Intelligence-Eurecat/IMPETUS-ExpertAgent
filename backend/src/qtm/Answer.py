from dataclasses import dataclass
from .Metadata import Metadata

@dataclass
class Answer:
    content: str
    metadata: Metadata | None