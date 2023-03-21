#!/usr/bin/env python3

# Create a standalone command-line program (i.e. not a web API) in Python to connect to each of
# the win/loss shards and pull the top 10 entries from each view. Then connect to Redis and store
# each entry in a sorted set.
# Note: this means that you will be storing 30 entries from each view (10 from each shard).
import sqlite3
import uuid
import redis

def get_top_streaks_shard(shardnum):
    sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
    sqlite3.register_adapter(uuid.UUID, lambda u: memoryview(u.bytes_le))
    game_connection = sqlite3.connect(f'./var/games{str(shardnum)}.db', detect_types=sqlite3.PARSE_DECLTYPES)
    game_cur = game_connection.cursor()

    user_connection = sqlite3.connect('./var/users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    user_cur = user_connection.cursor()

    streaks = game_cur.execute("SELECT * FROM streaks ORDER BY streak DESC LIMIT 10").fetchall()

    players_and_streaks = []

    for user in streaks:
        player = user_cur.execute("SELECT * FROM users WHERE user_id = ? LIMIT 1", [user[0]]).fetchall()
        username = player[0][1]
        num_streak = user[1]
        players_and_streaks.append({"username" : username, "streaks" : num_streak})
    
    game_connection.close()
    user_connection.close()

    return players_and_streaks

def get_top_wins_shard(shardnum):
    sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
    sqlite3.register_adapter(uuid.UUID, lambda u: memoryview(u.bytes_le))
    game_connection = sqlite3.connect(f'./var/games{str(shardnum)}.db', detect_types=sqlite3.PARSE_DECLTYPES)
    game_cur = game_connection.cursor()

    user_connection = sqlite3.connect('./var/users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    user_cur = user_connection.cursor()

    wins = game_cur.execute("SELECT * FROM wins LIMIT 10").fetchall()

    players_and_wins = []

    for user in wins:
        player = user_cur.execute("SELECT * FROM users WHERE user_id = ? LIMIT 1", [user[0]]).fetchall()
        username = player[0][1]
        num_win = user[1]
        players_and_wins.append({"username" : username, "wins" : num_win})

    game_connection.close()
    user_connection.close()
    return players_and_wins

def main():
    client_redis = redis.Redis()
    for i in range (1, 4):
        for player in get_top_streaks_shard(i):
            client_redis.zadd("streaks", {player['username'] : player['streaks']})
        for player in get_top_wins_shard(i):
            client_redis.zadd("wins", {player['username'] : player['wins']})

if __name__ == '__main__':
    main()
