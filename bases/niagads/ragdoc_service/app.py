import uvicorn
from fastapi import FastAPI
from niagads.ragdoc_service.config import Settings
from niagads.ragdoc_service.routes import router

app = FastAPI(
    title="Document Knowledgebase API",
    version=Settings.from_env().API_VERSION,
)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app="app:app")
