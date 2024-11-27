from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query

from typing import List, Any, Optional
from pydantic import BaseModel

from abc import ABC, abstractmethod
from src.qtm.QTCaller import QTCaller
from src.qtm.QT import QT
from src.qtm.Answer import Answer
from src.qtm.AbstractQT import AbstractQT
from src.broker.ContextBroker import ContextBroker
from ..schemas.schemas import ThumbsFeedback
from ..auth.auth import verify_token
from ..models.models import FeedbackInput
from src.retrieval.AbstractRA import DocumentObject
from src.utils.utils import get_title_from_document
from src.generation.LLM import ModelNotLoadedError
from src.api.schemas.schemas import Answer, LLMQuery
from src.api.auth.auth import is_bearer_token_authorised, get_session
from fastapi import Request
from fastapi.responses import JSONResponse


from datetime import datetime
import os
import time
import logging
import torch
import gc

router = APIRouter()

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BLACK = "\033[30m"
WHITE_SHINY = "\033[7m"
BLUE_SHINY_BACK = "\033[104m"
GREEN_BACK = "\033[42m"
WHITE_SHINY_BACK = "\033[107m"



@router.post("/query")
async def send_query_to_RAG(query: LLMQuery, request: Request,
                                       session_id: str = Depends(get_session),
                                       token: str = Depends(is_bearer_token_authorised)):
    from src.api.main import app

    db_name = app.state.db_name
    identity = ContextBroker.get_new_uuid()
    
    logging.getLogger(__name__).info(f"{identity} Query: {BLACK}{GREEN_BACK}{query.query_message}{RESET}")

    cb = ContextBroker()
    cb.overwrite_db(db_name)
    _ = ContextBroker().subscribe(identity, permanent_hear=True)

    ContextBroker().publish(
        identity=identity, topic="logging", value={"raw_query": query.query_message, "owner":session_id}
    )

    qt_caller = QTCaller(QT())
    try:
        qt_answer = qt_caller(query.query_message, identity)
    except ModelNotLoadedError:
        print("MODEL STILL NOT LOADED") 
        response_payload = {
            "status": "starting",
            "message": "The RAG service starting up. Please, try again in a few moments."
        }
        return JSONResponse(content=response_payload, status_code=202)

    logging.getLogger(__name__).info(f"{identity} Response:{BLUE_SHINY_BACK}{BLACK}{qt_answer.content}{RESET}")

    time.sleep(0.01)
    ContextBroker().publish(
        identity=identity, topic="logging", value={"end_time":datetime.now()}
    )
    time.sleep(0.01)

    _ = cb.unsubscribe(identity).pop()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache() 
    # documents = [{"title": get_title_from_document(document), "content":[document.content], "href":document.source.metadata["source"]} for document in qt_answer.metadata.documents]
    documents = [{"title": get_title_from_document(document), "content":[document.source.metadata.get("cleaned_context") if document.source.metadata.get("cleaned_context") is not None else document.content], "href":document.source.metadata["source"]} for document in qt_answer.metadata.documents]


    for i,d in enumerate(documents):
        logging.getLogger(__name__).info(f"{identity} Document {i}:\n{BLACK}{WHITE_SHINY_BACK}{d.get('title')}\n{d.get('content')[0]}\n{d.get('href')}{RESET}")


    return Answer(status="Successful",
                    content=qt_answer.content,
                    query_id=identity,
                    documents=documents,
                    datetime=(datetime.now()).isoformat() + "Z")

@router.get("/chat_list", response_model=List[dict])
async def read_items(page: int = Query(0, ge=0), page_size: int = Query(5, le=100),
                                session_id: str = Depends(get_session),
                                token: str = Depends(is_bearer_token_authorised)):
    """
    Endpoint to paginate through a list of strings.
    - page: int = current page number.
    - page_size: int = number of items per page, maximum of 100.
    """
    from src.api.main import app

    try:
        logger = app.state.logger
        session_logs = logger.get_logs_by_owner(session_id)
        
    except Exception as e:
        print('No owner found')
        session_logs = []

    chats = [{"query_id":log.id, "raw_query":log.raw_query} for log in session_logs]
    return chats[page:page+page_size]

