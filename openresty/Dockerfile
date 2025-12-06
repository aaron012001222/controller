FROM openresty/openresty:alpine

# 1. 一次性安装所有依赖 (增加 git，以防 luarocks 拉取源码失败)
RUN apk update && apk add --no-cache \
    curl \
    bash \
    openssl \
    build-base \
    unzip \
    luarocks \
    git

# 2. 直接安装，不带任何路径前缀
# apk 安装的 luarocks 会自动在系统 PATH 中，直接调用即可
RUN luarocks install lua-resty-auto-ssl

# 3. 创建目录并设置权限
RUN mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl \
    && chmod 755 /etc/resty-auto-ssl

# 4. 创建证书目录
RUN mkdir -p /usr/local/openresty/nginx/certs