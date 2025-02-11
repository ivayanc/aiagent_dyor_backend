from api.routes import router  # Import the router from api/routes.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from connectors.mongodb import MongoDBConnector
from settings import MONGODB_URL, ALLOWED_ORIGINS

@asynccontextmanager
async def lifespan(app: FastAPI):
    await MongoDBConnector.connect(MONGODB_URL)
    yield
    await MongoDBConnector.close()

app = FastAPI(lifespan=lifespan)

# Add this after creating the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(router)
