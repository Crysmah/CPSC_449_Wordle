#!/bin/sh

sqlite3 ./var/words.db < ./share/words.sql
sqlite3 ./var/answers.db < ./share/answers.sql
sqlite3 ./var/stats.db < ./share/sqlite3-populated.sql
