#!/bin/bash

# --- 配置区域 ---
REPO_URL="https://github.com/aaron012001222/controller.git"
INSTALL_DIR="traffic-system"
# ----------------

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}>>> 开始全自动安装...${NC}"

# 1. 环境检查与代码拉取 (保持之前的逻辑)
if ! command -v git &> /dev/null; then
    if [ -f /etc/debian_version ]; then apt-get update && apt-get install -y git; 
    elif [ -f /etc/redhat-release ]; then yum install -y git; fi
fi

if [ -d "$INSTALL_DIR" ]; then
    cd $INSTALL_DIR && git pull
else
    git clone $REPO_URL $INSTALL_DIR && cd $INSTALL_DIR
fi

# 2. Docker 安装 (保持之前的逻辑)
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker && systemctl start docker
fi

# ==========================================
# 3. 核心：生成随机凭证与入口
# ==========================================

# 生成 12 位随机字符串
RANDOM_USER=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
RANDOM_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
RANDOM_PATH=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)

echo ">>> 生成随机配置..."
echo "ADMIN_USER=$RANDOM_USER" > .env
echo "ADMIN_PASS=$RANDOM_PASS" >> .env

# 替换 Nginx 配置文件中的占位符 (SECRET_PATH)
# 为了防止多次运行脚本导致重复替换，先还原配置文件（如果仓库里是最新的）
git checkout openresty/conf/nginx.conf 2>/dev/null
# 执行替换
sed -i "s/SECRET_PATH/$RANDOM_PATH/g" openresty/conf/nginx.conf

# 确保 traffic.db 为空文件，防止 Docker 目录错误
rm -rf backend/traffic.db traffic.db
touch traffic.db
chmod 777 traffic.db

# ==========================================

# 4. 启动服务
chmod +x backend/*.py
docker compose up -d --build

# 5. 获取 IP 并输出结果
IP=$(curl -s ifconfig.me)

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   系统安装完成！安全入口已生成             ${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "后台入口: http://$IP/$RANDOM_PATH"
echo -e "账号: $RANDOM_USER"
echo -e "密码: $RANDOM_PASS"
echo -e "---------------------------------------------"
echo -e "注意：直接访问 http://$IP 会显示 404，必须通过上方入口进入！"
echo -e "${GREEN}=============================================${NC}"