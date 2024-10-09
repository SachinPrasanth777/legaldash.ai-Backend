from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import os

load_dotenv()


class Database:
    def __init__(self):
        db_name, db_uri = os.getenv("DB_NAME"), os.getenv("DB_URI")
        self.client = MongoClient(db_uri, tlsCAFile=certifi.where())
        self.db = self.client[db_name]
        self.clients = self.db.clients  
        self.lawsuits = self.db.lawsuits  


    def __del__(self):
        self.client.close()
