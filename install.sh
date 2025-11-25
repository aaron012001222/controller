#!/bin/bash

# --- 配置区域 ---
# 你的仓库地址
REPO_URL="https://github.com/aaron012001222/controller.git"
# 安装目录名称
INSTALL_DIR="traffic-system"
# ----------------

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   Traffic Control System 一键安装脚本       ${NC}"
echo -e "${GREEN}=============================================${NC}"

# 1. 检查并安装 Git (如果还没有)
if ! command -v git &> /dev/null; then
    echo ">>> 检测到未安装 Git，正在自动安装..."
    if [ -f /etc/debian_version ]; then
        apt-get update && apt-get install -y git
    elif [ -f /etc/redhat-release ]; then
        yum install -y git
    else
        echo -e "${RED}无法自动安装 Git，请手动安装后重试。${NC}"
        exit 1
    fi
fi

# 2. 拉取/更新代码
if [ -d "$INSTALL_DIR" ]; then
    echo ">>> 检测到目录已存在，正在更新代码..."
    cd $INSTALL_DIR
    git pull
else
    echo ">>> 正在从 GitHub 克隆代码..."
    git clone $REPO_URL $INSTALL_DIR
    cd $INSTALL_DIR
fi

# 3. 检查并安装 Docker
if ! command -v docker &> /dev/null; then
    echo ">>> 未检测到 Docker，正在自动安装..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}Docker 安装完成${NC}"
fi

# 4. 检查 Docker Compose 插件
if ! docker compose version &> /dev/null; then
    echo ">>> 安装 Docker Compose 插件..."
    if [ -f /etc/debian_version ]; then
        apt-get update && apt-get install -y docker-compose-plugin
    elif [ -f /etc/redhat-release ]; then
        yum install -y docker-compose-plugin
    fi
fi

# 5. 赋予权限并启动
echo ">>> 正在构建并启动服务..."
chmod +x backend/*.py
chmod +x *.sh

# 强制重新构建并后台启动
docker compose up -d --build

# 6. 显示结果
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   安装完成！系统已成功启动。               ${NC}"
echo -e "${GREEN}=============================================${NC}"
# 获取本机IP
IP=$(curl -s ifconfig.me)
echo -e "访问地址: http://$IP"
echo -e "默认账号: admin"
echo -e "默认密码: admin888"
echo -e "---------------------------------------------"
echo -e "查看日志: cd $INSTALL_DIR && docker logs -f traffic_backend"
echo -e "${GREEN}=============================================${NC}"