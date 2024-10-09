from fastapi import FastAPI
from utilities.response import JSONResponse
from utilities.database import Database
from routes.client import router

app = FastAPI()
db = Database()


@app.get("/")
async def index():
    return JSONResponse(
        content={"success": True, "message": "All Modules loaded successfully"}
    )

app.include_router(router, prefix="/client")