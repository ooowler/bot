#!/bin/bash

set -e
echo "[+] Запускаем Redis и PostgreSQL..."
docker-compose build
docker-compose up --remove-orphans --force-recreate