@router.get("/chat/{query_id}")
async def get_chat(query_id: str ,
                   token: str = Depends(is_bearer_token_authorised)):
    """
    Endpoint to get a specific chat by its query id
    - query_id: str - query identifier
    """
    from src.api.main import app

    try:
        logger = app.state.logger
        query_log = logger.get_log_by_id(query_id)
        document_list_log = logger.get_documents_by_log_id(query_id)
        chat = {
            "query_id": query_id,
            "user_message": query_log.raw_query,
            "system_message": query_log.response,
            "documents": [{"title":document_log.title.replace("\n", " "),
                        "content":document_log.content,
                        "href": document_log.href.replace('/app/data/', "")} 
                        for document_log in document_list_log],

            "datetime": query_log.start_time,
            "thumbs": query_log.feedback, 
        }
    except Exception as e:
        print("EXCEPTION WHILE PROCESSING CHAT")
        chat = None

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.post("/feedback")
async def handle_feedback(feedback_input: FeedbackInput,
                          token: str = Depends(is_bearer_token_authorised)):
    """
    Receives feedback for a specific query, thumbs up or down.
    Input:
        - feedback_input: FeedbackInput 
                            - id_query : str = query identifyer 
                            - feedback : Literal['up', 'down', None] = feedback can be 'up', 'donw', or no feedback (which means
                                that the user removed previous feedback).
            
    """
    from src.api.main import app

    logger = app.state.logger
    logger.update_log_by_id(feedback_input.id_query, feedback=feedback_input.feedback)

    return {"message": "Feedback received successfully"}







@router.post("/query_mocked")
async def send_query_to_RAG_mocked(query: LLMQuery, request: Request,
                                       session_id: str = Depends(get_session),
                                       token: str = Depends(is_bearer_token_authorised)):
    from src.api.main import app
    from src.retrieval.RA import RA
    from src.retrieval.RACaller import RACaller

    db_name = app.state.db_name
    identity = ContextBroker.get_new_uuid()

    cb = ContextBroker()
    cb.overwrite_db(db_name)
    _ = ContextBroker().subscribe(identity, permanent_hear=True)



    # qt_caller = QTCaller(QT())
    # qt_answer = qt_caller(query.query_message, identity)

    # racaller = RACaller(RA())

    # ContextBroker().publish(
    #     identity=identity, topic="logging", value={"raw_query": query.query_message, "owner":session_id}
    # )
    documents = [{"id":ContextBroker.get_new_uuid(),"title":"Titletitletitle", "content":"Contentcontentcontentcontentcontentcontent", "href":"example.pdf", "similarity":0.8},
                                                   {"id":ContextBroker.get_new_uuid(),"title":"Titletitletitle22222", "content":"Contentcontentcontentcontentcontentcontent22222", "href":"example222.pdf"}]

    ContextBroker().publish(
        identity=identity, topic="logging", value={"raw_query": query.query_message, "owner":session_id,
                                                   "response": "mocked_response", "start_time":datetime.now(),
                                                   "documents":documents}
    )

    query_id = "29f0b561-1730-4a6e-86a3-ef7303bfab4c"
    logger = app.state.logger
    document_list_log = logger.get_documents_by_log_id(query_id)
    # documents = [{"title":document_log.title.replace("\n", " "),
    #                    "content":document_log.content,
    #                    "href": document_log.href.replace('/app/data/', "")} 
    #                  for document_log in document_list_log]



    time.sleep(0.01)
    ContextBroker().publish(
        identity=identity, topic="logging", value={"end_time":datetime.now()}
    )
    time.sleep(0.01)

    _ = cb.unsubscribe(identity).pop()
    gc.collect()  # Force garbage collection
    if torch.cuda.is_available():
        torch.cuda.empty_cache() 

    return Answer(status="Successful",
                    # content=qt_answer.content,
                    content="Mocked Answer",
                    query_id=identity,
                    # documents=[{"title": get_title_from_document(document), "content":[document.content], "href":document.source.metadata["source"]} for document in qt_answer.metadata.documents],
                    documents=documents,
                    datetime=(datetime.now()).isoformat() + "Z")