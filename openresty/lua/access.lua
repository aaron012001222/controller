-- gateway/openresty/lua/access.lua
-- 核心功能: 路径验证, 伪装, B池随机轮询, 异步流量日志上报
-- 【安全修复】：强制管理路由必须携带 Cookie

local redis = require "resty.redis"
local red = redis:new()
red:set_timeout(1000)

local cjson = require "cjson" 


-- 辅助函数：从 Redis B池列表中随机获取一个 URL
local function get_random_url(redis_key, list_size)
    if list_size == 0 then return nil end

    local seed = ngx.time() * 1000 + tonumber(string.sub(ngx.var.msec, 3))
    math.randomseed(seed)

    local index = math.random(0, list_size - 1) 
    local urls = red:lrange(redis_key, index, index)
    
    if urls and urls[1] then
        return urls[1]
    end
    return nil
end


-- 异步流量日志上报
local function log_traffic(is_bot_flag, project_id, host)
    local payload = cjson.encode({
        project_id = tonumber(project_id) or 0,
        is_bot = is_bot_flag,
        domain = host
    })
    
    -- 使用 ngx.location.capture 发送异步 POST 请求到后端
    local res = ngx.location.capture("/api/log/hit", {
        method = ngx.HTTP_POST,
        body = payload,
        headers = {["Content-Type"] = "application/json"}
    })
    ngx.log(ngx.NOTICE, "Traffic Log Sent. Status: ", res.status, ", Bot: ", is_bot_flag)
end


-- 1. 连接 Redis
local ok, err = red:connect("redis", 6379)
if not ok then
    ngx.log(ngx.ERR, "Redis连接失败: ", err)
    return -- Redis 挂了，显示假博客
end

-- 2. 获取当前访问的域名和路径
local host = ngx.var.host or ""
local uri = ngx.var.uri or "" 
local admin_access = ngx.var.cookie_admin_access or ""


-- ----------------------------------------------------------------------
-- 【核心安全检查】：强制管理后台访问必须携带 Cookie
-- ----------------------------------------------------------------------

-- 检查当前 URI 是否是管理后台的前端路由
-- 正则表达式匹配 /login, /settings, /projects, /domains, / 或 /account/settings 等所有前端路由
-- 注意：/api 和静态资源（如 /bg_video.mp4, /assets/）会通过 try_files 逻辑处理
local is_admin_route = string.match(uri, "^/(login|settings|projects|domains|account|dashboard)") or uri == "/"

if is_admin_route then
    if admin_access == "true" then
        -- 场景 A：已登录管理员访问前端路由 -> 放行
        ngx.log(ngx.NOTICE, "Admin Route Access Granted by Cookie.")
        return 
    else
        -- 场景 B：非登录用户访问前端路由（如直接访问 /login） -> 拒绝 (伪装)
        ngx.log(ngx.NOTICE, "Unauthorized access to admin route: ", uri)
        return -- 触发 404 伪装页，隐藏后台
    end
end

-- 如果是 /api/ 请求，也必须通过 Cookie 检查 (可选，但推荐)
if string.match(uri, "^/api/") then
     if admin_access == "true" then
        ngx.log(ngx.NOTICE, "Admin API Access Granted.")
        return -- 放行到 FastAPI
    else
        ngx.log(ngx.NOTICE, "Unauthorized API access: ", uri)
        ngx.exit(ngx.HTTP_FORBIDDEN) -- 阻止未经授权的 API 调用
    end
end


-- ----------------------------------------------------------------------
-- 3. 流量调度逻辑（只针对非管理员和非后台路由）
-- ----------------------------------------------------------------------


-- 从 Redis 查询入口域名信息 (Hash)
local entry_key = "domain:" .. host
local domain_info_raw, err = red:hgetall(entry_key)

if not domain_info_raw or #domain_info_raw == 0 then
    -- 未注册域名，兜底显示假博客
    return
end


-- 4. 数据解析与状态检查
local entry_info = {}
for i = 1, #domain_info_raw, 2 do
    entry_info[domain_info_raw[i]] = domain_info_raw[i + 1]
end

local project_id = entry_info["project_id"]
local status = entry_info["status"]
local required_path = entry_info["custom_path"] or "" 

-- 核心修复开始: 路径验证和修正
local redirect_uri = uri
local path_matched = true 

-- 5. 路径验证 (如果配置了自定义路径)
if required_path ~= "" then
    local expected_path_part = "/" .. required_path
    local expected_path_len = #expected_path_part
    
    if uri:sub(1, expected_path_len) == expected_path_part then
        local remaining_uri = uri:sub(expected_path_len + 1)
        redirect_uri = remaining_uri == "" and "/" or remaining_uri
    else
        path_matched = false
    end
end

if not path_matched then
    return -- 路径不匹配，执行伪装
end


-- 6. 状态和归属检查 
if status ~= "ok" or project_id == "0" then
    return -- 域名被标记为 banned 或未分配，兜底显示假博客
end


-- 7. 伪装逻辑 (Cloaking) - 拦截爬虫
local ua = ngx.var.http_user_agent or ""
if string.find(ua, "MicroMessenger") then
    log_traffic(true, project_id, host) -- 记录为爬虫/拦截
    return 
end


-- 8. 核心：B池轮询逻辑
local landing_pool_key = "project:" .. project_id .. ":landing_urls"
local list_size = red:llen(landing_pool_key)


if list_size > 0 then
    local target_url = get_random_url(landing_pool_key, list_size)
    
    if target_url then
        local final_url = target_url .. redirect_uri
        
        log_traffic(false, project_id, host) -- 记录为有效点击
        ngx.log(ngx.NOTICE, "Successful route. Target: ", final_url)
        return ngx.redirect(final_url, 302)
    end
end


-- 9. 最终兜底 (如果 B池为空)
log_traffic(false, project_id, host)
ngx.log(ngx.ERR, "Final Fallback: No valid target found.")
return