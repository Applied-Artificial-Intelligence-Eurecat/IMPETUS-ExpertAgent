from .AbstractLLM import AbstractLLM
from src.api.config.config import settings
from src.broker.ContextBroker import ContextBroker

from requests.exceptions import RequestException, ConnectionError
import requests

import contextlib
import time
import re
import io


from langchain_community.llms import LlamaCpp
from src.api.config.config import settings

class ModelNotLoadedError(Exception):
    pass

class LLM(AbstractLLM):
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLM, cls).__new__(cls)
        return cls._instance

    """
    A specific implementation of the AbstractLLM class that uses LlamaCpp, a C++ backend for language models.
    This class configures and manages an instance of the LlamaCpp model for processing natural language inputs.
    
    Attributes:
        llm (LlamaCpp): The underlying language model powered by LlamaCpp.
    """
    def __init__(self):
        """
        Initializes the LLM model with specific parameters for the LlamaCpp backend.
        
        Args:
            model_path (str): Path to the model's files.
            n_gpu_layers (int, optional): Number of GPU layers to use. Defaults to 250.
            temperature (float, optional): Sampling temperature. Defaults to 0.01.
            max_tokens (int, optional): Maximum number of tokens to process in a single call. Defaults to 1024.
            n_batch (int, optional): Batch size for processing. Defaults to 1024.
            n_ctx (int, optional): Context size (number of tokens) the model can handle. Defaults to 4096.
            verbose (bool, optional): Enable verbose logging. Defaults to False.
            use_mlock (bool, optional): Whether to use mlock to prevent swapping. Defaults to True.
            streaming (bool, optional): Enable streaming mode for continuous input processing. Defaults to False.
            seed (int, optional): Random seed for initialization. Defaults to 42.
        """

        if not self._initialized:
            super().__init__()
            self.config = self._load_config()
            self._initialized = True 


    def _load_config(self):
        try:
            return settings.load_component_yml("LLM_CONFIG_PATH")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}")


    def _log_llm_parameters(self, query_id):
        time.sleep(0.1)
        ContextBroker().publish(
            identity=query_id, topic="logging", value={"llm_tag":self.llm.model_path, "max_tokens": self.llm.max_tokens,
                                                       "n_ctx": self.llm.n_ctx, "top_k":self.llm.top_k,
                                                       "n_gpu_layers":self.llm.n_gpu_layers,
                                                       "repeat_penalty":self.llm.repeat_penalty,
                                                       "temperature":self.llm.temperature,
                                                       "top_p":self.llm.top_p,
                                                       }
        )
        time.sleep(0.2)

    def _log_llm_timings(self, query_id, timings_dict):
        time.sleep(0.1)
        ContextBroker().publish(
            identity=query_id, topic="logging", value=timings_dict
        )
        time.sleep(0.2)

    def subquestion_process(self, sentence):
        subquestion_prompt_template  = """Given a complex question, break it down into a set of sub-questions, while identifying the appropriate data source and retrieval function for each sub-question.\nQuestion: {question}\nOnly return the subquestions below and nothing else.\nSubquestions:"""
        prompt = subquestion_prompt_template.format(question=sentence)
        response = self.llm.invoke(prompt)
        return response
        
    def send_question_to_TGI(self, question, parameters):
        try:
            headers = {"Content-Type": "application/json",}
            data = {
                'inputs': question,
                'parameters': parameters
            }
            url = "http://TGI:80"
            response = requests.post(url, headers=headers, json=data)

            return response.json()[0]['generated_text']
        except ConnectionError as ce:
            print("Model still not ready.", ce)
            return None
        except Exception as e:
            print("Response failed due to unexpected error: ", e)
            return "Response failed due to an unexpected error."


    def __call__(self, sentence: str, query_id) -> str:
        """
        Process a sentence using the LlamaCpp language model and return the model's generated response.
        
        Args:
            sentence (str): The input sentence to process.
        
        Returns:
            str: The output response from the language model.
        """
        parameters =  {'max_new_tokens': 2, 'repetition_penalty':1.1, 'temperature':0.01, "top_k":50, "top_p":0.9, "return_full_text":False}
        response = self.send_question_to_TGI(sentence, parameters)
        if not response:
            raise ModelNotLoadedError() 


        return response

