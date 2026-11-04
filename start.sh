#!/usr/bin/env bash
# Render 启动：后台常驻采集（启动即采一次），前台网页服务绑定 $PORT
cd "$(dirname "$0")"
mkdir -p data
python -m scheduler.jobs > data/scheduler.log 2>&1 &
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
