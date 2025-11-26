#!/bin/bash

# --- 配置区域 ---
REPO_URL="https://github.com/aaron012001222/controller.git"
INSTALL_DIR="traffic-system"
# ----------------

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}>>> 开始全自动安装...${NC}"

# 1. 环境检查与代码拉取
if ! command -v git &> /dev/null; then
    if [ -f /etc/debian_version ]; then apt-get update && apt-get install -y git; 
    elif [ -f /etc/redhat-release ]; then yum install -y git; fi
fi

if [ -d "$INSTALL_DIR" ]; then
    cd $INSTALL_DIR
    # 强制重置本地修改，确保配置模板最新
    git fetch --all
    git reset --hard origin/master
    git pull
else
    git clone $REPO_URL $INSTALL_DIR
    cd $INSTALL_DIR
fi

# 2. Docker 安装
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker && systemctl start docker
fi

# ==========================================
# 3. 核心：自动生成配置 (账号、密码、IP)
# ==========================================

# 生成随机账号密码
RANDOM_USER=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
RANDOM_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
RANDOM_PATH=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)

# 【关键】自动获取当前服务器公网 IP
CURRENT_IP=$(curl -s ifconfig.me)

echo ">>> 正在生成环境配置..."
# 写入 .env 文件 (这文件只在客户服务器上生成，不在 Git 里)
echo "ADMIN_USER=$RANDOM_USER" > .env
echo "ADMIN_PASS=$RANDOM_PASS" >> .env
echo "SERVER_IP=$CURRENT_IP" >> .env  # <--- 这里！自动写入当前服务器IP

# 替换 Nginx 入口
sed -i "s/SECRET_ENTRANCE_PLACEHOLDER/$RANDOM_PATH/g" openresty/conf/nginx.conf

# 初始化数据库文件
rm -rf backend/traffic.db traffic.db
touch traffic.db
chmod 777 traffic.db

# ==========================================

# 4. 启动服务
chmod +x backend/*.py
docker compose up -d --build

# 5. 输出结果
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   系统安装完成！请保存以下信息             ${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "服务器 IP: $CURRENT_IP"
echo -e "后台入口 : http://$CURRENT_IP/$RANDOM_PATH"
echo -e "账号     : $RANDOM_USER"
echo -e "密码     : $RANDOM_PASS"
echo -e "---------------------------------------------"
echo -e "注意：系统已自动配置解析 IP 为本机 IP ($CURRENT_IP)"
echo -e "${GREEN}=============================================${NC}"