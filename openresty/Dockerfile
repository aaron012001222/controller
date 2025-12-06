# -----------------------------------------------------------
# 使用官方提供的 "fat" 版本镜像
# 这个版本已经预装了 luarocks, gcc, make, git 等所有编译工具
# 绝对不会出现找不到 luarocks 的问题
# -----------------------------------------------------------
FROM openresty/openresty:alpine-fat

# 1. 仅安装 Auto-SSL 运行时的核心依赖 (openssl, curl, bash)
# 注意：不需要再安装 luarocks 或 build-base，镜像里自带了
RUN apk add --no-cache openssl curl bash

# 2. 直接安装插件 (肯定能成功，因为环境是预设好的)
RUN luarocks install lua-resty-auto-ssl

# 3. 创建必要的目录并设置权限
RUN mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl \
    && chmod 755 /etc/resty-auto-ssl \
    && mkdir -p /usr/local/openresty/nginx/certs