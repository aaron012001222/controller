-- gateway/openresty/lua/access.lua
-- 核心功能: 路径验证, 伪装, B池随机轮询, 异步流量日志上报

local redis = require "resty.redis"
local red = redis:new()
red:set_timeout(1000)

-- 【新增】引入 JSON 库用于构造 API 请求体
local cjson = require "cjson" 


-- 辅助函数：从 Redis B池列表中随机获取一个 URL
local function get_random_url(redis_key, list_size)
    -- 注意：Lua math.random 需要在 list_size > 0 时调用
    if list_size == 0 then
        return nil
    end

    -- 核心修复：使用当前时间的纳秒作为随机数种子
    local seed = ngx.time() * 1000 + tonumber(string.sub(ngx.var.msec, 3))
    math.randomseed(seed)

    -- 随机选择一个索引 (0 到 list_size - 1)
    local index = math.random(0, list_size - 1) 
    
    -- LRANGE key start stop (start 和 stop 都是包含的)
    local urls = red:lrange(redis_key, index, index)
    
    if urls and urls[1] then
        return urls[1]
    end
    return nil
end


-- ----------------------------------------------------------------------
-- 【新增函数】异步流量日志上报
-- ----------------------------------------------------------------------
local function log_traffic(is_bot_flag, project_id, host)
    -- 注意：project_id 必须是整数，host 是域名
    local payload = cjson.encode({
        project_id = tonumber(project_id) or 0, -- 确保是数字
        is_bot = is_bot_flag,
        domain = host
    })
    
    -- 使用 ngx.location.capture 发送异步 POST 请求到后端
    -- 异步且非阻塞，不会影响重定向速度
    local res = ngx.location.capture("/api/log/hit", {
        method = ngx.HTTP_POST,
        body = payload,
        headers = {["Content-Type"] = "application/json"}
    })
    -- 记录日志 (可选)
    ngx.log(ngx.NOTICE, "Traffic Log Sent. Status: ", res.status, ", Bot: ", is_bot_flag)
end
-- ----------------------------------------------------------------------


-- 1. 连接 Redis
local ok, err = red:connect("redis", 6379)
if not ok then
    ngx.log(ngx.ERR, "Redis连接失败: ", err)
    return -- Redis 挂了，显示假博客 (安全第一)
end

-- 1.5. 管理员访问判断
local admin_access = ngx.var.cookie_admin_access or ""
if admin_access == "true" then
    -- 如果有管理员 Cookie，直接放行，让 Nginx 渲染前端页面 (try_files)
    ngx.log(ngx.NOTICE, "Admin Access Granted.")
    return
end

-- 2. 获取当前访问的域名和路径
local host = ngx.var.host or ""
-- ngx.var.uri 是路径，如 /go/item.html
local uri = ngx.var.uri or "" 


-- 3. 从 Redis 查询入口域名信息 (Hash)
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
local required_path = entry_info["custom_path"] or "" -- 读取 custom_path 字段

-- 核心修复开始: 路径验证和修正
local redirect_uri = uri -- 默认使用完整 URI
local path_matched = true 

-- 5. 路径验证 (如果配置了自定义路径)
if required_path ~= "" then
    local expected_path_part = "/" .. required_path
    local expected_path_len = #expected_path_part
    
    -- 检查 URI 是否以 /required_path 开头
    if uri:sub(1, expected_path_len) == expected_path_part then
        -- 匹配成功，从 URI 中移除匹配的部分
        local remaining_uri = uri:sub(expected_path_len + 1)
        
        -- 如果 remaining_uri 是空字符串，则重定向到 B 池的根路径 "/"
        redirect_uri = remaining_uri == "" and "/" or remaining_uri
        
        ngx.log(ngx.NOTICE, "Path Matched. Required: ", required_path, " Redirect URI: ", redirect_uri)
    else
        path_matched = false
        ngx.log(ngx.NOTICE, "Path Mismatch. Required: ", required_path, " Actual URI: ", uri)
    end
end

if not path_matched then
    return -- 路径不匹配，执行伪装
end
-- 核心修复结束


-- 6. 状态和归属检查 (移到路径修正之后)
if status ~= "ok" or project_id == "0" then
    -- 域名被标记为 banned 或未分配，兜底显示假博客
    return 
end


-- 7. 伪装逻辑 (Cloaking)
local ua = ngx.var.http_user_agent or ""
-- 检查是否为微信 UA (或其他需拦截的爬虫)
if string.find(ua, "MicroMessenger") then
    log_traffic(true, project_id, host) -- 【新增记录】记录为爬虫/拦截
    return 
end


-- 8. 核心：B池轮询逻辑
local landing_pool_key = "project:" .. project_id .. ":landing_urls"
local list_size = red:llen(landing_pool_key) -- 获取 B池的链接数量


if list_size > 0 then
    local target_url = get_random_url(landing_pool_key, list_size)
    
    if target_url then
        -- 核心：拼接 B 池 URL 和修正后的路径
        local final_url = target_url .. redirect_uri
        
        log_traffic(false, project_id, host) -- 【新增记录】记录为有效点击
        ngx.log(ngx.NOTICE, "Successful route. Target: ", final_url)
        return ngx.redirect(final_url, 302)
    end
end


-- 9. 最终兜底 (如果 B池为空，也应该记录为失败或无效点击)
log_traffic(false, project_id, host)
ngx.log(ngx.ERR, "Final Fallback: No valid target found.")
return