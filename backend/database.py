from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./traffic.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 1. 系统设置表
class SystemSetting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

# 2. 项目/分组表
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    status = Column(String, default="on")
    safe_mode = Column(Boolean, default=True)

    entry_domains = relationship("EntryDomain", back_populates="project")
    landing_domains = relationship("LandingDomain", back_populates="project")

# 3. 入口域名表
class EntryDomain(Base):
    __tablename__ = "entry_domains"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True)
    provider = Column(String, default="cloudflare")
    zone_id = Column(String)
    status = Column(String, default="ok")
    custom_path = Column(String, nullable=True)
    ns_servers = Column(Text, nullable=True)
    ns_status = Column(String, default="unknown")
    last_ns_check = Column(DateTime, nullable=True)
    ns_check_count = Column(Integer, default=0)
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="entry_domains")

# 4. 落地页表
class LandingDomain(Base):
    __tablename__ = "landing_domains"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String)
    status = Column(String, default="ok")
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="landing_domains")

# 5. 域名状态日志表
class DomainStatusLog(Base):
    __tablename__ = "domain_status_logs"
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("entry_domains.id"))
    check_type = Column(String)
    status = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    domain = relationship("EntryDomain")

# 【核心新增】6. 管理员表
class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)

# 7. 实时流量统计表 (新增)
class TrafficStats(Base):
    __tablename__ = "traffic_stats"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)
    # 统计类型: 'hit' (有效点击), 'bot' (拦截爬虫)
    stat_type = Column(String, index=True) 
    count = Column(Integer, default=1) # 存储汇总后的计数
    timestamp = Column(DateTime, default=datetime.utcnow)