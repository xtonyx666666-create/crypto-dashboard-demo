#!/usr/bin/env bash
# 一条命令本机启动：创建虚拟环境 → 装依赖 → 先采集一次真实数据 → 后台常驻定时采集 → 启动网页
# 用法：./run.sh            （默认端口 8000；PORT=9000 ./run.sh 可改端口）
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
.venv/bin/python -m scheduler.jobs --once
.venv/bin/python -m scheduler.jobs >data/scheduler.log 2>&1 &
trap 'kill $! 2>/dev/null' EXIT
echo "打开 http://localhost:${PORT:-8000}"
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
