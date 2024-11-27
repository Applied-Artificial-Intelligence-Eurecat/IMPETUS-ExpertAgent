# pylint: disable=C0103, W0238
from typing import List

from src.retrieval.Source import FaissSource
from src.api.config.config import settings

from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders.json_loader import JSONLoader
from langchain_community.document_loaders.markdown import UnstructuredMarkdownLoader
from langchain_community.document_loaders.pdf import PDFPlumberLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents.base import Document
from transformers import AutoModelForSequenceClassification, AutoTokenizer


from src.retrieval.builder import chunk_directory
from src.retrieval.AbstractRA import AbstractRA, DocumentObject
from src.broker.ContextBroker import ContextBroker
from src.api.config.config import settings
from src.generation.LLM import LLM
import torch

import os
import numpy as np
import json

ADDITIONAL_EMBEDDINGS_PATH = "/app/other_data/additional_embeddings/additional_embeddings.json"
CHUNK_DUMP_PATH = "/app/other_data/chunk_inspection/chunks.json"

class RA(AbstractRA):
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RA, cls).__new__(cls)
        return cls._instance

    """
    Retrieval agent for querying a vector database and returning relevant documents.
    """

    AVAILABLE_EXTENSIONS = {
        "pdf": PDFPlumberLoader,
        "md": UnstructuredMarkdownLoader,
        "txt": TextLoader,
        "json": JSONLoader,
    }

    def __init__(self):
        if not self._initialized:

            super().__init__()
            self.config = self._load_config()
            self.config['K'] = 20
            self.config['DEVICE'] = "cuda"
            self.config['CHUNK_SIZE'] = 512
            self.config['CHUNK_OVERLAP'] = 20
            self.model_name = "thenlper/gte-large"

            self.embeddings = self._initialize_embeddings()
            self.vector_db = self._load_vector_db()
            self.reranker, self.reranker_tokenizer = self._initialize_reranker()
            self._initialized = True 


            self.AVAILABLE_EXTENSIONS = {
                ext: entity
                for ext, entity in self.AVAILABLE_EXTENSIONS.items()
                if ext in self.config["ENABLED_EXTENSIONS"]
            }

    def _initialize_reranker(self):
        tokenizer = AutoTokenizer.from_pretrained(self.config['RERANK_TOKENIZER'], clean_up_tokenization_spaces=True)
        model = AutoModelForSequenceClassification.from_pretrained(self.config['RERANK_MODEL'])
        return model, tokenizer

    def _load_config(self):
        """
        Loads the configuration for retrieval.

        Returns:
            dict: The retrieval configuration.
        """
        try:
            return settings.load_component_yml("RETRIEVAL_CONFIG_PATH")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}") from e

    def _initialize_embeddings(self):
        """
        Initializes the embeddings model.

        Returns:
            HuggingFaceEmbeddings: The initialized embeddings model.
        """
        try:
            embedding_model_path = self.config["EMBEDDING_MODEL_PATH"]
            return HuggingFaceEmbeddings(
                model_name=embedding_model_path,
                model_kwargs={"device": "gpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as e:
            raise RuntimeError(f"Error initializing embeddings: {e}") from e

    def _load_vector_db(self):
        """
        Loads the vector database.

        Returns:
            FAISS: The loaded vector database.
        """
        try:
            vector_db_path = self.config["VECTOR_DB_PATH"]
            return FAISS.load_local(
                vector_db_path,
                self.embeddings,
                allow_dangerous_deserialization=self.config[
                    "ALLOW_DANGEROUS_DESERIALIZATION"
                ],
            )  
        except Exception as e:
            raise RuntimeError(f"Error loading vector database: {e}") from e

    def _transform_faiss_documents(self, faiss_document, similarity) -> DocumentObject:
        """
        Transforms a FAISS document into a DocumentObject.

        Args:
            faiss_document: The document returned by FAISS.

        Returns:
            DocumentObject: The transformed document.
        """
        content = faiss_document.page_content
        metadata = faiss_document.metadata
        source = FaissSource(metadata) if metadata else None
        return DocumentObject(content=content, source=source, cleaned_content=faiss_document.metadata["cleaned_context"],similarity=similarity)

    def add_document(self, filepath: str) -> List[str]:
            """Adds a new document to the already build vector DB

            Args:
                filepath (str): current local path of the document

            Returns:
                List[str] : The list of id chunks
            """
            ext = os.path.splitext(filepath)[1]
            loader_key = ext[1:]
            try:
                loader = self.AVAILABLE_EXTENSIONS[loader_key]
            except KeyError:
                return
            faiss_loader = loader(filepath)
            faiss_documents = faiss_loader.load()

            text_splitter = self.__get_text_splitter()
            texts = text_splitter.split_documents(faiss_documents)

            return self.vector_db.add_documents(texts)


    def rerank(self, query: str, documents: List[DocumentObject], top_n: int):
        pairs = [[query, document.content] for document in documents]
        encoded_input = self.reranker_tokenizer(pairs, padding=True, truncation=True, return_tensors='pt')
        with torch.inference_mode():
            scores = self.reranker(**encoded_input, return_dict=True).logits.view(-1, ).float().detach().numpy()
        scores = list(scores)
        scored_docs = list(zip(scores, documents))
        scored_docs = sorted(scored_docs, key=lambda x: x[0])

        return list(map(lambda x: x[1], scored_docs))[::-1][:top_n]

    def __call__(self, optimized_query: str, query_id) -> List[DocumentObject]:
        """
        Retrieves relevant documents based on optimized query.

        Args:
            optimized_query (str): The query to retrieve documents for.

        Returns:
            List[DocumentObject]: A list of relevant documents.
        """

        try:
            documents_with_similarities = self.vector_db.similarity_search_with_score(query=optimized_query, k=self.config['K'])

            documents = [
                self._transform_faiss_documents(doc, similarity) for doc, similarity in documents_with_similarities
            ]

            print('documents pre-rerank', len(documents))
            documents = self.rerank(optimized_query, documents, self.config['RERANK_TOP_N'])
            print('documents post-rerank', len(documents))


            documents_to_log = [{"id":ContextBroker.get_new_uuid(),"title":doc.content[:20]+"...", "content":doc.content, "href":repr(doc.source), "similarity":doc.similarity} for doc in documents]

            ContextBroker().publish(
                identity=query_id, topic="logging", value={"embedding_tag":self.model_name,
                                                           "documents": documents_to_log}
            )
            return documents
        except Exception as e:
            raise RuntimeError(f"Error retrieving documents: {e}") from e

    def add_additional_embeddings(self, path="/app/other_data/additional_embeddings/additional_embeddings.json"):
        vectordb_path = self.config["VECTOR_DB_PATH"] 

        with open(path, 'r') as f:
            additional_texts_dict = json.load(f)['additional_embeddings']
        
        documents = []

        for text_to_embed in additional_texts_dict:
            doc = Document(page_content=text_to_embed.get('context'),
                           metadata={'source':text_to_embed.get('source'),
                                     'file_path':"file_path",
                                     'page': 0,
                                     'total_pages':1,
                                     'Producer':"me",
                                     'ModDate':'D:20240828123056Z'}) 
            documents.append(doc)
            print(text_to_embed.get('context'))
            print(text_to_embed.get('source'))
            print("\n\n")
        

        embedding_model_path = self.config["EMBEDDING_MODEL_PATH"]

        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_path,
            model_kwargs={"device": self.config["DEVICE"]},
        )
        

        vectorstore = FAISS.from_documents(documents, embeddings)
        vectorstore.save_local(vectordb_path)
        print("database built successfully")


    def build_pdf_header_based(self, vectordb_path=None):
        """
        Method intended to build a new version of the Vector Database given the context
        which can be found in `retrieval_config.yml` file.
        """
        chunk_size = self.config["CHUNK_SIZE"]
        chunk_overlap = self.config["CHUNK_OVERLAP"]
        embedding_model_path = self.config["EMBEDDING_MODEL_PATH"]
        sources_path = self.config["DATA_PATH"]
        vectordb_path = (
            self.config["VECTOR_DB_PATH"] if vectordb_path is None else vectordb_path
        )

        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_path,
            model_kwargs={"device": self.config["DEVICE"]},
        )

        chunks = chunk_directory(sources_path, min_chars=900, max_chars=1100)

        with open(CHUNK_DUMP_PATH, 'w') as f:
            json.dump(chunks ,f)
            
        texts = []
        for chunk in chunks:
            doc = Document(page_content=chunk.get('text'),
                           metadata={'source':chunk.get('pdf_path'),
                                     'cleaned_context':None,
                                     'file_path':chunk.get('pdf_path'),
                                     'page': chunk.get('pages')[0],
                                     'total_pages':1,
                                     'Producer':"Impetus-parser",
                                     'ModDate':''}) 
            texts.append(doc)


        with open(ADDITIONAL_EMBEDDINGS_PATH, 'r') as f:
            additional_texts_dict = json.load(f)['additional_embeddings']
        for text_to_embed in additional_texts_dict:
            doc = Document(page_content=text_to_embed.get('context_to_embed'),
                           metadata={'source':text_to_embed.get('source'),
                                     'cleaned_context':text_to_embed.get("context_to_show"),
                                     'file_path':"",
                                     'page': 0,
                                     'total_pages':1,
                                     'Producer':"",
                                     'ModDate':'',
                                     }) 
            texts.append(doc)

        print("Number of chunks stored", len(texts))
        vectorstore = FAISS.from_documents(texts, embeddings)

        vectorstore.save_local(vectordb_path)
        print("database built successfully")
