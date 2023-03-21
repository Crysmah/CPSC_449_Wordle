import contextlib
import logging.config
import sqlite3
import uuid
import redis
import json


from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, BaseSettings

sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
sqlite3.register_adapter(uuid.UUID, lambda u: memoryview(u.bytes_le))

class Settings(BaseSettings):
    stat_database: str
    logging_config: str

    user_database: str
    game1_database: str
    game2_database: str
    game3_database: str

    class Config:
        env_file = ".env"

def get_user_db():
    with contextlib.closing(sqlite3.connect(settings.user_database, detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        db.row_factory = sqlite3.Row
        yield db

def get_game1_db():
    with contextlib.closing(sqlite3.connect(settings.game1_database, detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        db.row_factory = sqlite3.Row
        yield db

def get_game2_db():
    with contextlib.closing(sqlite3.connect(settings.game2_database, detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        db.row_factory = sqlite3.Row
        yield db

def get_game3_db():
    with contextlib.closing(sqlite3.connect(settings.game3_database, detect_types=sqlite3.PARSE_DECLTYPES)) as db:
        db.row_factory = sqlite3.Row
        yield db

def get_logger():
    return logging.getLogger(__name__)

client_redis = redis.Redis()
settings = Settings()
app = FastAPI(root_path="/games")

logging.config.fileConfig(settings.logging_config)

# Start a new game
@app.post("/start", status_code=status.HTTP_201_CREATED)
def start_game(
    username: str,
    game_id: int,
    user_db: sqlite3.Connection = Depends(get_user_db),
    game1_db: sqlite3.Connection = Depends(get_game1_db),
    game2_db: sqlite3.Connection = Depends(get_game2_db),
    game3_db: sqlite3.Connection = Depends(get_game3_db)
):
    # Check if user_id is valid in user_db
    #user_id = uuid.UUID(user_id)
    # Check whether user_id exists in the user database or not
    player = user_db.execute("SELECT * FROM users WHERE username = ?",[username]).fetchall()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )
    for play in player:
      user_id = play[0]


    # If the user has already played the game, they should receive an error.
    # Choose the correct shard for this user_id
    if int(user_id) % 3 == 1:
        db = game1_db
    elif int(user_id) % 3 == 2:
        db = game2_db
    else:
        db = game3_db

    game = db.execute("SELECT * FROM games WHERE user_id = ? AND game_id = ?", [user_id, game_id]).fetchall()
    if game:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already played this game"
        )

    # Start a new game and save its state in redis db
    new_game_key = str(user_id) + str(game_id)

    # Check if this game is already in progress
    current_game = client_redis.get(new_game_key)
    if current_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game in progress"
        )

    new_game = {"user_id" : str(user_id), "game_id" : game_id, "guess1" : None, "guess2" : None, 'guess3' : None, 'guess4' : None, 'guess5' : None, 'guess6' : None, "remain_guess" : 6}
    client_redis.set(new_game_key, json.dumps(new_game))

    return new_game

# Update the state of a game
@app.post("/update")
def update_game(
    user_id: str,
    game_id: int,
    guess: str,
):
    game_key = user_id + str(game_id)
    current_game = client_redis.get(game_key)

    # Check if this game exists
    if not current_game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    current_game = json.loads(current_game.decode('utf-8'))
    remain_guess = current_game['remain_guess']


    if remain_guess < 1:
        # If a user tries to guess more than
        # six times, they should receive an error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request exceeded allowed guess limit"
        )
    else:
        # When a user makes a new guess for a game,
        # record the guess and update the number of guesses remaining.
        guess_num = 6 - remain_guess + 1
        current_game[f'guess{str(guess_num)}'] = guess
        current_game['remain_guess'] = remain_guess - 1
        client_redis.set(game_key, json.dumps(current_game))

    return current_game

# Restoring the state of a game.
@app.get("/restore")
def retrieve_game(
    user_id: str,
    game_id: int,
):
    game_key = user_id + str(game_id)
    restore_game = client_redis.get(game_key)

    # Check if this game exists
    if not restore_game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    restore_game = json.loads(restore_game.decode('utf-8'))

    return restore_game
