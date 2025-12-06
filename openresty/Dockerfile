# 使用官方全功能镜像，自带 LuaRocks 和编译工具
FROM openresty/openresty:alpine-fat

# 1. 安装系统依赖
RUN apk add --no-cache openssl curl bash

# 2. 显式安装所有 Lua 依赖 (不要依赖自动处理，手动装最稳)
RUN luarocks install lua-resty-http \
    && luarocks install lua-resty-redis \
    && luarocks install lua-resty-auto-ssl

# 3. 创建目录并设置权限
RUN mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl \
    && chmod 755 /etc/resty-auto-ssl \
    && mkdir -p /usr/local/openresty/nginx/certs