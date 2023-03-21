import contextlib
import logging.config
from operator import countOf
import sqlite3


from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseSettings


class Settings(BaseSettings):
    answer_database: str
    logging_config: str

    class Config:
        env_file = ".env"

def get_db():
    with contextlib.closing(sqlite3.connect(settings.answer_database)) as db:
        db.row_factory = sqlite3.Row
        yield db


def get_logger():
    return logging.getLogger(__name__)


settings = Settings()
app = FastAPI(root_path="/guess")

logging.config.fileConfig(settings.logging_config)

@app.get("/check")
def check_guess(
    game_id: int,
    guess: str,
    db: sqlite3.Connection = Depends(get_db)
):
    answer = ""
    for row in db.execute("SELECT * FROM answers WHERE game_id = ? LIMIT 1", [game_id]):
        answer = row['answer']

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    response_list = []


    for i in range(len(guess)):
        if guess[i] == answer[i]:
            response_list.append({"correct" : f"{guess[i]}"})
        elif guess[i] in answer:
            response_list.append({"present" : f"{guess[i]}"})

    if not response_list:
      response_list.append({"status": "incorrect"})

    return {"response": response_list}

@app.post("/add_answer", status_code=status.HTTP_201_CREATED)
def add_asnwer(
    answer: str,
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        cur =  db.execute("INSERT INTO answers(answer) VALUES(?)", [answer])
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"type": type(e).__name__, "msg": str(e)},
        )
    new_answer_id = cur.lastrowid
    return {"id": f"{new_answer_id}", "answer": f"{answer}"}

@app.patch("/change_answer")
def change_answer(
    game_id: int,
    new_answer: str,
    db: sqlite3.Connection = Depends(get_db)
):
    cur =  db.execute("SELECT * FROM answers WHERE game_id = ? LIMIT 1", [game_id])
    answers = cur.fetchall()

    if not answers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    try:
        cur =  db.execute("UPDATE answers SET answer = ? WHERE game_id = ?", [new_answer, game_id])
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"type": type(e).__name__, "msg": str(e)},
        )
    return {"game_id": f"{game_id}", "answer": f"{new_answer}"}
