import contextlib
import logging.config
import sqlite3
import uuid
import datetime
import redis


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

class Game(BaseModel):
    user_id: str
    game_id: int
    finished: datetime.date
    guesses: int
    won: bool

# Get different databases
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


settings = Settings()
app = FastAPI(root_path="/stats")
client_redis = redis.Redis()

logging.config.fileConfig(settings.logging_config)


# Post a new games
@app.post("/games/", status_code=status.HTTP_201_CREATED)
def insert_new_game(
    game: Game,
    user_db: sqlite3.Connection = Depends(get_user_db),
    game1_db: sqlite3.Connection = Depends(get_game1_db),
    game2_db: sqlite3.Connection = Depends(get_game2_db),
    game3_db: sqlite3.Connection = Depends(get_game3_db),
):
    print("<= request routed to this instance\n")
    g = dict(game)
    user_id = uuid.UUID(g['user_id'])

    # Check whether user_id exists in the user database or not
    player = user_db.execute("SELECT * FROM users WHERE user_id = ?", [user_id]).fetchall()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    # Make sure number of guesses is between 1 and 6
    if g["guesses"] < 1 or g["guesses"] > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid number of guesses"
        )

    # Choose the correct shard to insert a new game
    if int(user_id) % 3 == 1:
        db = game1_db
    elif int(user_id) % 3 == 2:
        db = game2_db
    else:
        db = game3_db

    # Make sure user_id is UUID in game class before inserting in games 
    g["user_id"]= user_id
    try:
        db.execute(
            """
            INSERT INTO games(user_id, game_id, finished, guesses, won) 
            VALUES(:user_id, :game_id, :finished, :guesses, :won)
            """,
            g
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"type": type(e).__name__, "msg": str(e)},
        )
    return g

# Get stat of a user based on user_id
@app.get("/users/{user_id}")
def retrieve_stat(
    user_id: str,
    user_db: sqlite3.Connection = Depends(get_user_db),
    game1_db: sqlite3.Connection = Depends(get_game1_db),
    game2_db: sqlite3.Connection = Depends(get_game2_db),
    game3_db: sqlite3.Connection = Depends(get_game3_db)
):
    print("<= request routed to this instance\n")
    user_id = uuid.UUID(user_id)

    # Check whether user_id exists in the user database or not
    player = user_db.execute("SELECT * FROM users WHERE user_id = ?",[user_id]).fetchall()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    # Choose the correct shard for this user_id
    if int(user_id) % 3 == 1:
        db = game1_db
    elif int(user_id) % 3 == 2:
        db = game2_db
    else:
        db = game3_db

    currentStreak = maxStreak = gamesPlayed = gamesWon = averageGuesses = fail = winPercentage = 0
    statistics = {}

    # Get current streak
    streak1 = db.execute("SELECT streak FROM streaks WHERE user_id = ? ORDER BY ending DESC", [user_id]).fetchone()
    if streak1:
        currentStreak = streak1[0]

    # Get max streak
    streak2 = db.execute("SELECT streak FROM streaks WHERE user_id = ? ORDER BY streak DESC LIMIT 1", [user_id]).fetchone()
    if streak2:
        maxStreak = streak2[0]

    # Get total games played
    games = db.execute("SELECT COUNT(user_id) FROM games WHERE user_id = ?", [user_id]).fetchone()
    if games:
        gamesPlayed = games[0]

    # Get total games won
    wins = db.execute("SELECT COUNT(user_id) FROM games WHERE user_id = ? AND won = 1", [user_id]).fetchone()
    if wins:
        gamesWon = wins[0]

    # Get average guesses
    avgGuess = db.execute("SELECT AVG(guesses) FROM games WHERE user_id = ?", [user_id]).fetchone()
    if avgGuess:
        averageGuesses = round(avgGuess[0])

    # Calculate win %
    if gamesPlayed != 0:
        winPercentage = round((gamesWon/gamesPlayed)*100)

    # Get guesses counts
    guessCount = db.execute("SELECT guesses, COUNT(guesses) FROM games WHERE user_id = ? and won !=0 GROUP BY guesses", [user_id]).fetchall()

    guess_record = {'1':0, '2':0, '3':0,'4':0, '5':0, '6':0, 'fail':0}
    for guess in guessCount:
        guess_record[f'{guess[0]}'] = guess[1]

    # Get number of games failed
    gamesFailed = db.execute("SELECT count(won) FROM games WHERE user_id = ? AND won = 0", [user_id]).fetchone()
    if gamesFailed:
        fail = gamesFailed[0]
    guess_record["fail"] = fail

    statistics["currentStreak"] = currentStreak
    statistics["maxStreak"] = maxStreak
    statistics["guesses"] = guess_record
    statistics["winPercentage"] = winPercentage
    statistics["gamesPlayed"] = gamesPlayed
    statistics["gamesWon"] = gamesWon
    statistics["averageGuesses"] = averageGuesses

    return statistics

################################################### Leaderboard #################################################

# modify the service from Project 3 to
# pull the data for the wins and streaks leaderboards from Redis rather than from the shareded
# relational database.

@app.get("/leaders/streaks/")
def list_ten_streaks():
    top_ten_streaks = []
    for player in client_redis.zrevrange("streaks", 0, 9, withscores=True):
        username = player[0].decode('utf-8')
        streaks = player[1]
        top_ten_streaks.append({"username" : username, "streaks" : streaks})
    
    return {"top_ten_streaks" : top_ten_streaks}

@app.get("/leaders/wins/")
def list_ten_wins():
    top_ten_wins = []
    for player in client_redis.zrevrange("wins", 0, 9, withscores=True):
        username = player[0].decode('utf-8')
        wins = player[1]
        top_ten_wins.append({"username" : username, "wins" : wins})
    
    return {"top_ten_wins" : top_ten_wins}
