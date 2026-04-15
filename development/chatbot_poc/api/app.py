from fastapi import FastAPI

from development.chatbot_poc.api.config import Settings
from development.chatbot_poc.api.routes import router


app = FastAPI(
    title="Document Knowledgebase API",
    version=Settings.from_env().API_VERSION,
)
app.include_router(router)
