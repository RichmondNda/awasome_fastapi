import couchdb
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get env values
COUCHDB_USER = os.getenv('COUCHDB_USER')
COUCHDB_PASSWORD = os.getenv('COUCHDB_PASSWORD')
COUCHDB_URL = os.getenv('COUCHDB_URL')
DB_NAME = os.getenv('COUCHDB_DB_NAME')

# Setup CouchDB connection
full_url = f"http://{COUCHDB_USER}:{COUCHDB_PASSWORD}@{COUCHDB_URL.split('://')[1]}"
couch = couchdb.Server(full_url)

# Create or get the database
if DB_NAME in couch:
    db = couch[DB_NAME]
else:
    db = couch.create(DB_NAME)
