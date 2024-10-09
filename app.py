from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get('/')
async def index():
    return JSONResponse({"success": True, "message": "All Modules loaded successfully"})
