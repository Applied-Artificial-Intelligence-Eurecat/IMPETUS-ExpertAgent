from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routers import query_router, user_router
from src.broker.ContextBroker import ContextBroker
from src.logger.SqliteLogger import SqliteLogger
from src.generation.LLM import LLM
from src.retrieval.RA import RA
from contextlib import asynccontextmanager
from sqlalchemy import text  

from googleapiclient.discovery import build

import asyncio
import logging
import time
import os


DATABASE_PATH = SqliteLogger.BASE_DB_PATH
DATABASE_NAME = "testing"
REMOVE_DB = False

shutdown_threshold = 60 * 60

last_request_time = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  
    handlers=[logging.StreamHandler()]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = DATABASE_PATH
    db_name = DATABASE_NAME
    db_filename = db_path + os.sep + db_name + ".db"
    if REMOVE_DB and os.path.exists(db_filename):
        os.remove(db_filename)
    logger = SqliteLogger(db_path, db_name, name="VanillaLogger")

    context_broker = ContextBroker(name="SingletonContextBroker")

    asyncio.create_task(check_inactivity())

    app.state.db_name = db_name 
    app.state.logger = logger  

    engine = logger.engine 

    with engine.connect() as connection:
        connection.execute(text("""
            CREATE VIEW IF NOT EXISTS combined_view AS
            SELECT 
                pl.id AS log_id,
                pl.raw_query,
                pl.response,
                pl.embedding_tag,
                pl.llm_tag,
                ds.id AS document_id,
                ds.title,
                ds.content,
                ds.href,
                ds.similarity
            FROM 
                prompt_logs pl
            LEFT JOIN 
                documents ds
            ON 
                pl.id = ds.parent_id;
        """))

    LLM() # Load the LLM an the Embedding model in GPU
    RA()


    yield

    cb = ContextBroker()
    cb.close()
    if logger is not None:
        logger.disconnect_db()
        if REMOVE_DB:
            logger._SqliteLogger__remove_db()

app = FastAPI(title="Impetus Expert Agent API",
              description="Impetus Expert Agent API",
              version="0.1.0",
              docs_url='/docs',
              root_path="/api",
              redoc_url='/redoc',
              lifespan=lifespan)



@app.middleware("http")
async def update_last_request_time(request: Request, call_next):
    """
    Middleware para registrar el tiempo de la última solicitud.
    Se ejecuta antes y después de procesar la solicitud HTTP.
    """
    global last_request_time

    excluded_paths = ["/health"]
    if request.url.path not in excluded_paths:
        last_request_time = time.time()

    response = await call_next(request)


    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)

app.include_router(user_router.router, prefix="/user", tags=["user"])
app.include_router(query_router.router, prefix="/query", tags=["query"])

@app.get("/health")
async def health_check():
    return {'status': 'ok 👍'}
    

@app.get("/shutdown")
async def shut_down():
    await shutdown_instance()
    return {'status': 'Server will shut down in a few seconds...'}

async def check_inactivity():
    global last_request_time

    while True:
        current_time = time.time()
        print(f'INFO:\tTime untill inactivity shutdown: {shutdown_threshold - (current_time - last_request_time)}', flush=True)
        if current_time - last_request_time > shutdown_threshold:
            await shutdown_instance()
            break
        await asyncio.sleep(60*5)

async def shutdown_instance():
    compute = build('compute', 'v1')
    project = ''
    zone = ''
    instance = ''

    request = compute.instances().stop(project=project, zone=zone, instance=instance)
    response = request.execute()
    print('INFO:\t Shutting down instance due to inactivity:',response, flush=True)


