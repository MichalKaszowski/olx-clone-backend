import os
import time
import uuid
import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Mini-OLX API")

# Konfiguracja CORS (niezbędna, gdy frontend i backend są hostowane niezależnie)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Modele danych ---
class QuestionCreate(BaseModel):
    author: str
    content: str


class Question(QuestionCreate):
    id: str


class ItemCreate(BaseModel):
    title: str
    description: str
    price: float
    image_filename: Optional[str] = None


class Item(ItemCreate):
    id: str
    questions: List[Question] = []


# Tymczasowa baza danych w pamięci (w pkt 8 podmienisz ją na AWS RDS lub DynamoDB)
ITEMS_DB: List[Item] = [
    Item(id="1",
         title="Podręcznik do chmury AWS",
         description="Stan idealny, przydatny do projektu.",
         price=45.0,
         image_filename=None,
         questions=[
             Question(id="q1",
                      author="Janek",
                      content="Czy ogłoszenie jest aktualne?")
         ])
]


# 1. Endpoint GET #1 - Pobranie listy ogłoszeń (+ opcjonalne opóźnienie pod CloudWatch)
@app.get("/items", response_model=List[Item])
def get_items(simulate_delay: bool = Query(
    False, description="Symulacja opóźnienia dla CloudWatch")):
    if simulate_delay:
        time.sleep(3)  # Sztuczne opóźnienie 3 sekundy
    return ITEMS_DB


# 2. Endpoint GET #2 - Pobranie szczegółów pojedynczego ogłoszenia
@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: str):
    for item in ITEMS_DB:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404,
                        detail="Ogłoszenie nie zostało znalezione")


# 3. Endpoint POST #1 - Dodanie nowego ogłoszenia
@app.post("/items", response_model=Item, status_code=201)
def create_item(item_data: ItemCreate):
    new_item = Item(id=str(uuid.uuid4())[:8],
                    **item_data.model_dump(),
                    questions=[])
    ITEMS_DB.insert(0, new_item)
    return new_item


# 4. Endpoint POST #2 - Zadanie pytania do ogłoszenia
@app.post("/items/{item_id}/questions",
          response_model=Question,
          status_code=201)
def add_question(item_id: str, question_data: QuestionCreate):
    for item in ITEMS_DB:
        if item.id == item_id:
            new_question = Question(id=str(uuid.uuid4())[:8],
                                    **question_data.model_dump())
            item.questions.append(new_question)
            return new_question
    raise HTTPException(status_code=404,
                        detail="Ogłoszenie nie zostało znalezione")


# 5. Endpoint multimedialny POST - Przesłanie zdjęcia przedmiotu (w pkt 7 podmienisz na AWS S3)
@app.post("/images")
def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": unique_filename}


# 6. Endpoint multimedialny GET - Pobranie/wyświetlenie zdjęcia przedmiotu
@app.get("/images/{filename}")
def get_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Plik nie istnieje")
    return FileResponse(file_path)
