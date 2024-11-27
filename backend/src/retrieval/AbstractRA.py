# pylint: disable=C0103
"""
Abstract definition of the RetrievalAugmented (RA) module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from .Source import Source


@dataclass
class DocumentObject:
    """
    A data class representing a document object. This class stores information about a document,
    including its name, content, and the source from which the document was derived.

    Attributes:
        content (str): The textual content of the document.
        source (Union[Source, None]): The source of the document, which may include metadata about
                                      where the document originated, or None if the source is
                                      unknown.
    """

    content: str
    source: Source | None
    cleaned_content: str | None
    similarity: float


# pylint: disable=R0903
class AbstractRA(ABC):
    """
    Abstract base class for a Retrieval Augmenter. This class provides a framework for augmenting
    information retrieval, ensuring that all derived classes implement the required methods. The
    primary role of this class is to enhance the retrieval of document objects by augmenting query
    results based on a given input sentence.

    Attributes:
        config (dict): Configuration parameters for the retrieval augmenter.
    """

    def __init__(self, **config):
        """
        Initializes the retrieval augmenter with the provided configuration settings.

        Args:
            **config (dict): Arbitrary keyword arguments containing configuration options for the
            retrieval augmenter.
        """

    @abstractmethod
    def __call__(self, sentence: str) -> List[DocumentObject]:
        """
        Enhances information retrieval by augmenting the results based on the input sentence.
        This method should augment the input to produce more relevant or extended document results.
        It must be implemented by all subclasses of AbstractRA.

        Args:
            sentence (str): The input sentence used to augment retrieval of document objects.

        Returns:
            List[DocumentObject]: A list of DocumentObject instances that are augmented and relevant
            to the input sentence.

        Raises:
            NotImplementedError: If this method is not overridden by a subclass.
        """
