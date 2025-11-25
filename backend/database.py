# database.py - 添加域名状态检查相关表

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
    
    # 【修复】确保 NS 状态相关字段有正确默认值
    ns_status = Column(String, default="unknown")  # unknown, pending, active, failed
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

# 【新增】5. 域名状态检查日志表
class DomainStatusLog(Base):
    __tablename__ = "domain_status_logs"
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("entry_domains.id"))
    check_type = Column(String)  # ns_check, health_check
    status = Column(String)      # pending, active, failed, ok, banned
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联域名
    domain = relationship("EntryDomain")

def init_db():
    Base.metadata.create_all(bind=engine)