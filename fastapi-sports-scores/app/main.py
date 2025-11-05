from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints.scores import router as scores_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scores_router, prefix="/api", tags=["scores"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Sports Scores API"}