# CPSC_449_Wordle

# RESTful Back-end Microservices and APIs for a Server-side Wordle Game

## Group Members:

    Kevin Garcia Sarmiento

    Javier Diaz

    Maia Nguyen

    Michael Dang

## Run and test the services:

1. Go to the /api directory:

    ```
    cd api
    ```

2. Initialize the databases:

    ```
    ./bin/init.sh
    ```

3. Shard the stats database (We modified our shard.py and it runs much faster now):
    ```
    ./shard.py
    ```

4. Download Traefik (a single binary) from:

    `https://github.com/traefik/traefik/releases/download/v2.6.3/traefik_v2.6.3_linux_amd64.tar.gz`


5. Extract the compressed file and move the `traefik` file into api folder

6. Start Traefik:

    ```
    ./traefik --configFile=traefik.toml
    ```

7. Open another terminal window and go to the /api directory to start the services with
    one instance of dict (validate guess) service,
    one instance of guess (check guess) service,
    three instances of the stats service,
    one instance of the state (track state) service:

    ```
    foreman start -m dict=1,guess=1,stats=3,state=1,req=1
    ```
8. Open another terminal window and go to the /api directory to run the leaderboards script and store top 10 streaks and wins in NoSQL:

    ```
    ./leaderboards.py
    ```

9. Test the services using curl, HTTPie, or automatic docs

    * Use the following request URLs with curl or HTTPie :

        - "Validate Guess" service:

            * To validate a guess: `http://localhost:9999/dict/validate?guess={your_guess}`

            * To add a new/possible guess: `http://localhost:9999/dict/add_guess?guess={new_word}`

            * To remove a bad guess: `http://localhost:9999/dict/remove_guess?guess={bad_word}`


        - "Check Guess against Answer" service:

            * To check a valid guess against the answer: `http://localhost:9999/guess/check?game_id={game_id}&guess={valid_guess}`

            * To add a new/possible answer: `http://localhost:9999/guess/add_answer?answer={new_answer}`

            * To update/change the answer of an existing game: `http://localhost:9999/guess/change_answer?game_id={game_id}&new_answer={new_answer}`

        - "Track user statistics" service:

            * To post a win or loss for a particular game:
                In another terminal window and in /api directory, run the command:

                ```
                ./bin/post.sh ./share/game.json
                ```

            * To retrieve the statistics for a user: `http://localhost:9999/stats/users/{user_id}`

            * To retrieve the top 10 users by number of wins: `http://localhost:9999/stats/leaders/wins`

            * To retrieve the top 10 users by longest streaks: `http://localhost:9999/stats/leaders/streaks/`

        - "Track state" service:

            * To start a new game: `http://localhost:9999/games/start?user_id={user_id}&game_id={game_id}`

            * To update the state of a game by recording guess and updating number of guesses remaining: `http://localhost:9999/games/update?user_id={user_id}&game_id={game_id}&guess={valid_guess}`

            * To restore the state of a game: `http://localhost:9999/games/restore?user_id={user_id}&game_id={game_id}`

        - " Requests service via HTTP "

            * Posting a game to a specific user: `http://localhost:9999/req/new?username={username}`

            * posting new guess: `http://localhost:9999/req/guess?user_id={user_id}&game_id={game_id}&guess={guess}`

    * Automatic docs:

        - "Validate Guess" service: `http://localhost:9999/dict/docs`

        - "Check Guess against Answer" service: `http://localhost:9999/guess/docs`

        - "Track user statistics" service: `http://localhost:9999/stats/docs`

        - "Track state" service: `http://localhost:9999/games/docs`

        - "HTTP Request" service `http://localhost:9999/req/docs`
