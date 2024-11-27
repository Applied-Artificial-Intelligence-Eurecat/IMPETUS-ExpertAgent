from .AbstractQT import AbstractQT
from src.api.config.config import settings
from src.generation.LLMCaller import LLMCaller
from src.generation.LLM import LLM
from src.retrieval.RACaller import RACaller
from src.retrieval.RA import RA
from src.api.config.config import settings
from .Answer import Answer
from .Metadata import FaissMetadata
from src.broker.ContextBroker import ContextBroker
import time

SENTENCE_TOO_LONG_MESSAGE = "Your question is too long. Please shorten it to get a response."

class QT(AbstractQT):

    def __init__(self, **config):

        super().__init__()
        self.qtm_config = self._load_config()

        self.llmcaller = LLMCaller(LLM())
        self.racaller = RACaller(RA())

    def _load_config(self):
        """
        Loads the configuration for QTM component.

        Returns:
            dict: The QTM configuration.
        """
        try:
            return settings.load_component_yml("QTM_CONFIG_PATH")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}") from e

    def _is_sentence_too_long(self, sentence, max_characters):
        cleaned_sentence = ' '.join(sentence.split())
        return len(cleaned_sentence) > max_characters

    def __call__(self, sentence: str, query_id) -> Answer:
        if self._is_sentence_too_long(sentence, max_characters = 2000):
            return Answer(SENTENCE_TOO_LONG_MESSAGE, FaissMetadata([]))
        documents = self.racaller(sentence, query_id)
        content_strings = [f"Context {i}:\nSource:{doc.source}\n Content:{doc.content}" for i, doc in enumerate(documents)]
        combined_content = "\n".join(content_strings)

        prompt_template ="""You are an agent created to answer questions regarding the European project called IMPETUS.
        Context: {context}
        Question: {question}
        Give a small summary on what you found on the context, referencing its source. If a piece of context doesn't relate to the question, REFRAIN from using it. If the answer of the question is clear, give it.
        Summary & answer if clear:"""
        
        prompt = prompt_template.format(question=sentence, context=combined_content)
        answer = Answer(self.llmcaller(prompt, query_id), FaissMetadata(documents))

        ContextBroker().publish(
            identity=query_id, topic="logging", value={"response":answer.content, "prompt_template":prompt_template}
        )
        time.sleep(0.01)

        return answer

