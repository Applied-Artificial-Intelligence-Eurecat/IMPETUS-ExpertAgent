from abc import ABC, abstractmethod
from src.retrieval.AbstractRA import DocumentObject
from typing import List

class Metadata(ABC):

   @abstractmethod
   def __repr__(self) -> str:
       pass 

class FaissMetadata(Metadata):
    def __init__(self, documents: List[DocumentObject]):
        self.documents = documents

    def __repr__(self) -> str:
        return [repr(doc) for doc in self.documents]
