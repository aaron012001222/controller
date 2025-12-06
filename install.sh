#!/bin/bash

# --- 配置区域 ---
REPO_URL="https://github.com/aaron012001222/controller.git"
INSTALL_DIR="traffic-system"
# ----------------

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}>>> 开始系统安装/重置...${NC}"

# 1. 基础依赖检查
if ! command -v git &> /dev/null; then
    if [ -f /etc/debian_version ]; then apt-get update && apt-get install -y git; 
    elif [ -f /etc/redhat-release ]; then yum install -y git; fi
fi

# 2. 代码目录处理 (注意：这里去掉了强制覆盖，防止您本地修改的文件丢失)
if [ ! -d "$INSTALL_DIR" ]; then
    echo ">>> 克隆代码仓库..."
    git clone $REPO_URL $INSTALL_DIR
    cd $INSTALL_DIR
else
    echo ">>> 检测到安装目录已存在，使用当前目录代码..."
    cd $INSTALL_DIR
    # 如果您希望强制更新代码，请取消下面两行的注释，但这会覆盖您的修改！
    # git fetch --all
    # git reset --hard origin/master
fi

# 3. Docker 安装
if ! command -v docker &> /dev/null; then
    echo ">>> 安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker && systemctl start docker
fi

# ==========================================
# 4. 核心：生成配置
# ==========================================

# 如果没有 .env 文件，则生成随机凭证
if [ ! -f .env ]; then
    echo ">>> 生成随机管理员凭证..."
    # 生成随机凭证
    RANDOM_USER=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
    RANDOM_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
    RANDOM_PATH=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)
    # 获取本机公网 IP
    CURRENT_IP=$(curl -s ifconfig.me)

    echo "ADMIN_USER=$RANDOM_USER" > .env
    echo "ADMIN_PASS=$RANDOM_PASS" >> .env
    echo "SERVER_IP=$CURRENT_IP" >> .env

    # 替换 Nginx 入口 (仅在首次安装时替换)
    if [ -f openresty/conf/nginx.conf ]; then
        sed -i "s/SECRET_ENTRANCE_PLACEHOLDER/$RANDOM_PATH/g" openresty/conf/nginx.conf
    fi
else
    echo ">>> 检测到已有 .env 配置，跳过凭证生成。"
    # 读取现有的配置用于最后显示
    source .env
    # 尝试从 nginx.conf 中提取入口路径（如果能提取到）
    RANDOM_PATH=$(grep "location =" openresty/conf/nginx.conf | awk '{print $3}' | sed 's/\///g')
fi

# ==========================================
# 5. SSL 证书处理 (适配 Auto-SSL)
# ==========================================

echo -e "${YELLOW}----------------------------------------------------${NC}"
echo -e "${YELLOW}SSL 配置: 生成 Auto-SSL 启动所需的兜底证书${NC}"
echo -e "${YELLOW}注意: 这只是为了让 Nginx 能启动。真实的证书将由 OpenResty 在用户访问时全自动申请。${NC}"
echo -e "${YELLOW}----------------------------------------------------${NC}"

# 准备证书目录
mkdir -p openresty/certs

# 无论如何都重新生成这个自签名证书，确保 Nginx 启动不报错
echo ">>> 生成自签名兜底证书..."
openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
    -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=localhost" \
    -keyout openresty/certs/server.key -out openresty/certs/server.crt

echo -e "${GREEN}>>> 兜底证书生成完毕。${NC}"

# ==========================================
# 6. 数据库与权限
# ==========================================

# 初始化数据库文件 (如果不存在)
if [ ! -f traffic.db ]; then
    touch traffic.db
    chmod 777 traffic.db
fi
# 确保权限正确 (防止 Docker 挂载后无权限写入)
chmod 777 traffic.db

# 确保后端脚本有执行权限
if [ -d "backend" ]; then
    chmod +x backend/*.py
fi

# ==========================================
# 7. 启动服务
# ==========================================

echo ">>> 正在构建并启动服务..."
# 强制重新构建 (因为您修改了 Dockerfile 和 requirements.txt)
docker compose down
docker compose up -d --build

# ==========================================
# 8. 输出结果
# ==========================================

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}   系统安装/更新完成！                      ${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "您可以直接通过 IP 访问（浏览器会提示不安全，点击高级->继续访问即可）："
echo -e ""
echo -e "管理后台 : https://${SERVER_IP:-$CURRENT_IP}/$RANDOM_PATH"
echo -e "服务器 IP: ${SERVER_IP:-$CURRENT_IP}"
echo -e "账号     : ${ADMIN_USER:-$RANDOM_USER}"
echo -e "密码     : ${ADMIN_PASS:-$RANDOM_PASS}"
echo -e "---------------------------------------------"
echo -e "【后续操作】"
echo -e "1. 登录后台后，请在'域名仓库'添加您的域名。"
echo -e "2. 将域名 A 记录解析到本 IP，并关闭 Cloudflare 小黄云。"
echo -e "3. 之后使用 https://您的域名/$RANDOM_PATH 访问，会自动获得绿锁证书。"
echo -e "${GREEN}=============================================${NC}"