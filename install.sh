#!/bin/bash
echo ">>> 开始安装环境..."

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker && systemctl start docker
fi

echo ">>> 拉取最新代码..."
git pull

echo ">>> 启动服务..."
# 确保脚本有执行权限
chmod +x backend/*.py
docker compose up -d --build

echo ">>> 安装完成！"