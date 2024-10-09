from fastapi import HTTPException, APIRouter
from utilities.database import Database

router=APIRouter()
db = Database()

@router.post("/")
async def create_client(client_data: dict):
    # Insert new  data
    result = db.clients.insert_one(client_data)
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="Failed to create client")
    return {"message": "Client created", "client_id": str(result.inserted_id)}

@router.get("/{client_id}")
async def read_client(client_id: str):
    client = db.clients.find_one({"_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}")
async def update_client(client_id: str, client_data: dict):

    result = db.clients.update_one({"_id": client_id}, {"$set": client_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client updated"}

@router.delete("/{client_id}")
async def delete_client(client_id: str):

    result = db.clients.delete_one({"_id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted"}
