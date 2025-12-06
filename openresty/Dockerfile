FROM openresty/openresty:alpine

# 1. 安装基础依赖
# curl, bash, openssl: Auto-SSL 运行时需要
# build-base, unzip: 编译 Lua 模块需要
# luarocks: Lua 包管理器
RUN apk add --no-cache curl bash openssl build-base unzip luarocks

# 2. 安装 lua-resty-auto-ssl
# 修复：不使用绝对路径，直接用 luarocks 命令，因为 apk 安装后它一定在 PATH 里
# 如果 luarocks 命令失败，尝试查找路径
RUN if command -v luarocks &> /dev/null; then \
        luarocks install lua-resty-auto-ssl; \
    else \
        # 兜底：尝试常见路径
        /usr/bin/luarocks install lua-resty-auto-ssl || \
        /usr/local/bin/luarocks install lua-resty-auto-ssl; \
    fi

# 3. 创建证书存储目录并设置权限
RUN mkdir -p /etc/resty-auto-ssl \
    && chown nobody:nobody /etc/resty-auto-ssl \
    && chmod 755 /etc/resty-auto-ssl

# 4. 创建默认证书目录
RUN mkdir -p /usr/local/openresty/nginx/certs