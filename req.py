import asyncio
import httpx
import random
import contextlib
import logging.config
import json

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, BaseSettings

app = FastAPI(root_path="/req")

# Start new game
@app.post("/new", status_code=200)
def startGame(username:str):
  x = random.randint(1,2111)
  params = {'username': f'{username}', 'game_id': x}
  r = httpx.post('http://localhost:9999/games/start', params=params)
  return {'status': 'new', 'user_id': r.json()['user_id'], 'game_id': r.json()['game_id']}

@app.post("/guess")
def newGuess(user_id:str, game_id:int, guess:str):
  # Validate the guess
  params = {'guess': f'{guess}'}
  r = httpx.get('http://localhost:9999/dict/validate', params=params)
  code = r.status_code
  if code == 400:
    return r.json()


  # Record guess and updates guesses remaining
  params = {'user_id': user_id,'game_id': game_id, 'guess': guess}
  r = httpx.post(f'http://localhost:9999/games/update', params=params)
  if r.status_code == 400:
    return r.json()
  params = {'game_id': game_id, 'guess': guess}
  answer = httpx.get('http://localhost:9999/guess/check', params=params)

  return {'remaining': r.json()['remain_guess'],**answer.json()}



#f07d4756-e5fd-4b2e-9c44-b14e79c90e42
#13192
