from abc import ABC, abstractmethod
from .Answer import Answer

class AbstractQT(ABC):
    """
    Abstract base class for a query treatment. This class outlines the fundamental structure for query treatments,
    ensuring all derived classes implement the required methods. The primary purpose is to transform a given input
    sentence into a modified format or representation that suits specific processing needs or requirements for the
    other modules.
    
    Attributes:
        config (dict): Configuration parameters for the query treatment.
    """
    def __init__(self, **config):
        """
        Initializes the query treatment with the provided configuration settings.
        
        Args:
            **config (dict): Arbitrary keyword arguments containing configuration options for the query treatment.
        """
        pass

    @abstractmethod
    def __call__(self, sentence: str) -> Answer:
        """
        Transforms the input sentence into a new format or representation as defined by the specific implementation.
        This method must be overridden by all subclasses of AbstractQT.
        
        Args:
            sentence (str): The input sentence to transform.
        
        Returns:
            str: The transformed version of the input sentence.
        
        Raises:
            NotImplementedError: If this method is not overridden by a subclass.
        """
        pass
