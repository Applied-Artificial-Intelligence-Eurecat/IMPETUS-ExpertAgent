from abc import ABC, abstractmethod

class Source(ABC):

    @abstractmethod
    def __repr__(self) -> str:
        pass 

class FaissSource(Source):
    def __init__(self, metadata: dict):
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"Source: {self.metadata.get('source', 'Unknown')}, Page: {self.metadata.get('page', 'Unknown')}"
