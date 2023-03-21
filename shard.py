#!/usr/bin/env python3
import sqlite3
import uuid

def create_user_database(users):
    print("Creating and inserting data to users database...\n")
    sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
    sqlite3.register_adapter(uuid.UUID, lambda u: memoryview(u.bytes_le))

    connection = sqlite3.connect('./var/users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = connection.cursor()

    cur.execute('DROP TABLE IF EXISTS users;')
    cur.execute('CREATE TABLE users (user_id GUID PRIMARY KEY, username VARCHAR UNIQUE)')
    map_key = {}

    # Insert a fake user to test posting a win/loss record later:
    fake_user_id = uuid.UUID("00000a0a-0a00-00a0-a000-0a00aa00abcd")
    fake_user_name = "project4group4"
    cur.execute('INSERT INTO users VALUES (?,?)', [fake_user_id, fake_user_name])

    for user in users:
        
        new_user_id = uuid.uuid4()
        map_key[user[0]] = new_user_id
        cur.execute('INSERT INTO users VALUES (?,?)', [new_user_id, user[1]])

    connection.commit()
    connection.close()
    return map_key

def create_sharding_games(shard_num):
    print(f"Creating sharding game{shard_num} database...\n")
    sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
    sqlite3.register_adapter(uuid.UUID, lambda u: memoryview(u.bytes_le))

    connection = sqlite3.connect(f'./var/games{shard_num}.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = connection.cursor()

    cur.execute('DROP TABLE IF EXISTS games;')
    cur.execute('CREATE TABLE games('
                    'user_id GUID NOT NULL,'
                    'game_id INTEGER NOT NULL,'
                    'finished DATE DEFAULT CURRENT_TIMESTAMP,'
                    'guesses INTEGER,'
                    'won BOOLEAN,'
                    'PRIMARY KEY(user_id, game_id));')
    
    cur.execute('CREATE INDEX games_won_idx ON games(won);')

    cur.execute('DROP VIEW IF EXISTS wins;')
    cur.execute('CREATE VIEW wins '
                'AS '
                'SELECT '
                    'user_id,'
                    'COUNT(won) '
                'FROM '
                    'games '
                'WHERE '
                    'won = TRUE '
                'GROUP BY '
                    'user_id '
                'ORDER BY '
                    'COUNT(won) DESC;')
    
    cur.execute('DROP VIEW IF EXISTS streaks;')
    cur.execute('CREATE VIEW streaks '
                'AS '
                    'WITH ranks AS ('
                        'SELECT DISTINCT '
                            'user_id,'
                            'finished, '
                            'RANK() OVER(PARTITION BY user_id ORDER BY finished) AS rank '
                        'FROM '
                            'games '
                        'WHERE '
                            'won = TRUE '
                        'ORDER BY '
                            'user_id,'
                            'finished'
                    '),'
                    'groups AS ('
                        'SELECT '
                            'user_id,'
                            'finished,'
                            'rank, '
                            "DATE(finished, '-' || rank || ' DAYS') AS base_date "
                        'FROM '
                            'ranks'
                    ') '
                    'SELECT '
                        'user_id,'
                        'COUNT(*) AS streak,'
                        'MIN(finished) AS beginning,'
                        'MAX(finished) AS ending '
                    'FROM '
                        'groups '
                    'GROUP BY '
                        'user_id, base_date '
                    'HAVING '
                        'streak > 1 '
                    'ORDER BY '
                        'user_id,'
                        'finished;')
    
    connection.commit()
    connection.close()

def insert_to_shard(game, connection, new_user_id):
    cur = connection.cursor()
    cur.execute('INSERT INTO games VALUES (?,?,?,?,?)', [new_user_id, game[1], game[2], game[3], game[4]])

def main():

    user_connection = sqlite3.connect('./var/stats.db')
    user_cur = user_connection.cursor()
    users = user_cur.execute("SELECT * FROM users")
    map_key = create_user_database(users)
    user_connection.close()

    for i in range(1, 4):
        create_sharding_games(str(i))

    game_connection = sqlite3.connect('./var/stats.db')
    game_cur = game_connection.cursor()
    
    print("Sharding games into three different games database...\n")

    sqlite3.register_converter('GUID', lambda b: uuid.UUID(bytes_le=b))
    sqlite3.register_adapter(uuid.UUID, lambda u: memoryview(u.bytes_le))

    shard1_connection = sqlite3.connect('./var/games1.db', detect_types=sqlite3.PARSE_DECLTYPES)
    shard2_connection = sqlite3.connect('./var/games2.db', detect_types=sqlite3.PARSE_DECLTYPES)
    shard3_connection = sqlite3.connect('./var/games3.db', detect_types=sqlite3.PARSE_DECLTYPES)

    for game in game_cur.execute("SELECT * FROM games"):
        new_user_id = map_key.get(game[0])

        if int(new_user_id)%3 == 1:
            insert_to_shard(game, shard1_connection, new_user_id)

        elif int(new_user_id)%3 == 2:
            insert_to_shard(game, shard2_connection, new_user_id)

        else:
            insert_to_shard(game, shard3_connection, new_user_id)
    shard1_connection.commit()
    shard1_connection.close()

    shard2_connection.commit()
    shard2_connection.close()

    shard3_connection.commit()
    shard3_connection.close()

    game_connection.close()

if __name__ == '__main__':
    main()
