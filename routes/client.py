from fastapi import HTTPException, APIRouter
from utilities.database import Database
from schema.schema import CreateClient, UpdateClient
from utilities.response import JSONResponse
from bson import ObjectId

router = APIRouter()
db = Database()


@router.post("/")
async def create_client(clientData: CreateClient):
    result = db.clients.insert_one(clientData.dict())
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="Failed to create client")
    return JSONResponse(
        content={"message": "Client created", "client_id": str(result.inserted_id)}
    )


@router.get("/{client_id}")
async def read_client(client_id: str):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    client = db.clients.find_one({"_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client["_id"] = str(client["_id"])
    return JSONResponse(content=client)


@router.put("/{client_id}")
async def update_client(client_id: str, client_data: UpdateClient):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")

    result = db.clients.update_one(
        {"_id": client_id}, {"$set": {"name": client_data.name}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return JSONResponse(content={"message": "Client updated"})


@router.delete("/{client_id}")
async def delete_client(client_id: str):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")

    result = db.clients.delete_one({"_id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return JSONResponse(content={"message": "Client deleted"})
