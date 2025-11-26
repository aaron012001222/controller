# worker.py - 修复版本
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import urllib3
import time
import dns.resolver
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import traceback

try:
    from database import SessionLocal, EntryDomain, LandingDomain, DomainStatusLog
except ImportError as e:
    print(f">>> 导入数据库模块失败: {e}")

from database import SessionLocal, EntryDomain, LandingDomain, DomainStatusLog

# 抑制警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_domain_status(url):
    """健康检查逻辑 - 增强伪装版"""
    if not url.startswith(('http://', 'https://')):
        return 'banned'
    
    # 伪装成 Chrome 浏览器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        # 增加 timeout 防止卡死，verify=False 忽略证书错误
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        # 核心修改：有些网站反爬会返回 403，但这说明网站是活着的
        # 如果是 403/401 (权限不足)，也视为"ok" (因为网站通了)
        # 只有 404 (找不到) 或 5xx (服务器崩了) 才算失效
        if response.status_code < 500 and response.status_code != 404:
            return 'ok'
        else:
            return 'banned'
            
    except requests.exceptions.RequestException:
        return 'banned'
    except Exception:
        return 'banned'

def check_ns_status(domain_obj):
    """NS 状态检查逻辑 - 修复版本"""
    try:
        # 获取预期的 NameServers
        expected_ns = domain_obj.ns_servers.split(",") if domain_obj.ns_servers else []
        if not expected_ns:
            return "unknown", "未配置预期 NS 服务器"
        
        # 清理 NS 服务器名称
        expected_ns = [ns.strip().lower().rstrip('.') for ns in expected_ns]
        
        # 查询当前域名的 NS 记录
        resolver = dns.resolver.Resolver()
        resolver.timeout = 10
        resolver.lifetime = 10
        
        answers = resolver.resolve(domain_obj.domain, 'NS')
        current_ns = [str(rdata).lower().rstrip('.') for rdata in answers]
        
        # 检查是否匹配 - 修复逻辑
        is_active = all(expected_ns in current_ns for expected_ns in expected_ns)
        
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

def init_ns_status_for_existing_domains():
    """为现有域名初始化 NS 状态"""
    db = SessionLocal()
    try:
        # 查找所有没有 NS 状态的域名
        domains = db.query(EntryDomain).filter(
            EntryDomain.ns_status == None
        ).all()
        
        updated_count = 0
        for domain in domains:
            if domain.ns_servers:
                # 如果有 NS 服务器信息，设置为 pending
                domain.ns_status = "pending"
            else:
                # 没有 NS 服务器信息，设置为 unknown
                domain.ns_status = "unknown"
            updated_count += 1
        
        db.commit()
        if updated_count > 0:
            print(f">>> 初始化了 {updated_count} 个域名的 NS 状态")
            
    except Exception as e:
        print(f">>> 初始化 NS 状态失败: {str(e)}")
        db.rollback()
    finally:
        db.close()

def run_ns_checks():
    """NS 状态检查任务 - 修复版本"""
    print("[" + time.strftime('%H:%M:%S') + "] --- 开始 NS 状态检查 ---")
    
    db: Session = SessionLocal()
    
    try:
        # 检查所有有 NS 服务器信息的域名
        domains_to_check = db.query(EntryDomain).filter(
            EntryDomain.ns_servers != None,
            EntryDomain.ns_servers != ''
        ).all()
        
        updated_count = 0
        checked_count = 0
        
        for domain in domains_to_check:
            try:
                checked_count += 1
                old_status = domain.ns_status
                
                # 执行 NS 检查
                ns_status, message = check_ns_status(domain)
                
                # 记录检查日志
                log_entry = DomainStatusLog(
                    domain_id=domain.id,
                    check_type="ns_check",
                    status=ns_status,
                    message=message
                )
                db.add(log_entry)
                
                # 更新域名状态
                domain.ns_status = ns_status
                domain.last_ns_check = datetime.utcnow()
                domain.ns_check_count = (domain.ns_check_count or 0) + 1
                
                # 如果 NS 已生效，更新域名主状态
                if ns_status == "active" and domain.status != "ok":
                    domain.status = "ok"
                    print(f">>> 域名 {domain.domain} 状态已更新为 ok (NS 已生效)")
                
                if old_status != ns_status:
                    updated_count += 1
                    print(f">>> 域名 {domain.domain} NS 状态: {old_status} -> {ns_status}")
                else:
                    print(f">>> 域名 {domain.domain} NS 状态: {ns_status} (未变化)")
                    
            except Exception as e:
                print(f">>> 检查域名 {domain.domain} 失败: {str(e)}")
                # 记录错误日志
                error_log = DomainStatusLog(
                    domain_id=domain.id,
                    check_type="ns_check",
                    status="failed",
                    message=f"检查过程中发生错误: {str(e)}"
                )
                db.add(error_log)
                continue
        
        db.commit()
        print(f">>> NS 检查完成，检查了 {checked_count} 个域名，更新了 {updated_count} 个域名状态")
        
    except Exception as e:
        print(">>> NS 检查任务失败: " + str(e))
        print(">>> 详细错误: " + traceback.format_exc())
        db.rollback()
    finally:
        db.close()

def run_health_checks():
    """健康检查任务"""
    start_time = time.time()
    print("[" + time.strftime('%H:%M:%S') + "] --- 开始健康检查 Worker ---")
    
    db: Session = SessionLocal() 
    
    try:
        landing_domains = db.query(LandingDomain).all()
        updated_landing_count = 0
        
        for landing in landing_domains:
            try:
                old_status = landing.status
                status = check_domain_status(landing.url)
                
                if old_status != status:
                    landing.status = status
                    updated_landing_count += 1
                    print(f">>> 落地页 {landing.url} 状态: {old_status} -> {status}")
            except Exception as e:
                print(">>> 检查落地页 " + landing.url + " 失败: " + str(e))
                continue
        
        db.commit()
        
        end_time = time.time()
        print("[" + time.strftime('%H:%M:%S') + "] --- 健康检查完成，更新了 " + str(updated_landing_count) + " 条状态 (耗时: " + str(round(end_time - start_time, 2)) + "s) ---")

    except Exception as e:
        print(">>> Worker 任务失败: " + str(e))
        print(">>> 详细错误: " + traceback.format_exc())
        db.rollback()
    finally:
        db.close()

scheduler = BackgroundScheduler()

def start_scheduler():
    try:
        # 先初始化 NS 状态
        init_ns_status_for_existing_domains()
        
        # 健康检查：每5分钟一次
        scheduler.add_job(
            run_health_checks, 
            trigger=IntervalTrigger(minutes=5), 
            id='health_check_job', 
            name='Domain Health Check', 
            replace_existing=True
        )
        
        # NS 检查：每10分钟一次
        scheduler.add_job(
            run_ns_checks,
            trigger=IntervalTrigger(minutes=10),
            id='ns_check_job',
            name='NS Status Check',
            replace_existing=True
        )
        
        # 立即运行一次检查
        scheduler.add_job(run_health_checks, trigger='date', run_date=datetime.now())
        scheduler.add_job(run_ns_checks, trigger='date', run_date=datetime.now())
        
        scheduler.start()
        print(">>> 后台任务调度器启动成功")
        
        # 立即运行一次初始化检查
        run_ns_checks()
        
    except Exception as e:
        print(">>> 调度器启动失败: " + str(e))
        print(">>> 详细错误: " + traceback.format_exc())