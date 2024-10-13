from fastapi import HTTPException, APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from utilities.database import Database
from schema.schema import CreateClient, UpdateClient
from utilities.response import JSONResponse
from bson import ObjectId
from minio.error import S3Error
from utilities.minio import client
from dotenv import load_dotenv
from io import BytesIO
from slugify import slugify
import os

router = APIRouter()
db = Database()
load_dotenv()


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


@router.post("/{client_id}/nda/upload")
async def upload_file(client_id: str, file: UploadFile = File(...)):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    try:
        content = await file.read()
        file_name = slugify(file.filename)
        file_data = BytesIO(content)
        client.put_object(
            bucket_name=bucket_name,
            object_name=f"{client_id}/nda/{file_name}",
            data=file_data,
            length=len(content),
            content_type=file.content_type,
        )
        db.clients.update_one(
            {"_id": client_id},
            {
                "$addToSet": {
                    "documents": {
                        "name": file_name,
                        "path": f"{client_id}/nda/{file_name}",
                        "slug": file_name,
                    }
                }
            },
        )
        return {"message": f"File '{file.filename}' uploaded successfully!"}
    except S3Error as err:
        raise HTTPException(status_code=500, detail=f"MinIO error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.get("/{client_id}/nda/{slug}")
async def download_file(client_id: str, slug: str):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    object_name = f"{client_id}/nda/{slug}"
    try:
        data = client.get_object(bucket_name, object_name)
        return StreamingResponse(
            data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={slug}"},
        )
    except S3Error as err:
        raise HTTPException(status_code=404, detail=f"File not found: {str(err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")


@router.get("/")
async def read_clients():
    clients = db.clients.find()
    clients = [client for client in clients]
    for client in clients:
        client["_id"] = str(client["_id"])
    return JSONResponse(content=clients)


@router.post("/{client_id}/lawsuit/upload")
async def upload_file(client_id: str, file: UploadFile = File(...)):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    try:
        content = await file.read()
        file_name = slugify(file.filename)
        file_data = BytesIO(content)
        client.put_object(
            bucket_name=bucket_name,
            object_name=f"{client_id}/lawsuit/{file_name}",
            data=file_data,
            length=len(content),
            content_type=file.content_type,
        )
        db.clients.update_one(
            {"_id": client_id},
            {
                "$addToSet": {
                    "documents": {
                        "name": file_name,
                        "path": f"{client_id}/lawsuit/{file_name}",
                        "slug": file_name,
                    }
                }
            },
        )
        return {"message": f"File '{file.filename}' uploaded successfully!"}
    except S3Error as err:
        raise HTTPException(status_code=500, detail=f"MinIO error: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.get("/{client_id}/lawsuit/{slug}")
async def download_file(client_id: str, slug: str):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    object_name = f"{client_id}/lawsuit/{slug}"
    try:
        data = client.get_object(bucket_name, object_name)
        return StreamingResponse(
            data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={slug}"},
        )
    except S3Error as err:
        raise HTTPException(status_code=404, detail=f"File not found: {str(err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")


@router.delete("/{client_id}/nda/{slug}")
async def delete_nda_file(client_id: str, slug: str):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")

    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    object_name = f"{client_id}/nda/{slug}"

    try:
        client.remove_object(bucket_name, object_name)
    except S3Error as err:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

    result = db.clients.update_one(
        {"_id": client_id},
        {"$pull": {"documents": {"slug": slug}}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="File not found in the database")

    return JSONResponse(content={"message": f"File '{slug}' deleted successfully!"})


@router.delete("/{client_id}/lawsuit/{slug}")
async def delete_lawsuit_file(client_id: str, slug: str):
    try:
        client_id = ObjectId(client_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID format")

    bucket_name = os.getenv("MINIO_BUCKET_NAME")
    object_name = f"{client_id}/lawsuit/{slug}"

    try:
        client.remove_object(bucket_name, object_name)
    except S3Error as err:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

    result = db.clients.update_one(
        {"_id": client_id},
        {"$pull": {"documents": {"slug": slug}}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="File not found in the database")

    return JSONResponse(content={"message": f"File '{slug}' deleted successfully!"})
