from minio import Minio
from dotenv import load_dotenv
import os

load_dotenv()

client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False,
)

bucketName = os.getenv("MINIO_BUCKET_NAME")
if not client.bucket_exists(bucketName):
    client.make_bucket(bucketName)
