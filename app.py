from fastapi import FastAPI
from utilities.response import JSONResponse
from utilities.database import Database
from routes.client import router
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import chat_router

app = FastAPI()
db = Database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index():
    return JSONResponse(
        content={"success": True, "message": "All Modules loaded successfully"}
    )


app.include_router(router, prefix="/client")
app.include_router(chat_router, prefix="/chat")