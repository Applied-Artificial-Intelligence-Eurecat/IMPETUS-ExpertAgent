from abc import ABC, abstractmethod

class AbstractLLM(ABC):
    """
    Abstract base class for a language model. This class provides a template for language models,
    ensuring that all derived models implement the required methods as specified.
    
    Attributes:
        config (dict): Configuration parameters for the language model.
    """
    def __init__(self, **config):
        """
        Initializes the language model with the provided configuration settings.
        
        Args:
            **config (dict): Arbitrary keyword arguments containing configuration options for the language model.
        """
        self.config = config

    @abstractmethod
    def __call__(self, sentence: str) -> str:
        """
        Processes the input sentence and returns the model's response. This method must be implemented
        by all subclasses of AbstractLLM.
        
        Args:
            sentence (str): The input sentence to process.
        
        Returns:
            str: The processed output from the language model.
        
        Raises:
            NotImplementedError: If this method is not overridden by a subclass.
        """
        pass