# openresty/Dockerfile - 修复版
FROM openresty/openresty:alpine

# 1. 安装基础依赖
# curl, bash, openssl: Auto-SSL 运行时需要
# build-base, unzip: 编译 Lua 模块可能需要
RUN apk add --no-cache curl bash openssl build-base unzip

# 2. 专门安装 luarocks (Alpine 仓库里有)
RUN apk add --no-cache luarocks

# 3. 使用 luarocks 安装 lua-resty-auto-ssl
# 注意：不需要指定路径，直接用系统命令
RUN luarocks install lua-resty-auto-ssl

# 4. 创建证书存储目录并设置权限 (OpenResty 默认运行用户可能是 nobody 或 www-data)
RUN mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl \
    && chmod 755 /etc/resty-auto-ssl

# 5. 生成自签名证书作为默认回退 (这一步 install.sh 已经在宿主机做了，但为了容器健壮性，这里也声明一下目录)
RUN mkdir -p /usr/local/openresty/nginx/certs