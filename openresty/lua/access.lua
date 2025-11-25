-- gateway/openresty/lua/access.lua
-- 核心功能: 路径验证, 伪装, B池随机轮询

local redis = require "resty.redis"
local red = redis:new()
red:set_timeout(1000)

-- 辅助函数：从 Redis B池列表中随机获取一个 URL
local function get_random_url(redis_key, list_size)
    -- 注意：Lua math.random 需要在 list_size > 0 时调用
    if list_size == 0 then
        return nil
    end

    -- Redis List 索引从 0 开始。
    -- 随机选择一个索引 (0 到 list_size - 1)
    local index = math.random(0, list_size - 1) 
    
    -- LRANGE key start stop (start 和 stop 都是包含的)
    local urls = red:lrange(redis_key, index, index)
    
    if urls and urls[1] then
        return urls[1]
    end
    return nil
end


-- 1. 连接 Redis
local ok, err = red:connect("redis", 6379)
if not ok then
    ngx.log(ngx.ERR, "Redis连接失败: ", err)
    return -- Redis 挂了，显示假博客 (安全第一)
end


-- 2. 获取当前访问的域名和路径
local host = ngx.var.host or ""
-- ngx.var.uri 是路径，如 /go/ 或者 /
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


-- 5. 路径验证 (核心新增：必须匹配自定义路径)
-- required_path 比如是 "go" 或 "asdf12"
if required_path ~= "" then
    -- 检查 URI 是否以 /required_path/ 或 /required_path 开头
    local expected_path_part = "/" .. required_path
    
    -- 如果用户访问的 URI 不是 /required_path 开头，则失败
    if uri:sub(1, #expected_path_part) ~= expected_path_part then
        ngx.log(ngx.NOTICE, "Path Mismatch. Required: ", required_path, " Actual URI: ", uri)
        return -- 路径不匹配，执行伪装
    end
end


-- 6. 状态和归属检查
if status ~= "ok" or project_id == "0" then
    -- 域名被标记为 banned 或未分配，兜底显示假博客
    return 
end


-- 7. 伪装逻辑 (Cloaking)
local ua = ngx.var.http_user_agent or ""
-- 如果是微信 UA，我们直接返回 Nginx 的静态伪装页
if string.find(ua, "MicroMessenger") then
    return 
end


-- 8. 核心：B池轮询逻辑
local landing_pool_key = "project:" .. project_id .. ":landing_urls"
local list_size = red:llen(landing_pool_key) -- 获取 B池的链接数量


if list_size > 0 then
    local target_url = get_random_url(landing_pool_key, list_size)
    
    if target_url then
        ngx.log(ngx.NOTICE, "Successful route. Target: ", target_url)
        return ngx.redirect(target_url, 302)
    end
end


-- 9. 最终兜底
ngx.log(ngx.ERR, "Final Fallback: No valid target found.")
return