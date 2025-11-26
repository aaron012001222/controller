# main.py - 100% 完整无删减版 (修复 Redis 路径丢失 + CF 解析报错)
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from sqlalchemy.orm import Session
import httpx
import redis
import json
import os 
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ServerException, ClientException
from aliyunsdkdomain.request.v20180129 import QueryDomainListRequest, SaveBatchTaskForModifyingDomainDnsRequest 

import random
import string
import time
import hashlib
import traceback
import dns.resolver
from typing import Dict, Any
import asyncio

# 导入数据库模型
from database import SessionLocal, init_db, EntryDomain, LandingDomain, Project, SystemSetting, DomainStatusLog, AdminUser
from worker import start_scheduler, check_domain_status 

app = FastAPI(title="Traffic Control System")

# 配置 CORS 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 添加 OPTIONS 方法的通用处理
@app.options("/{path:path}")
async def options_handler(path: str):
    """处理所有 OPTIONS 预检请求"""
    return {"message": "OK"}

def generate_random_path(length=6):
    """生成 6 位字母和数字的混合随机路径"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# --- 辅助函数：获取公网 IP ---
async def get_public_ip():
    # 1. 优先从环境变量获取 (最稳)
    env_ip = os.getenv("SERVER_IP")
    if env_ip:
        print(f">>> 使用配置的服务器 IP: {env_ip}")
        return env_ip

    # 2. 尝试自动获取
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get('https://api.ipify.org', timeout=5)
            if resp.status_code == 200:
                ip = resp.text.strip()
                print(f">>> 自动检测到 IP: {ip}")
                return ip
    except Exception as e:
        print(f">>> 无法自动获取公网 IP: {e}")
    
    return None

# --- 核心：Cloudflare 自动防红配置函数 ---
async def auto_configure_cf_security(client: httpx.AsyncClient, zone_id: str, headers: dict):
    """
    自动化配置 Cloudflare 防红策略组合拳
    """
    settings_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings"
    
    configs = [
        ("security_level", {"value": "high"}, "安全级别设为 High"),
        ("rocket_loader", {"value": "on"}, "开启 Rocket Loader 混淆"),
        ("always_use_https", {"value": "on"}, "开启强制 HTTPS"),
        ("minify", {"value": {"css": "on", "html": "on", "js": "on"}}, "开启全站代码压缩"),
        ("browser_integrity_check", {"value": "on"}, "开启浏览器完整性检查"),
        ("min_tls_version", {"value": "1.2"}, "设置最低 TLS 为 1.2"),
        ("bot_fight_mode", {"value": "on"}, "开启 Bot Fight Mode"),
        ("challenge_ttl", {"value": 1800}, "设置验证码有效期为 30 分钟")
    ]

    print(f">>> 开始为 Zone {zone_id} 配置全套防红策略...")
    
    for endpoint, data, desc in configs:
        try:
            resp = await client.patch(f"{settings_url}/{endpoint}", headers=headers, json=data)
            if resp.status_code == 200:
                print(f"    [成功] {desc}")
            else:
                print(f"    [跳过] {desc} (状态码: {resp.status_code})")
        except Exception as e:
            print(f"    [错误] {desc}: {e}")

def debug_aliyun_request(client, request, operation_name):
    """调试阿里云请求的详细信息"""
    debug_info = {"operation": operation_name, "timestamp": time.time()}
    try:
        response = client.do_action_with_exception(request)
        response_data = json.loads(response.decode('utf-8'))
        debug_info["status"] = "success"
        return response_data
    except Exception as e:
        print(f"\n!!! 阿里云API失败: {operation_name} - {str(e)}\n")
        raise e

def _get_error_reason(error_code):
    """根据错误代码返回可能的错误原因"""
    error_reasons = {
        "InvalidAccessKeyId.NotFound": "AccessKey ID 不存在或已禁用",
        "SignatureDoesNotMatch": "AccessKey Secret 不正确",
        "Forbidden.RAM": "RAM 权限不足",
        "DomainNotExist": "域名不存在",
        "InvalidPageNumber": "页码参数错误",
        "InvalidPageSize": "每页大小参数错误",
        "InternalError": "阿里云内部错误，请稍后重试",
        "ServiceUnavailable": "服务暂时不可用",
    }
    return error_reasons.get(error_code, "未知错误，请查看错误信息")

# --- Redis 配置 ---
REDIS_HOST = "redis"
REDIS_PORT = 6379
try:
    pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r = redis.Redis(connection_pool=pool)
except:
    print("!!! Redis 连接失败，请检查 Docker。")

# --- 商业配置 ---
SECRET_KEY = "commercial_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# --- 数据库依赖 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 模型定义 ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ImportRequest(BaseModel):
    token: Optional[str] = None
    domains: List[dict]

class DomainSwitchRequest(BaseModel):
    target_provider: str

class DomainStatusCheckRequest(BaseModel):
    domain_ids: List[int]

class DomainStatusResponse(BaseModel):
    domain_id: int
    domain_name: str
    ns_status: str
    last_check: Optional[datetime]
    message: str

class SettingRequest(BaseModel):
    cf_token: Optional[str] = None
    aliyun_key: Optional[str] = None
    aliyun_secret: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str

class BulkBindEntryRequest(BaseModel):
    domain_ids: List[int] 

class BulkLandingCreate(BaseModel):
    urls: str 

class BulkDeleteEntry(BaseModel):
    entry_ids: List[int]

class BulkDeleteLanding(BaseModel):
    landing_ids: List[int]

class AliyunDomainImport(BaseModel):
    domain_names: List[str] # 接收用户勾选的域名列表

class UpdateEntryPath(BaseModel):
    domain_id: int
    custom_path: str # 新的自定义路径

class AliyunSetupRequest(BaseModel):
    # 接收前端选择的域名名称列表
    selected_domains: List[str]

# 单个绑定操作
class LandingCreate(BaseModel):
    url: str
class BindEntryRequest(BaseModel):
    domain_id: int

class UpdateUserRequest(BaseModel):
    username: str
    password: str

# --- 认证和用户模拟 ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401, detail="凭证过期")
    return username

# --- 辅助函数：同步到 Redis (修复 404 的关键！) ---
def sync_domain_to_redis(domain_obj):
    """将 Entry Domain 状态写入 Redis，供 OpenResty 读取"""
    key = "domain:" + domain_obj.domain
    
    value = {
        "status": domain_obj.status,
        "project_id": str(domain_obj.project_id) if domain_obj.project_id else "0",
        "provider": domain_obj.provider,
        # 【修复】这里必须把 custom_path 写入 Redis，否则网关查不到路径会报 404
        "custom_path": domain_obj.custom_path if domain_obj.custom_path else ""
    }
    
    try:
        r.hset(key, mapping=value)
    except redis.exceptions.ConnectionError:
        pass

# 新增：同步落地页池函数 (B池)
def sync_landing_pool_to_redis(project_id: int, db: Session):
    """
    将项目下的所有 B 池 URL 写入一个 Redis 列表 (用于轮询)
    """
    # 查出所有的 B 池 URL
    landings = db.query(LandingDomain).filter(LandingDomain.project_id == project_id, LandingDomain.status == 'ok').all()
    urls = [l.url for l in landings]
    
    # 使用 Redis List 结构存储，方便随机获取
    redis_key = "project:" + str(project_id) + ":landing_urls"
    
    try:
        # 清空旧列表，写入新列表
        r.delete(redis_key)
        if urls:
            r.rpush(redis_key, *urls)
        print(">>> Redis B Pool Sync: Project " + str(project_id) + " 共有 " + str(len(urls)) + " 条链接")
    except redis.exceptions.ConnectionError:
        print("!!! Redis B Pool Sync 失败.")

# --- 补全缺失的 NS 检查函数 (修复 500 错误) ---
def check_ns_status(domain_obj):
    """检查域名的 NS 记录状态"""
    try:
        expected_ns = domain_obj.ns_servers.split(",") if domain_obj.ns_servers else []
        if not expected_ns:
            return "unknown", "未配置预期 NS 服务器"
        
        resolver = dns.resolver.Resolver()
        resolver.timeout = 10
        resolver.lifetime = 10
        resolver.nameservers = ['1.1.1.1', '8.8.8.8']

        answers = resolver.resolve(domain_obj.domain, 'NS')
        current_ns = [str(rdata).lower().rstrip('.') for rdata in answers]
        
        # 检查是否包含（只要包含预期的即可，顺序无关）
        is_active = all(ns in current_ns for ns in expected_ns)
        
        if is_active:
            return "active", "NS 记录已生效: " + ', '.join(current_ns)
        else:
            return "pending", "NS 记录未生效。当前: " + ', '.join(current_ns) + "，预期: " + ', '.join(expected_ns)
    except dns.resolver.NoAnswer:
        return "failed", "域名查询无 NS 记录"
    except dns.resolver.NXDOMAIN:
        return "failed", "域名不存在"
    except Exception as e:
        return "failed", "DNS 查询失败: " + str(e)

# ================= 接口区域 =================

@app.post("/api/login")
async def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    # 查数据库验证
    user = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()
    if not user or form_data.password != user.password:
        raise HTTPException(status_code=400, detail="账号或密码错误")
    
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/user/update")
async def update_admin_user(req: UpdateUserRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    # 只能修改当前登录用户的密码
    user = db.query(AdminUser).filter(AdminUser.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查新用户名是否冲突
    if req.username != current_user:
        exists = db.query(AdminUser).filter(AdminUser.username == req.username).first()
        if exists: raise HTTPException(status_code=400, detail="用户名已存在")

    user.username = req.username
    user.password = req.password
    db.commit()
    return {"code": 200, "message": "账户已更新，请重新登录"}

@app.post("/api/entry_domains/update_path")
async def update_entry_domain_path(req: UpdateEntryPath, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """更新单个入口域名的自定义访问路径"""
    domain_entry = db.query(EntryDomain).filter(EntryDomain.id == req.domain_id).first()

    if not domain_entry:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    # 检查路径是否被其他域名占用
    if req.custom_path:
        existing_path_domain = db.query(EntryDomain).filter(
            EntryDomain.id != req.domain_id,
            EntryDomain.custom_path == req.custom_path
        ).first()
        if existing_path_domain:
            raise HTTPException(status_code=400, detail="路径 " + req.custom_path + " 已被域名 " + existing_path_domain.domain + " 占用")

    # 更新路径
    domain_entry.custom_path = req.custom_path
    db.commit()
    
    # 同步到 Redis
    sync_domain_to_redis(domain_entry)

    return {"code": 200, "message": "域名 " + domain_entry.domain + " 路径已更新为 /" + req.custom_path + " "}

# --- 系统设置接口 ---
@app.post("/api/settings")
async def save_settings(req: SettingRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    if req.cf_token: db.merge(SystemSetting(key="cf_token", value=req.cf_token))
    if req.aliyun_key: db.merge(SystemSetting(key="aliyun_key", value=req.aliyun_key))
    if req.aliyun_secret: db.merge(SystemSetting(key="aliyun_secret", value=req.aliyun_secret))
    db.commit()
    return {"code": 200, "message": "系统设置已保存"}

@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    settings = db.query(SystemSetting).all()
    data = {s.key: s.value for s in settings}
    return {"code": 200, "data": data}

# --- 项目管理接口 ---
@app.post("/api/projects")
async def create_project(req: ProjectCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    exists = db.query(Project).filter(Project.name == req.name).first()
    if exists: raise HTTPException(status_code=400, detail="项目名称已存在")
    new_proj = Project(name=req.name)
    db.add(new_proj)
    db.commit()
    return {"code": 200, "message": "项目创建成功"}

@app.get("/api/projects")
async def list_projects(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    projs = db.query(Project).all()
    projs_data = []
    for p in projs:
        p_dict = p.__dict__.copy()
        p_dict['entry_count'] = len(p.entry_domains)
        p_dict['landing_count'] = len(p.landing_domains)
        projs_data.append(p_dict)
    return {"code": 200, "data": projs_data}

@app.get("/api/projects/{project_id}")
async def get_project_details(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    
    return {
        "code": 200, 
        "data": {
            "id": project.id,
            "name": project.name,
            "entry_domains": [d.__dict__.copy() for d in project.entry_domains],
            "landing_domains": [d.__dict__.copy() for d in project.landing_domains]
        }
    }

# 批量绑定 A 池
@app.post("/api/projects/{project_id}/bind_entry")
async def bind_entry_domain(project_id: int, req: BulkBindEntryRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    count = 0
    for domain_id in req.domain_ids:
        domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id).first()
        if domain:
            domain.project_id = project_id
            db.commit()
            sync_domain_to_redis(domain)
            count += 1
            
    return {"code": 200, "message": "成功绑定 " + str(count) + " 个域名到该项目"}

# 批量添加 B 池
@app.post("/api/projects/{project_id}/landing")
async def add_landing_page(project_id: int, req: BulkLandingCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    urls = [url.strip() for url in req.urls.split('\n') if url.strip()]
    count = 0
    for url in urls:
        if not url.startswith(("http://", "https://")): continue
        new_landing = LandingDomain(
            url=url,
            project_id=project_id,
            status="ok"
        )
        db.add(new_landing)
        count += 1
    db.commit()
    sync_landing_pool_to_redis(project_id, db) 
    return {"code": 200, "message": "成功添加 " + str(count) + " 个落地页"}

# --- 域名相关接口 ---
@app.get("/api/domains")
async def get_domains(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    domains = db.query(EntryDomain).all()
    return {"code": 200, "data": [d.__dict__.copy() for d in domains]}

@app.get("/api/domains/unused")
async def get_unused_domains(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    domains = db.query(EntryDomain).filter(EntryDomain.project_id == None).all()
    return {"code": 200, "data": [d.__dict__.copy() for d in domains]}

@app.get("/api/cloudflare/scan")
async def scan_cloudflare(token: Optional[str] = None, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    # 1. 尝试从数据库拿 Token
    if not token:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "cf_token").first()
        if setting and setting.value:
            token = setting.value
    
    if not token:
        raise HTTPException(status_code=400, detail="请先在设置页保存 Token，或手动输入")

    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("https://api.cloudflare.com/client/v4/zones", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="连接 Cloudflare 失败，Token 可能无效")
            data = resp.json()
            zones = []
            for item in data.get("result", []):
                # 获取 Cloudflare 返回的 name_servers
                ns_list = item.get("name_servers", [])
                zones.append({
                    "name": item["name"], 
                    "id": item["id"], 
                    "status": item["status"],
                    "name_servers": ns_list
                })
            return {"code": 200, "data": zones}
        except Exception as e:
             raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cloudflare/import")
async def import_cf_domains(req: ImportRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    count = 0
    for item in req.domains:
        exists = db.query(EntryDomain).filter(EntryDomain.domain == item["name"]).first()
        if not exists:
            ns_raw = item.get("name_servers", [])
            ns_str = ",".join(ns_raw) if isinstance(ns_raw, list) else ""

            new_domain = EntryDomain(
                domain=item["name"],
                provider="cloudflare",
                status="ok",
                zone_id=item["id"],
                custom_path=generate_random_path(),
                ns_servers=ns_str,
                ns_status="pending" if ns_str else "unknown"
            )
            db.add(new_domain)
            db.commit()
            sync_domain_to_redis(new_domain)
            count += 1
    return {"code": 200, "message": "成功导入 " + str(count) + " 个域名"}

# 切换线路
@app.post("/api/domains/{domain_id}/switch")
async def switch_domain_route(domain_id: int, request: DomainSwitchRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    domain.provider = request.target_provider
    db.commit()
    sync_domain_to_redis(domain)
    return {"code": 200, "message": "已切换至 " + request.target_provider}

@app.delete("/api/domains/{domain_id}")
async def delete_domain(domain_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    try:
        r.delete("domain:" + domain.domain)
    except: pass
    db.delete(domain)
    db.commit()
    return {"code": 200, "message": "删除成功"}

# 单个绑定操作
@app.post("/api/projects/{project_id}/landing_single")
async def add_landing_page_single(project_id: int, req: LandingCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    if not req.url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL 必须以 http 或 https 开头")
    new_landing = LandingDomain(url=req.url, project_id=project_id, status="ok")
    db.add(new_landing)
    db.commit()
    return {"code": 200, "message": "落地页添加成功"}

@app.post("/api/projects/{project_id}/bind_entry_single")
async def bind_entry_domain_single(project_id: int, req: BindEntryRequest, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    domain = db.query(EntryDomain).filter(EntryDomain.id == req.domain_id).first()
    if not domain: raise HTTPException(status_code=404, detail="域名不存在")
    domain.project_id = project_id
    db.commit()
    sync_domain_to_redis(domain)
    return {"code": 200, "message": "域名已绑定到该项目"}

@app.delete("/api/projects/{project_id}/entry/{domain_id}")
async def unbind_entry_domain(project_id: int, domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id, EntryDomain.project_id == project_id).first()
    if not domain: raise HTTPException(status_code=404, detail="域名未绑定到该项目")
    domain.project_id = None
    db.commit()
    sync_domain_to_redis(domain) 
    return {"code": 200, "message": "域名已解除绑定，回归闲置池"}

@app.delete("/api/projects/{project_id}/landing/{landing_id}")
async def delete_landing_page(project_id: int, landing_id: int, db: Session = Depends(get_db)):
    landing = db.query(LandingDomain).filter(LandingDomain.id == landing_id, LandingDomain.project_id == project_id).first()
    if not landing: raise HTTPException(status_code=404, detail="落地页不存在")
    db.delete(landing)
    db.commit()
    sync_landing_pool_to_redis(project_id, db)
    return {"code": 200, "message": "落地页已删除"}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    
    for domain in project.entry_domains:
        domain.project_id = None
        sync_domain_to_redis(domain) 
    
    db.query(LandingDomain).filter(LandingDomain.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return {"code": 200, "message": "项目 " + project.name + " 已彻底删除"}

@app.delete("/api/projects/{project_id}/entry/bulk")
async def bulk_delete_entry(project_id: int, req: BulkDeleteEntry, db: Session = Depends(get_db)):
    count = 0
    for domain_id in req.entry_ids:
        domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id, EntryDomain.project_id == project_id).first()
        if domain:
            domain.project_id = None
            db.commit()
            sync_domain_to_redis(domain)
            count += 1
    return {"code": 200, "message": "成功解绑 " + str(count) + " 个入口域名"}

@app.post("/api/projects/{project_id}/landing/bulk_delete")
async def bulk_delete_landing_domains_post(project_id: int, req: BulkDeleteLanding, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    if not req.landing_ids:
        raise HTTPException(status_code=400, detail="未选择任何B池落地页")
    
    delete_count = db.query(LandingDomain).filter(
        LandingDomain.project_id == project_id,
        LandingDomain.id.in_(req.landing_ids)
    ).delete(synchronize_session=False) 
    
    db.commit()
    sync_landing_pool_to_redis(project_id, db)
    return {"code": 200, "message": "成功删除 " + str(delete_count) + " 个落地页"}

# 引入 worker 里的核心检测逻辑
from worker import check_domain_status 

@app.post("/api/projects/{project_id}/manual_check")
async def manual_health_check_project(project_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """手动触发当前项目的 B 池健康检查 (同步执行)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    
    updated_count = 0
    for landing in project.landing_domains:
        status = check_domain_status(landing.url)
        if landing.status != status:
            landing.status = status
            db.commit()
            updated_count += 1
    return {"code": 200, "message": "手动检查完成，更新了 " + str(updated_count) + " 个落地页状态"}

# --- 新增 Cloudflare 账户信息获取接口 ---
@app.get("/api/cloudflare/account")
async def get_cloudflare_account(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """获取 Cloudflare 账户信息"""
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "cf_token").first()
        if not setting or not setting.value:
            raise HTTPException(status_code=400, detail="请先配置 Cloudflare Token")
        
        headers = {"Authorization": "Bearer " + setting.value, "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            # 获取账户列表
            resp = await client.get("https://api.cloudflare.com/client/v4/accounts", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="获取账户信息失败")
            
            accounts = resp.json()
            if not accounts.get("result"):
                raise HTTPException(status_code=400, detail="未找到 Cloudflare 账户")
            
            # 使用第一个账户（通常是最主要的）
            account = accounts["result"][0]
            return {
                "code": 200,
                "data": {
                    "id": account["id"],
                    "name": account["name"]
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取账户信息失败: " + str(e))

@app.get("/api/cloudflare/verify_token")
async def verify_cloudflare_token(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """验证 Cloudflare Token 是否有效"""
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "cf_token").first()
        if not setting or not setting.value:
            return {"code": 400, "valid": False, "message": "未配置 Cloudflare Token"}
        
        cf_token = setting.value
        headers = {"Authorization": "Bearer " + cf_token, "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            # 简化验证：只测试最基本的权限
            zone_resp = await client.get("https://api.cloudflare.com/client/v4/zones?per_page=1", headers=headers)
            
            if zone_resp.status_code == 200:
                zone_data = zone_resp.json()
                return {
                    "code": 200,
                    "valid": True,
                    "message": "Token 验证成功",
                    "zone_count": len(zone_data.get("result", [])),
                    "permissions": "具备 Zone 读取权限"
                }
            else:
                error_data = zone_resp.json()
                error_msg = error_data.get('errors', [{}])[0].get('message', 'Token 无效')
                error_code = error_data.get('errors', [{}])[0].get('code', '未知错误码')
                
                return {
                    "code": 400,
                    "valid": False,
                    "message": "Token 验证失败: " + error_msg,
                    "error_code": error_code,
                    "required_permissions": "Zone:Read, Zone:Write, Account:Read",
                    "suggested_fix": "请在 Cloudflare 创建具备 'Edit zone DNS' 权限的 Token"
                }
                
    except Exception as e:
        return {
            "code": 500,
            "valid": False,
            "message": "验证过程中发生错误: " + str(e)
        }

@app.post("/api/aliyun/scan_for_selection")
async def aliyun_scan_for_selection(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """扫描阿里云账户下的域名，并返回列表供前端选择"""
    try:
        keys = db.query(SystemSetting).filter(SystemSetting.key.in_(["aliyun_key", "aliyun_secret"])).all()
        settings = {k.key: k.value for k in keys}
        aliyun_key = settings.get("aliyun_key")
        aliyun_secret = settings.get("aliyun_secret")
        
        if not aliyun_key or not aliyun_secret:
            raise HTTPException(status_code=400, detail="请先在设置页配置完整的阿里云密钥")

        print(">>> 开始扫描阿里云域名，Key: " + aliyun_key[:8] + "...")
        client = AcsClient(aliyun_key, aliyun_secret, 'ap-southeast-1')
        request = QueryDomainListRequest.QueryDomainListRequest()
        request.set_PageSize(50)
        request.set_PageNum(1)
        response = client.do_action_with_exception(request)
        response_data = json.loads(response.decode('utf-8'))
        
        # 检查API返回错误
        if 'Code' in response_data and response_data['Code'] != '200':
            error_msg = "阿里云API错误: " + response_data.get('Message', '未知错误') + " (代码: " + response_data['Code'] + ")"
            raise HTTPException(status_code=500, detail=error_msg)

        domains = []
        for item in response_data.get('Data', {}).get('Domain', []):
            domains.append({
                "name": item.get('DomainName', ''),
                "status": item.get('DomainStatus', 'Unknown'),
                "expire_date": item.get('ExpirationDate', ''),
                "registration_date": item.get('RegistrationDate', '')
            })
        print(">>> 成功获取 " + str(len(domains)) + " 个域名")
        return {"code": 200, "data": domains}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/aliyun/list_domains")
async def list_aliyun_domains(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """获取阿里云域名列表"""
    try:
        keys = db.query(SystemSetting).filter(SystemSetting.key.in_(["aliyun_key", "aliyun_secret"])).all()
        settings = {k.key: k.value for k in keys}
        aliyun_key = settings.get("aliyun_key")
        aliyun_secret = settings.get("aliyun_secret")
        
        if not aliyun_key or not aliyun_secret:
            raise HTTPException(status_code=400, detail="请先在设置页配置阿里云密钥")

        client = AcsClient(aliyun_key, aliyun_secret, 'ap-southeast-1')
        request = QueryDomainListRequest.QueryDomainListRequest()
        request.set_PageSize(100)
        request.set_PageNum(1)
        
        # 使用增强的调试功能
        response_data = debug_aliyun_request(client, request, "QueryDomainList")
        
        domains = []
        for item in response_data.get('Data', {}).get('Domain', []):
            domains.append({
                "name": item['DomainName'], 
                "status": item.get('DomainStatus', 'Active')
            })
            
        return {"code": 200, "data": domains}
        
    except ServerException as e:
        detailed_error = "阿里云服务错误: [" + e.get_error_code() + "] " + e.get_error_msg()
        raise HTTPException(status_code=500, detail=detailed_error)
    except ClientException as e:
        detailed_error = "客户端错误: [" + e.get_error_code() + "] " + e.get_error_msg()
        raise HTTPException(status_code=400, detail=detailed_error)
    except Exception as e:
        detailed_error = "未知错误: " + str(e)
        raise HTTPException(status_code=500, detail=detailed_error)

@app.post("/api/aliyun/debug_scan")
async def debug_aliyun_scan(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    调试接口：获取阿里云API的原始响应
    """
    try:
        keys = db.query(SystemSetting).filter(SystemSetting.key.in_(["aliyun_key", "aliyun_secret"])).all()
        settings = {k.key: k.value for k in keys}
        aliyun_key = settings.get("aliyun_key")
        aliyun_secret = settings.get("aliyun_secret")
        
        if not aliyun_key or not aliyun_secret:
            return {"code": 400, "message": "密钥未配置"}

        # 测试不同区域
        regions = ['ap-southeast-1', 'us-west-1', 'eu-central-1']
        results = {}
        
        for region in regions:
            try:
                print(">>> 测试区域: " + region)
                client = AcsClient(aliyun_key, aliyun_secret, region)
                request = QueryDomainListRequest.QueryDomainListRequest()
                request.set_PageSize(5)
                request.set_PageNum(1)
                
                response = client.do_action_with_exception(request)
                response_data = json.loads(response.decode('utf-8'))
                
                results[region] = {
                    "status": "success",
                    "data": response_data
                }
                print(">>> 区域 " + region + " 请求成功")
                
            except Exception as e:
                results[region] = {
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error_code": getattr(e, 'error_code', 'N/A'),
                    "error_msg": getattr(e, 'error_msg', 'N/A')
                }
                print(">>> 区域 " + region + " 请求失败: " + str(e))
        
        return {
            "code": 200, 
            "message": "调试完成", 
            "results": results,
            "used_key": aliyun_key[:8] + "..." + aliyun_key[-4:] if aliyun_key else "None"
        }
        
    except Exception as e:
        return {
            "code": 500, 
            "message": "调试失败: " + str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@app.post("/api/aliyun/setup_domain")
async def aliyun_setup_domain(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """一键处理：扫描所有域名并接入"""
    # 获取阿里云密钥
    keys = db.query(SystemSetting).filter(SystemSetting.key.in_(["aliyun_key", "aliyun_secret"])).all()
    settings = {k.key: k.value for k in keys}
    aliyun_key = settings.get("aliyun_key")
    aliyun_secret = settings.get("aliyun_secret")
    
    if not aliyun_key or not aliyun_secret:
        raise HTTPException(status_code=400, detail="请先在设置页配置完整的阿里云密钥")

    # 1. 假设 CF Nameservers 已知 (请替换为你真实的 CF Nameservers)
    target_ns = ["ns1.cloudflare.com", "ns2.cloudflare.com"]
    
    client = AcsClient(aliyun_key, aliyun_secret, 'ap-southeast-1') # 国际站区域修正

    domain_list_request = QueryDomainListRequest.QueryDomainListRequest()
    domain_list_request.set_PageSize(100)
    domain_list_request.set_PageNum(1) 
    
    domains_to_modify = []
    
    try:
        # --- 核心操作：执行查询 ---
        response = client.do_action_with_exception(domain_list_request)
        data = json.loads(response.decode('utf-8'))
        
        for domain_item in data.get('Data', {}).get('Domain', []):
            domains_to_modify.append(domain_item['DomainName'])
        
        if not domains_to_modify:
            return {"code": 200, "message": "未在阿里云账号下发现任何域名。"}

        # 5. 核心：执行批量修改 NS (使用 SaveBatchTaskForModifyingDomainDnsRequest)
        batch_modify_request = SaveBatchTaskForModifyingDomainDnsRequest.SaveBatchTaskForModifyingDomainDnsRequest()
        
        # --- 修复核心：循环添加 DomainName.1, DomainName.2 等参数 ---
        
        # 添加所有要修改的域名
        for i, domain in enumerate(domains_to_modify):
            # 域名参数格式必须是 DomainName.1, DomainName.2, ...
            batch_modify_request.add_query_param('DomainName.%d' % (i + 1), domain)
            
        # 添加目标 DNS 服务器列表
        for i, dns in enumerate(target_ns):
             # DNS 服务器参数格式必须是 DomainNameServer.1, DomainNameServer.2, ...
             batch_modify_request.add_query_param('DomainNameServer.%d' % (i + 1), dns)

        # 必须设置 AliyunDns 为 False，否则 API 报错
        batch_modify_request.add_query_param('AliyunDns', 'False') 

        # 执行批量修改 NS 操作
        client.do_action_with_exception(batch_modify_request)
        
        return {"code": 200, "message": "成功向阿里云发送了批量修改 NS 的请求，共 " + str(len(domains_to_modify)) + " 个域名。请等待解析生效后同步。"}

    except ServerException as e:
        # 强制返回 400，让前端清晰显示错误，而不是 500 Internal Error
        error_msg = "阿里云认证失败: 错误码: " + e.get_error_code() + " - " + e.get_error_msg()
        raise HTTPException(status_code=400, detail=error_msg)
    except ClientException as e:
        error_msg = "客户端错误: 请检查 Access Key ID/Secret 是否正确 - " + e.get_error_code()
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail="未知错误: " + str(e))

@app.post("/api/aliyun/execute_setup")
async def execute_aliyun_setup(req: AliyunDomainImport, db: Session = Depends(get_db)):
    """手动执行阿里云域名接入（单个或多个）"""
    keys = db.query(SystemSetting).filter(SystemSetting.key.in_(["aliyun_key", "aliyun_secret", "cf_token"])).all()
    settings = {k.key: k.value for k in keys}
    
    aliyun_key = settings.get("aliyun_key")
    aliyun_secret = settings.get("aliyun_secret")
    cf_token = settings.get("cf_token")
    
    if not cf_token or not aliyun_key:
        raise HTTPException(status_code=400, detail="请检查密钥是否完整")

    cf_headers = {"Authorization": "Bearer " + cf_token, "Content-Type": "application/json"}
    aliyun_client = AcsClient(aliyun_key, aliyun_secret, 'ap-southeast-1')
    success_count = 0
    
    current_server_ip = await get_public_ip()

    async with httpx.AsyncClient() as client:
        for domain_name in req.domain_names:
            
            # --- 步骤 1: CF API 创建 Zone ---
            # 这里的 account ID 最好从 /accounts 接口获取，这里为了兼容暂用 placeholder
            zone_create_resp = await client.post(
                "https://api.cloudflare.com/client/v4/zones", 
                headers=cf_headers, 
                json={"name": domain_name, "account": {"id": "placeholder"}} 
            )
            
            if zone_create_resp.status_code == 200:
                cf_result = zone_create_resp.json()
                unique_ns = [ns.lower() for ns in cf_result['result']['name_servers']]
                zone_id = cf_result['result']['id']
                
                # --- 步骤 1.5: 自动添加 A 记录 (修复：显示详细报错) ---
                if current_server_ip:
                    try:
                        print(f">>> 正在解析 {domain_name} 到 {current_server_ip}")
                        dns_resp = await client.post(
                            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                            headers=cf_headers,
                            json={"type":"A","name":"@","content":current_server_ip.strip(),"ttl":1,"proxied":True}
                        )
                        if dns_resp.status_code != 200:
                            print(f"!!! [解析失败] {domain_name}: {dns_resp.text}")
                        else:
                            print(f">>> [解析成功] {domain_name}")
                    except Exception as e:
                        print(f"!!! [解析异常] {str(e)}")
                
                # --- 核心：自动防红配置 ---
                await auto_configure_cf_security(client, zone_id, cf_headers)
                
                # --- 步骤 2: 调用阿里云 API 修改 Nameserver ---
                modify_ns_request = SaveBatchTaskForModifyingDomainDnsRequest.SaveBatchTaskForModifyingDomainDnsRequest()
                modify_ns_request.add_query_param('DomainName.1', domain_name)
                for i, ns in enumerate(unique_ns):
                    modify_ns_request.add_query_param('DomainNameServer.%d' % (i + 1), ns)

                modify_ns_request.add_query_param('AliyunDns', 'False') 
                aliyun_client.do_action_with_exception(modify_ns_request)
                
                # --- 步骤 3: 存入本地 DB ---
                new_entry = EntryDomain(
                    domain=domain_name,
                    provider="cloudflare",
                    status="ok",
                    zone_id=zone_id,
                    custom_path=generate_random_path(),
                    ns_servers=",".join(unique_ns)
                )
                db.add(new_entry)
                db.commit()
                sync_domain_to_redis(new_entry)
                success_count += 1
            else:
                print("CF Zone Creation Failed for " + domain_name)

        return {"code": 200, "message": "成功接入 Cloudflare 和修改 NS 记录 " + str(success_count) + " 个域名"}

@app.post("/api/aliyun/scan_domains")
async def scan_aliyun_domains(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """扫描阿里云域名（遍历多区域）"""
    try:
        keys = db.query(SystemSetting).filter(SystemSetting.key.in_(["aliyun_key", "aliyun_secret"])).all()
        settings = {k.key: k.value for k in keys}
        aliyun_key = settings.get("aliyun_key")
        aliyun_secret = settings.get("aliyun_secret")
        
        if not aliyun_key or not aliyun_secret:
            raise HTTPException(status_code=400, detail="请先在设置页配置完整的阿里云密钥")

        regions = ['ap-southeast-1', 'cn-hangzhou', 'cn-beijing', 'us-west-1']
        domains = []
        
        for region in regions:
            try:
                client = AcsClient(aliyun_key, aliyun_secret, region)
                request = QueryDomainListRequest.QueryDomainListRequest()
                request.set_PageSize(100)
                request.set_PageNum(1)
                
                response = client.do_action_with_exception(request)
                response_data = json.loads(response.decode('utf-8'))
                
                if 'Code' in response_data and response_data['Code'] != '200':
                    continue
                
                domain_list = response_data.get('Data', {}).get('Domain', [])
                for item in domain_list:
                    domain_name = item.get('DomainName', '')
                    if domain_name and domain_name not in [d['name'] for d in domains]:
                        domains.append({
                            "name": domain_name,
                            "status": item.get('DomainStatus', 'Unknown'),
                            "expire_date": item.get('ExpirationDate', ''),
                            "registration_date": item.get('RegistrationDate', ''),
                            "region": region
                        })
                if domains: break 
            except Exception:
                continue
        
        return {"code": 200, "data": domains}
    except Exception as e:
        raise HTTPException(status_code=500, detail="扫描域名失败: " + str(e))

@app.post("/api/aliyun/setup_domains")
async def setup_aliyun_domains(req: AliyunDomainImport, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """将阿里云域名批量自动接入 Cloudflare (带全自动防红配置)"""
    try:
        keys = db.query(SystemSetting).filter(SystemSetting.key.in_([
            "aliyun_key", "aliyun_secret", "cf_token"
        ])).all()
        settings = {k.key: k.value for k in keys}
        
        aliyun_key = settings.get("aliyun_key")
        aliyun_secret = settings.get("aliyun_secret")
        cf_token = settings.get("cf_token")
        
        if not all([aliyun_key, aliyun_secret, cf_token]):
            raise HTTPException(status_code=400, detail="请先完整配置阿里云和Cloudflare密钥")

        success_count = 0
        failed_domains = []
        
        current_server_ip = await get_public_ip()
        
        for domain_name in req.domain_names:
            try:
                print(">>> 开始处理域名: " + domain_name)
                
                cf_headers = {"Authorization": "Bearer " + cf_token, "Content-Type": "application/json"}
                async with httpx.AsyncClient() as client:
                    # 获取账户信息
                    account_resp = await client.get("https://api.cloudflare.com/client/v4/accounts", headers=cf_headers)
                    account_data = account_resp.json()
                    
                    account_id = None
                    if account_resp.status_code == 200 and account_data.get("result"):
                        account_id = account_data["result"][0]["id"]
                    
                    # 创建 Zone
                    create_data = {"name": domain_name, "jump_start": False, "type": "full"}
                    if account_id: create_data["account"] = {"id": account_id}
                    
                    create_resp = await client.post(
                        "https://api.cloudflare.com/client/v4/zones",
                        headers=cf_headers,
                        json=create_data,
                        timeout=30
                    )
                    
                    create_result = create_resp.json()
                    
                    zone_id = None
                    name_servers = []
                    
                    if create_resp.status_code == 200:
                        zone_info = create_result["result"]
                        zone_id = zone_info["id"]
                        name_servers = zone_info.get("name_servers", [])
                    else:
                        # 检查是否域名已存在
                        if "already exists" in str(create_result).lower():
                            search_resp = await client.get(f"https://api.cloudflare.com/client/v4/zones?name={domain_name}", headers=cf_headers)
                            if search_resp.status_code == 200:
                                zones_data = search_resp.json()
                                if zones_data.get("result"):
                                    zone_info = zones_data["result"][0]
                                    zone_id = zone_info["id"]
                                    name_servers = zone_info.get("name_servers", [])
                        
                        if not zone_id:
                            raise Exception("Zone 创建/获取失败")

                    if not name_servers:
                        raise Exception("无法获取 Cloudflare NameServers")
                    
                    # --- 1. 自动添加 A 记录 (修复：显示详细报错) ---
                    if current_server_ip:
                        try:
                            print(f">>> 正在解析 {domain_name} 到 {current_server_ip}")
                            dns_resp = await client.post(
                                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                                headers=cf_headers,
                                json={"type":"A","name":"@","content":current_server_ip.strip(),"ttl":1,"proxied":True}
                            )
                            if dns_resp.status_code != 200:
                                print(f"!!! [解析失败] {domain_name}: {dns_resp.text}")
                            else:
                                print(f">>> [解析成功] {domain_name}")
                        except Exception as e:
                            print(f"!!! [解析异常] {str(e)}")
                    else:
                        print(f"!!! [跳过解析] 未能获取到服务器 IP")

                    # --- 2. 【核心新增】自动应用防红配置 ---
                    await auto_configure_cf_security(client, zone_id, cf_headers)

                # 3. 在阿里云修改 NameServers
                aliyun_client = AcsClient(aliyun_key, aliyun_secret, 'ap-southeast-1')
                modify_request = SaveBatchTaskForModifyingDomainDnsRequest.SaveBatchTaskForModifyingDomainDnsRequest()
                modify_request.add_query_param('DomainName.1', domain_name)
                for i, ns in enumerate(name_servers[:2]):
                    modify_request.add_query_param('DomainNameServer.' + str(i+1), ns)
                modify_request.add_query_param('AliyunDns', 'False')
                
                try:
                    aliyun_client.do_action_with_exception(modify_request)
                except Exception as e:
                    print(">>> 阿里云 NS 修改异常 (可能已生效): " + str(e))
                
                # 4. 保存到数据库
                new_domain = EntryDomain(
                    domain=domain_name,
                    provider="cloudflare",
                    status="pending",
                    zone_id=zone_id,
                    custom_path=generate_random_path(),
                    ns_servers=",".join(name_servers),
                    ns_status="pending",
                    last_ns_check=datetime.utcnow()
                )
                db.add(new_domain)
                db.commit()
                sync_domain_to_redis(new_domain)
                
                success_count += 1
                
            except Exception as e:
                print(f"!!! 处理域名 {domain_name} 失败: {str(e)}")
                failed_domains.append(domain_name + ": " + str(e))
                continue
        
        message = "成功接入 " + str(success_count) + " 个域名到 Cloudflare"
        if failed_domains:
            message += "，失败 " + str(len(failed_domains)) + " 个"
        
        return {
            "code": 200,
            "message": message,
            "success_count": success_count,
            "failed_domains": failed_domains
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print("!!! 批量接入错误: " + str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="批量接入失败: " + str(e))

@app.get("/api/domains/{domain_id}/ns_status")
async def check_ns_status_endpoint(domain_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """检查域名NS记录是否已生效"""
    domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id).first()
    if not domain: raise HTTPException(status_code=404, detail="域名不存在")
    
    try:
        expected_ns = domain.ns_servers.split(",") if domain.ns_servers else []
        resolver = dns.resolver.Resolver()
        resolver.timeout = 10
        resolver.lifetime = 10
        answers = resolver.resolve(domain.domain, 'NS')
        current_ns = [str(rdata).lower().rstrip('.') for rdata in answers]
        is_active = all(ns in current_ns for ns in expected_ns)
        
        if is_active and domain.status == 'pending':
            domain.status = 'ok'
            db.commit()
            sync_domain_to_redis(domain)
        
        return {
            "code": 200,
            "is_active": is_active,
            "expected_ns": expected_ns,
            "current_ns": current_ns,
            "message": "NS记录已生效" if is_active else "NS记录尚未生效"
        }
    except Exception as e:
        return {"code": 200, "is_active": False, "message": str(e)}

@app.get("/api/domain_status")
async def get_domain_status_list(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(EntryDomain)
    if status: query = query.filter(EntryDomain.ns_status == status)
    domains = query.all()
    
    return {"code": 200, "data": [{
        "id": d.id,
        "domain": d.domain,
        "provider": d.provider,
        "ns_status": d.ns_status or "unknown",
        "status": d.status,
        "last_ns_check": d.last_ns_check,
        "ns_check_count": d.ns_check_count or 0,
        "ns_servers": d.ns_servers,
        "custom_path": d.custom_path,
        "project_id": d.project_id
    } for d in domains]}

@app.post("/api/domain_status/check")
async def manual_domain_status_check(req: DomainStatusCheckRequest, db: Session = Depends(get_db)):
    results = []
    for domain_id in req.domain_ids:
        domain = db.query(EntryDomain).filter(EntryDomain.id == domain_id).first()
        if not domain: continue
        
        ns_status, message = check_ns_status(domain)
        db.add(DomainStatusLog(domain_id=domain.id, check_type="manual_ns_check", status=ns_status, message=message))
        
        domain.ns_status = ns_status
        domain.last_ns_check = datetime.utcnow()
        domain.ns_check_count = (domain.ns_check_count or 0) + 1
        
        if ns_status == "active" and domain.status != "ok":
            domain.status = "ok"
        
        results.append({"domain_id": domain.id, "new_status": ns_status, "message": message})
    
    db.commit()
    return {"code": 200, "message": "检查完成", "results": results}

@app.post("/api/domain_status/init_ns_status")
async def init_domain_ns_status(db: Session = Depends(get_db)):
    domains = db.query(EntryDomain).all()
    count = 0
    for domain in domains:
        if not domain.ns_status:
            domain.ns_status = "pending" if domain.ns_servers else "unknown"
            count += 1
    db.commit()
    return {"code": 200, "message": "已初始化 " + str(count) + " 个域名"}

@app.post("/api/ns_check/run_all")
async def run_all_ns_checks(db: Session = Depends(get_db)):
    try:
        from worker import run_ns_checks
        import threading
        threading.Thread(target=run_ns_checks, daemon=True).start()
        return {"code": 200, "message": "NS 检查任务后台启动中"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="启动失败: " + str(e))

@app.get("/api/domain_status/{domain_id}/logs")
async def get_domain_status_logs(
    domain_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """获取域名状态检查日志"""
    logs = db.query(DomainStatusLog).filter(
        DomainStatusLog.domain_id == domain_id
    ).order_by(
        DomainStatusLog.created_at.desc()
    ).limit(limit).all()
    
    log_data = []
    for log in logs:
        log_data.append({
            "id": log.id,
            "check_type": log.check_type,
            "status": log.status,
            "message": log.message,
            "created_at": log.created_at
        })
    
    return {"code": 200, "data": log_data}

@app.on_event("startup")
async def on_startup():
    try:
        init_db()
        print(">>> 数据库初始化完成")
        
        # --- 核心：初始化随机管理员 ---
        db = SessionLocal()
        try:
            # 检查是否存在用户
            if not db.query(AdminUser).first():
                # 从环境变量获取安装脚本生成的随机密码
                env_user = os.getenv("ADMIN_USER", "admin")
                env_pass = os.getenv("ADMIN_PASS", "admin888")
                
                new_admin = AdminUser(username=env_user, password=env_pass)
                db.add(new_admin)
                db.commit()
                print(f">>> 初始化管理员账户: {env_user}")
        finally:
            db.close()
        # --------------------------------
        
        # 延迟启动 worker
        import asyncio
        await asyncio.sleep(2)
        try:
            from worker import start_scheduler
            start_scheduler()
            print(">>> 后台任务调度器启动成功")
        except Exception as e:
            print(f">>> 后台 Worker 启动失败: {str(e)}")
            
    except Exception as e:
        print(f">>> 系统启动失败: {str(e)}")
        import traceback
        traceback.print_exc()

@app.get("/api/health")
async def health_check():
    return {"code": 200, "status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/worker/status")
async def worker_status():
    try:
        from worker import scheduler
        jobs = scheduler.get_jobs()
        return {"code": 200, "scheduler_running": scheduler.running, "active_jobs": len(jobs)}
    except Exception as e:
        return {"code": 500, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)