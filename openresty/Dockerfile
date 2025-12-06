FROM openresty/openresty:alpine

# 1. 安装基础依赖
# curl, bash, openssl: Auto-SSL 运行时需要
# build-base, unzip: 编译 Lua 模块可能需要
# luarocks: Lua 包管理器
RUN apk add --no-cache curl bash openssl build-base unzip luarocks

# 2. 安装 lua-resty-auto-ssl
# 注意：使用绝对路径 /usr/bin/luarocks，防止环境变量未生效
RUN /usr/bin/luarocks install lua-resty-auto-ssl

# 3. 创建证书存储目录并设置权限
RUN mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl \
    && chmod 755 /etc/resty-auto-ssl

# 4. 创建默认证书目录
RUN mkdir -p /usr/local/openresty/nginx/certs