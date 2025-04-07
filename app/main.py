from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import User, UpdateUser, UserOut
from db import db
import uuid
from typing import List

app = FastAPI()

@app.post("/users/", response_model=UserOut)
def create_user(user: User):
    user_id = str(uuid.uuid4())
    doc = {
        "_id": user_id,
        "username": user.username,
        "email": user.email,
    }
    db.save(doc)
    return {"id": user_id, "username": user.username, "email": user.email}


@app.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: str):
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    doc = db[user_id]
    return {"id": doc["_id"], "username": doc["username"], "email": doc["email"]}


@app.get("/users/", response_model=List[UserOut])
def list_users(skip: int = 0, limit: int = 10):
    results = []
    count = 0
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("deleted"):
            continue  # Skip soft-deleted users
        if count < skip:
            count += 1
            continue
        if len(results) >= limit:
            break
        results.append({
            "id": doc["_id"],
            "username": doc.get("username"),
            "email": doc.get("email")
        })
    return results


@app.exception_handler(HTTPException)
def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.delete("/users/{user_id}")
def soft_delete_user(user_id: str):
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    doc = db[user_id]
    if doc.get("deleted"):
        raise HTTPException(status_code=400, detail="User already deleted")
    doc["deleted"] = True
    db.save(doc)
    return {"message": "User marked as deleted"}

@app.get("/users/export/json")
def export_users_json():
    users = []
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("deleted"):
            continue
        users.append({
            "id": doc["_id"],
            "username": doc.get("username"),
            "email": doc.get("email")
        })
    return JSONResponse(content=users)