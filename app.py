from fastapi import FastAPI
from utilities.response import JSONResponse
from utilities.database import Database

app = FastAPI()
db = Database()


@app.get("/")
async def index():
    return JSONResponse(
        content={"success": True, "message": "All Modules loaded successfully"}
    )
