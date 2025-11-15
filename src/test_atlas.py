from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from os import getenv

load_dotenv()
uri = getenv("MONGODB_URI")

# Créez un nouveau client et connectez-vous au serveur
client = MongoClient(uri, server_api=ServerApi('1'))

# Envoyez un ping pour confirmer une connexion réussie
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)