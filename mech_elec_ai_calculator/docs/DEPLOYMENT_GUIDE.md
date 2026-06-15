# 落地注意事项

## 目录

1. [环境准备](#1-环境准备)
2. [部署配置](#2-部署配置)
3. [运维监控](#3-运维监控)
4. [安全加固](#4-安全加固)
5. [性能优化](#5-性能优化)
6. [故障处理](#6-故障处理)

---

## 1. 环境准备

### 1.1 系统要求

```yaml
# 系统要求配置

system:
  operating_system:
    - Ubuntu 20.04 LTS
    - CentOS 7+
    - Debian 11+
  
  python:
    version: "3.10+"
    required_packages:
      - pydantic>=2.0
      - ezdxf>=1.0
      - PyMuPDF>=1.23
  
  hardware:
    minimum:
      cpu: "2 cores"
      memory: "4 GB"
      disk: "50 GB"
    
    recommended:
      cpu: "4 cores"
      memory: "8 GB"
      disk: "200 GB"
      ssd: true
  
  network:
    bandwidth: "10 Mbps"
    latency: "< 100 ms"
```

### 1.2 依赖服务

```yaml
# 依赖服务配置

services:
  database:
    type: "PostgreSQL 14+"
    host: "localhost"
    port: 5432
    database: "mech_elec_ai"
    
  cache:
    type: "Redis 6+"
    host: "localhost"
    port: 6379
    max_memory: "1GB"
  
  storage:
    type: "Local/S3/MinIO"
    path: "/data/mech_elec_ai"
    
  queue:
    type: "RabbitMQ/Redis"
    host: "localhost"
    port: 5672
```

### 1.3 环境变量

```bash
# 环境变量配置示例 (.env)

# 应用配置
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/mech_elec_ai
DATABASE_POOL_SIZE=20

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# 存储配置
STORAGE_TYPE=local
STORAGE_PATH=/data/mech_elec_ai
# STORAGE_TYPE=s3
# S3_ENDPOINT=http://localhost:9000
# S3_BUCKET=mech-elec-ai
# S3_ACCESS_KEY=
# S3_SECRET_KEY=

# API配置
OPENHUMAN_API_URL=https://api.openhuman.ai/v1
OPENHUMAN_API_KEY=
OPENHUMAN_TIMEOUT=120

# 安全配置
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_EXPIRY=3600

# 监控配置
METRICS_ENABLED=true
METRICS_PORT=9090
```

---

## 2. 部署配置

### 2.1 配置文件

```yaml
# config/production.yaml

app:
  name: "机电AI自动算量系统"
  version: "1.0.0"
  environment: "production"
  debug: false

storage:
  data_path: "/data/mech_elec_ai/data"
  output_path: "/data/mech_elec_ai/outputs"
  log_path: "/var/log/mech_elec_ai"
  cache_path: "/data/mech_elec_ai/cache"
  
  cleanup:
    enabled: true
    max_age_days: 30
    max_size_gb: 100

logging:
  level: "INFO"
  format: "json"
  rotation:
    max_size: "100MB"
    backup_count: 30
  handlers:
    - type: "file"
      path: "/var/log/mech_elec_ai/app.log"
    - type: "syslog"
      host: "localhost"
      port: 514

performance:
  workers: 4
  max_upload_size: "100MB"
  task_timeout: 600
  cache_ttl: 3600

security:
  cors:
    enabled: true
    allowed_origins:
      - "https://example.com"
  rate_limit:
    enabled: true
    requests_per_minute: 100
```

### 2.2 Docker部署

```dockerfile
# Dockerfile

FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /data/mech_elec_ai/{data,outputs,cache} \
    /var/log/mech_elec_ai

# 设置权限
RUN chown -R python:python /app /data /var/log/mech_elec_ai

# 切换到非root用户
USER python

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "600", "main:app"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  app:
    build: .
    container_name: mech-elec-ai
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data/mech_elec_ai
      - ./logs:/var/log/mech_elec_ai
      - /etc/localtime:/etc/localtime:ro
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/mech_elec_ai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - mech-elec-network

  db:
    image: postgres:14-alpine
    container_name: mech-elec-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mech_elec_ai
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - mech-elec-network

  redis:
    image: redis:6-alpine
    container_name: mech-elec-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - mech-elec-network

volumes:
  postgres_data:
  redis_data:

networks:
  mech-elec-network:
    driver: bridge
```

### 2.3 系统服务配置

```ini
# /etc/systemd/system/mech-elec-ai.service

[Unit]
Description=MechElec AI Calculator Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=mech_elec_ai
Group=mech_elec_ai
WorkingDirectory=/opt/mech_elec_ai
Environment="PATH=/opt/mech_elec_ai/venv/bin"
EnvironmentFile=/opt/mech_elec_ai/.env
ExecStart=/opt/mech_elec_ai/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 4 --timeout 600 main:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 3. 运维监控

### 3.1 日志配置

```python
# logging_config.py

import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
import json

class JSONFormatter(logging.Formatter):
    """JSON格式日志Formatter"""
    
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(config: dict):
    """配置日志系统"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # JSON格式文件处理器
    json_handler = RotatingFileHandler(
        config['log_path'] + '/app.json',
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=30
    )
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    # Syslog处理器
    syslog_handler = SysLogHandler(
        address=(config['syslog_host'], config['syslog_port'])
    )
    syslog_handler.setFormatter(logging.Formatter(
        'mech_elec_ai[%(process)d]: %(message)s'
    ))
    logger.addHandler(syslog_handler)
    
    return logger
```

### 3.2 监控指标

```python
# metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# 任务指标
task_total = Counter(
    'mech_elec_ai_tasks_total',
    'Total number of tasks',
    ['status']
)

task_duration = Histogram(
    'mech_elec_ai_task_duration_seconds',
    'Task duration in seconds',
    ['task_type']
)

# 步骤指标
step_duration = Histogram(
    'mech_elec_ai_step_duration_seconds',
    'Step duration in seconds',
    ['step_name']
)

# 资源指标
memory_usage = Gauge(
    'mech_elec_ai_memory_usage_bytes',
    'Memory usage in bytes'
)

cpu_usage = Gauge(
    'mech_elec_ai_cpu_usage_percent',
    'CPU usage percentage'
)

# 文件处理指标
file_size = Histogram(
    'mech_elec_ai_file_size_bytes',
    'Input file size in bytes',
    ['file_type']
)


def track_task(task_type: str):
    """任务执行装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                task_total.labels(status='success').inc()
                return result
            except Exception as e:
                task_total.labels(status='failed').inc()
                raise
            finally:
                duration = time.time() - start_time
                task_duration.labels(task_type=task_type).observe(duration)
        return wrapper
    return decorator
```

### 3.3 健康检查

```python
# health_check.py

from fastapi import FastAPI
from pydantic import BaseModel
import psutil
import time

app = FastAPI()

class HealthStatus(BaseModel):
    status: str
    timestamp: float
    services: dict
    resources: dict

@app.get("/health")
async def health_check():
    """健康检查接口"""
    services = {
        'database': check_database(),
        'redis': check_redis(),
        'storage': check_storage()
    }
    
    resources = {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    }
    
    all_healthy = all(s['healthy'] for s in services.values())
    
    return HealthStatus(
        status='healthy' if all_healthy else 'unhealthy',
        timestamp=time.time(),
        services=services,
        resources=resources
    )

def check_database() -> dict:
    """检查数据库连接"""
    try:
        # 执行简单查询
        return {'healthy': True, 'latency_ms': 0}
    except Exception as e:
        return {'healthy': False, 'error': str(e)}

def check_redis() -> dict:
    """检查Redis连接"""
    try:
        # 执行ping
        return {'healthy': True, 'latency_ms': 0}
    except Exception as e:
        return {'healthy': False, 'error': str(e)}

def check_storage() -> dict:
    """检查存储"""
    try:
        import os
        path = '/data/mech_elec_ai'
        stat = os.statvfs(path)
        free_gb = stat.f_bavail * stat.f_frsize / (1024**3)
        return {'healthy': free_gb > 1, 'free_gb': free_gb}
    except Exception as e:
        return {'healthy': False, 'error': str(e)}
```

---

## 4. 安全加固

### 4.1 防火墙配置

```bash
# ufw防火墙配置

# 允许SSH
ufw allow 22/tcp

# 允许HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 允许应用端口
ufw allow 8080/tcp

# 允许数据库端口（仅内网）
ufw allow from 10.0.0.0/24 to any port 5432
ufw allow from 10.0.0.0/24 to any port 6379

# 启用防火墙
ufw enable
```

### 4.2 Nginx反向代理配置

```nginx
# /etc/nginx/sites-available/mech-elec-ai

upstream mech_elec_ai {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name mech-elec-ai.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mech-elec-ai.example.com;
    
    ssl_certificate /etc/ssl/certs/mech-elec-ai.crt;
    ssl_certificate_key /etc/ssl/private/mech-elec-ai.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://mech_elec_ai;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
    
    location /health {
        proxy_pass http://mech_elec_ai/health;
        access_log off;
    }
}
```

### 4.3 数据库安全

```sql
-- PostgreSQL安全配置

-- 创建专用用户
CREATE USER mech_elec_ai WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE mech_elec_ai TO mech_elec_ai;

-- 创建专用schema
CREATE SCHEMA mech_elec_ai AUTHORIZATION mech_elec_ai;

-- 限制连接数
ALTER USER mech_elec_ai CONNECTION LIMIT 20;

-- 加密连接
ALTER USER mech_elec_ai WITH SSL;
```

---

## 5. 性能优化

### 5.1 数据库优化

```sql
-- PostgreSQL优化配置

-- 共享缓冲区
ALTER SYSTEM SET shared_buffers = '2GB';

-- 工作内存
ALTER SYSTEM SET work_mem = '256MB';

-- 维护内存
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- 有效缓存
ALTER SYSTEM SET effective_cache_size = '6GB';

-- 并行查询
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;

-- 启用压缩
ALTER TABLE task_results SET (fillfactor = 90);
ALTER TABLE quantity_items SET (fillfactor = 90);

-- 创建索引
CREATE INDEX idx_task_status ON tasks(status);
CREATE INDEX idx_task_created ON tasks(created_at);
CREATE INDEX idx_drawing_filename ON drawings(filename);
```

### 5.2 缓存优化

```python
# cache_config.py

CACHE_CONFIG = {
    'default': {
        'ttl': 3600,
        'max_size': 1000
    },
    'rules': {
        'ttl': 86400,  # 24小时
        'max_size': 100
    },
    'drawings': {
        'ttl': 3600,
        'max_size': 500
    },
    'results': {
        'ttl': 7200,
        'max_size': 1000
    }
}

# Redis缓存配置
REDIS_CONFIG = {
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'max_connections': 50,
    'decode_responses': True
}
```

### 5.3 应用优化

```python
# application_optimization.py

# 使用连接池
from psycopg2 import pool

connection_pool = pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    database="mech_elec_ai",
    user="user",
    password="password",
    host="localhost"
)

# 异步处理
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def async_process_file(file_path: str):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        process_file,
        file_path
    )
    return result

# 批量处理
def batch_process(items: list, batch_size: int = 100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        process_batch(batch)
```

---

## 6. 故障处理

### 6.1 常见故障处理

```python
# troubleshooting.py

TROUBLESHOOTING_GUIDE = {
    'app_startup_failure': {
        'symptoms': ['应用无法启动', '端口被占用'],
        'causes': [
            '端口已被占用',
            '配置文件错误',
            '依赖服务未启动'
        ],
        'solutions': [
            '检查端口占用: lsof -i:8080',
            '检查配置文件语法',
            '启动依赖服务: systemctl start postgresql redis'
        ]
    },
    
    'database_connection_failure': {
        'symptoms': ['无法连接数据库', '连接超时'],
        'causes': [
            '数据库服务未启动',
            '连接参数错误',
            '连接数已满'
        ],
        'solutions': [
            '检查数据库状态: systemctl status postgresql',
            '验证连接参数',
            '增加连接数或清理空闲连接'
        ]
    },
    
    'memory_oom': {
        'symptoms': ['内存溢出', '进程被kill'],
        'causes': [
            '处理大文件',
            '内存泄漏',
            '并发过高'
        ],
        'solutions': [
            '限制文件大小',
            '增加内存或增加swap',
            '限制并发数'
        ]
    },
    
    'disk_full': {
        'symptoms': ['磁盘空间不足', '写入失败'],
        'causes': [
            '日志文件过多',
            '临时文件未清理',
            '输出文件过多'
        ],
        'solutions': [
            '清理日志: find /var/log -name "*.log" -mtime +7 -delete',
            '清理临时文件',
            '配置自动清理任务'
        ]
    }
}
```

### 6.2 备份恢复

```bash
#!/bin/bash
# backup.sh - 备份脚本

BACKUP_DIR="/backup/mech_elec_ai"
DATE=$(date +%Y%m%d)

# 创建备份目录
mkdir -p $BACKUP_DIR/$DATE

# 备份数据库
pg_dump -Fc mech_elec_ai > $BACKUP_DIR/$DATE/db_backup.dump

# 备份配置文件
cp -r /opt/mech_elec_ai/config $BACKUP_DIR/$DATE/

# 备份规则库
cp -r /opt/mech_elec_ai/rules $BACKUP_DIR/$DATE/

# 压缩备份
tar -czf $BACKUP_DIR/${DATE}.tar.gz $DATE/

# 清理临时目录
rm -rf $BACKUP_DIR/$DATE

# 保留最近30天备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

```bash
#!/bin/bash
# restore.sh - 恢复脚本

BACKUP_FILE=$1
RESTORE_DIR="/tmp/restore"

# 解压备份
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# 恢复数据库
pg_restore -C -d postgres $RESTORE_DIR/db_backup.dump

# 恢复配置文件
cp -r $RESTORE_DIR/config /opt/mech_elec_ai/

# 恢复规则库
cp -r $RESTORE_DIR/rules /opt/mech_elec_ai/

# 清理
rm -rf $RESTORE_DIR
```

### 6.3 灾难恢复计划

```markdown
# 灾难恢复计划 (DRP)

## RTO (Recovery Time Objective): 4小时
## RPO (Recovery Point Objective): 1小时

## 恢复步骤

### 1. 评估阶段 (15分钟)
- [ ] 确定故障范围
- [ ] 评估数据损失
- [ ] 确定恢复策略

### 2. 恢复阶段 (2小时)
- [ ] 启动备用服务器
- [ ] 恢复操作系统
- [ ] 恢复数据库
- [ ] 恢复应用服务

### 3. 验证阶段 (1小时)
- [ ] 验证数据完整性
- [ ] 测试核心功能
- [ ] 验证接口可用性

### 4. 切换阶段 (45分钟)
- [ ] 切换DNS/负载均衡
- [ ] 验证流量正常
- [ ] 监控系统稳定

## 联系人

- 技术负责人: [姓名] [电话]
- 运维负责人: [姓名] [电话]
- 供应商支持: [联系方式]
```

---

## 附录

### A. 部署检查清单

```markdown
## 部署前检查

### 环境
- [ ] 操作系统版本确认
- [ ] Python版本确认
- [ ] 磁盘空间充足 (>50GB)
- [ ] 网络连接正常

### 配置
- [ ] 配置文件语法正确
- [ ] 环境变量已设置
- [ ] 依赖服务已配置

### 安全
- [ ] 防火墙规则已配置
- [ ] SSL证书已配置
- [ ] 强密码已设置

### 监控
- [ ] 日志已配置
- [ ] 监控已启用
- [ ] 告警已设置

## 部署后检查

### 功能
- [ ] 应用启动成功
- [ ] 健康检查通过
- [ ] 任务执行正常

### 性能
- [ ] 响应时间正常
- [ ] 资源使用正常

### 安全
- [ ] HTTPS可用
- [ ] 认证正常工作
```

### B. 联系方式

```yaml
support:
  email: support@mecheleai.com
  phone: +86-xxx-xxxx-xxxx
  hours: "9:00 - 18:00 UTC+8"
  
emergency:
  phone: +86-xxx-xxxx-xxxx
  hours: "7x24"
```
