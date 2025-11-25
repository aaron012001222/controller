#!/bin/bash
echo ">>> 开始更新系统..."

# 1. 拉取 Git 最新代码
git pull

# 2. 重启容器 (会重新构建后端，并加载最新的前端 dist)
docker compose down
docker compose up -d --build

echo ">>> 系统更新完成！"
docker logs -f traffic_backend