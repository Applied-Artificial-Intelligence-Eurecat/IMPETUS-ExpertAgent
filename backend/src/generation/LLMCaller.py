from . import AbstractLLM

class LLMCaller:
    """
    A wrapper class designed to facilitate calls to an instance of AbstractLLM. This class abstracts the
    complexity of making asynchronous or synchronous calls to a language model by delegating the execution
    to an AbstractLLM instance.

    Attributes:
        llm (AbstractLLM): An instance of AbstractLLM used to process natural language inputs.
    """
    llm = None
    def __init__(self, llm: AbstractLLM) -> None:
        """
        Initializes the LLMCaller with a specific instance of AbstractLLM.
        
        Args:
            llm (AbstractLLM): An instance of the language model class that adheres to the AbstractLLM interface.
        """
        self.llm = llm

    def __call__(self, sentence: str, query_id) -> str:
        """
        Processes a sentence using the provided AbstractLLM instance and returns the result. This method
        simplifies making calls to the language model, encapsulating whether the call is asynchronous or synchronous
        within the provided AbstractLLM logic.
        
        Args:
            sentence (str): The input sentence to be processed by the language model.
        
        Returns:
            str: The output from the language model as a response to the input sentence.
        """
        return self.llm(sentence, query_id)
