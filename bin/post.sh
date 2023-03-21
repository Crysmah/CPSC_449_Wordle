#!/bin/sh

http --verbose POST localhost:5200/games/ @"$1"
