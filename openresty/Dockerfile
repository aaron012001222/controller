FROM openresty/openresty:alpine

# 安装 Auto-SSL 必须的依赖 (openssl, curl, bash, lua-resty-auto-ssl)
RUN apk add --no-cache openssl curl bash \
    && /usr/local/openresty/luajit/bin/luarocks install lua-resty-auto-ssl \
    # 创建证书存储目录并设置权限
    && mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl