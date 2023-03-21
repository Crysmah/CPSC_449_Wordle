import contextlib
import logging.config
import sqlite3


from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseSettings


class Settings(BaseSettings):
    word_database: str
    logging_config: str

    class Config:
        env_file = ".env"

def get_db():
    with contextlib.closing(sqlite3.connect(settings.word_database)) as db:
        db.row_factory = sqlite3.Row
        yield db


def get_logger():
    return logging.getLogger(__name__)


settings = Settings()
app = FastAPI(root_path="/dict")

logging.config.fileConfig(settings.logging_config)

@app.get("/validate")
def validate_guess(
    guess : str,
    db: sqlite3.Connection = Depends(get_db)
):
    cur = db.execute("SELECT * FROM words WHERE word = ?", [guess])
    words = cur.fetchall()

    if len(guess) != 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{guess} not five letters."
        )
    elif not guess.isascii() or not guess.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{guess} not entirely letters."
        )
    elif not words:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{guess} not found in dictionary."
        )

    valid_guess = ""
    for word in words:
        valid_guess = word['word']
    return {"response": f"{valid_guess} is valid"}

@app.post("/add_guess", status_code=status.HTTP_201_CREATED)
def add_word(
    guess: str,
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        cur =  db.execute("INSERT INTO words(word) VALUES(?)", [guess])
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"type": type(e).__name__, "msg": str(e)},
        )

    new_word_id = cur.lastrowid
    return {"id": f"{new_word_id}", "word": f"{guess}"}

@app.delete("/remove_guess")
def remove_word(
    guess: str,
    db: sqlite3.Connection = Depends(get_db)
):
    cur = db.execute("SELECT * FROM words WHERE word = ? LIMIT 1", [guess])
    words = cur.fetchall()

    if not words:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Word not found"
        )

    cur =  db.execute("DELETE FROM words WHERE word = ?", [guess])
    db.commit()
    return {"response": f"Successfully removed {guess}"}
