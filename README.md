
# 🎓 校园二手交易平台

> 一个面向高校学生的个人二手物品展示与交易平台。

基于 **Vue 3 + FastAPI + MySQL + Redis** 开发，实现了商品发布与审核、订单管理、实时聊天、举报处理、管理员后台、Redis 多级缓存、限流与防刷等功能。

---

## 📖 项目简介

本项目是一个完整的前后端分离校园二手交易平台，面向高校学生提供二手物品的信息展示与交易服务。

用户可以：

- 注册并登录账号
- 发布二手商品
- 上传多张商品图片
- 浏览、搜索商品
- 收藏感兴趣的商品
- 创建订单并进行线下面交
- 与交易对象实时聊天
- 举报违规商品或用户
- 查看个人商品和销售数据

管理员可以：

- 审核商品
- 管理用户
- 处理举报
- 管理公告
- 查看订单
- 管理管理员账号
- 查看平台数据概览

---

# ✨ 功能特性

## 👤 用户端

### 🔐 用户系统

- 邮箱验证码注册
- 学号格式校验
- JWT 登录认证
- 个人中心
- 修改个人信息
- 登录状态自动管理
- 登录失败次数限制
- IP + 邮箱组合防暴力破解

---

### 📦 商品系统

- 发布商品
- 多图片上传
- 商品编辑
- 商品删除
- 商品标记售出
- 商品分类
- 商品分页浏览
- 商品关键词搜索
- 商品详情
- 卖家公开主页
- 商品审核机制
- 修改商品后重新进入审核
- 商品发布地区展示

商品审核流程：

```text
发布商品
   │
   ▼
待审核
   │
   ├── 审核通过 ──► 正常展示
   │
   └── 审核驳回 ──► 用户修改
```

---

### ❤️ 收藏系统

- 收藏商品
- 取消收藏
- 查看收藏列表

---

### 🛒 订单系统

支持完整的二手交易流程：

```text
浏览商品
   │
   ▼
创建订单
   │
   ▼
联系卖家
   │
   ▼
约定面交
   │
   ▼
完成交易
   │
   ▼
确认收货
```

具体功能：

- 创建订单
- 取消订单
- 买家确认收货
- 卖家完成订单
- 设置面交时间
- 设置面交地点
- 双方确认面交安排
- 超时自动确认收货

---

### 💬 实时聊天

支持订单关联聊天。

技术实现：

- HTTP 历史消息
- WebSocket 实时通信
- 消息发送
- 消息已读
- WebSocket 心跳
- 聊天消息限流

WebSocket 协议：

```text
客户端连接
    │
    ▼
发送 JWT Token
    │
    ▼
身份验证
    │
    ▼
开始实时聊天
```

---

### 🚨 举报系统

支持举报：

- 用户
- 商品

管理员可以：

- 查看举报详情
- 处理举报
- 驳回举报
- 扣除信用分
- 封禁违规用户

---

### 📢 公告系统

支持：

- 查看公告
- 管理员发布公告
- 修改公告
- 删除公告

---

### 📊 数据统计

用户可以查看：

- 商品销售情况
- 销售统计数据
- 个人交易数据

---

### 🌙 主题系统

支持：

- 浅色模式
- 深色模式

---

# 🛠️ 管理员后台

访问：

```text
/admin
```

管理员后台包含以下功能。

## 👥 用户管理

- 查看用户
- 搜索用户
- 封禁用户
- 解封用户
- 查看用户状态
- 查看信用分

---

## 📦 商品审核

管理员可以：

- 查看待审核商品
- 审核通过
- 审核驳回
- 填写审核原因
- 强制下架商品

---

## 🛒 订单管理

管理员可以：

- 查看订单
- 查看订单详情
- 查看订单状态

---

## 🚨 举报管理

管理员可以：

- 查看举报
- 查看举报详情
- 处理举报
- 扣除用户信用分
- 封禁违规用户

---

## 📢 公告管理

支持：

- 创建公告
- 修改公告
- 删除公告
- 查看公告

---

## 👑 管理员账号管理

超级管理员可以：

- 创建管理员
- 查看管理员
- 修改管理员角色
- 修改管理员状态

---

# 🚀 技术栈

| 分类 | 技术 |
|---|---|
| 前端 | Vue 3 |
| 前端构建 | Vite |
| 状态管理 | Pinia |
| 前端路由 | Vue Router |
| HTTP 请求 | Axios |
| 后端 | FastAPI |
| ASGI Server | Uvicorn |
| ORM | SQLAlchemy 2.x |
| 数据库驱动 | aiomysql |
| 数据库 | MySQL |
| 缓存 | Redis |
| 本地缓存 | cachetools |
| 布隆过滤器 | pybloom-live |
| JWT | python-jose |
| 密码加密 | bcrypt / passlib |
| WebSocket | FastAPI WebSocket |
| HTTP 客户端 | httpx |
| 邮件 | SMTP |
| IP 地址库 | ip2region |
| 图片服务 | 独立 FastAPI 图片服务器 |
| Web 服务器 | Nginx |

---

# 🧠 Redis 设计

本项目不仅将 Redis 用作普通缓存，还实现了多种缓存保护和高并发处理方案。

## 商品详情缓存

访问流程：

```text
请求商品
   │
   ▼
布隆过滤器
   │
   ├── 不存在 ──► 直接返回
   │
   ▼
本地缓存
   │
   ├── 命中 ──► 返回
   │
   ▼
Redis
   │
   ├── 命中 ──► 返回
   │
   ▼
MySQL
```

### 已实现

- 布隆过滤器防止缓存穿透
- 空值缓存
- 本地缓存
- Redis 缓存
- MySQL 数据回源
- TTL 随机抖动防止缓存雪崩
- 分片锁
- 双重检查
- 热点数据预热

---

## 缓存雪崩

缓存 TTL 加入随机时间：

```text
基础 TTL + 随机时间
```

避免大量缓存同时失效。

---

## 缓存击穿

针对热点数据：

```text
请求
 │
 ▼
缓存失效
 │
 ▼
获取锁
 │
 ▼
再次检查缓存
 │
 ▼
查询数据库
 │
 ▼
重建缓存
```

---

## 缓存穿透

使用：

```text
布隆过滤器
+
空值缓存
```

拦截不存在的数据请求。

---

## 缓存版本号

商品列表等缓存使用版本号：

```text
product:cache:version
```

商品发生变化时：

```text
INCR
```

即可让旧缓存自然失效。

避免：

```text
SCAN
批量删除 Redis Key
```

带来的性能问题。

---

## 浏览量统计

商品浏览量不会每次访问都直接写入 MySQL。

流程：

```text
用户浏览
   │
   ▼
Redis Hash
   │
   ▼
后台任务
   │
   ▼
批量写入 MySQL
```

优点：

- 减少数据库写入
- 提高高并发性能
- 支持失败重试

同时：

- 同一用户短时间重复访问不重复计数
- 同一 IP 短时间重复访问不重复计数

---

# 🛡️ 限流与安全

## 接口限流

使用 Redis 实现限流。

包括：

- 公开接口 IP 限流
- 搜索接口限流
- 聊天消息限流
- 登录失败限制
- 邮箱验证码发送限制
- 商品发布频率限制

---

## 登录安全

登录失败记录：

```text
IP
+
邮箱哈希
```

达到限制后暂时锁定。

---

## Redis 隐私保护

Redis Key 中不会直接保存用户邮箱。

邮箱经过密钥哈希后使用：

```text
Redis Key
```

避免 Redis 数据中直接出现用户邮箱。

---

## JWT

需要认证的接口使用：

```http
Authorization: Bearer <token>
```

---

# 📁 项目结构

```text
Trading_Platform/
│
├── front_end/                         # Vue 3 前端
│   │
│   ├── src/
│   │   ├── api/                       # API 接口封装
│   │   ├── components/                # 通用组件
│   │   ├── views/                     # 页面
│   │   ├── stores/                    # Pinia 状态管理
│   │   └── router/                    # Vue Router
│   │
│   ├── vite.config.js                 # Vite 配置
│   └── package.json
│
└── back_end/
    │
    ├── main.py                        # FastAPI 应用入口
    ├── requirements.txt               # Python 依赖
    │
    ├── routers_1/                     # 用户端路由
    ├── crud_1/                        # 用户端业务逻辑
    ├── modles_1/                      # SQLAlchemy 数据模型
    ├── schemas_1/                     # Pydantic 数据模型
    │
    ├── tools_1/                       # 工具模块
    │   ├── JWT
    │   ├── 密码加密
    │   ├── Redis 缓存
    │   ├── 限流
    │   ├── 浏览量统计
    │   ├── IP 地址查询
    │   ├── WebSocket
    │   ├── 邮件
    │   └── 后台任务
    │
    ├── database_1/                    # MySQL / Redis 配置
    ├── ip_data/                       # IP 地址数据库
    ├── admin/                         # 管理员后台
    └── image_server/                  # 独立图片服务器
```

---

# ⚙️ 快速开始

## 1️⃣ 环境要求

建议：

```text
Python 3.12+
Node.js 18+
MySQL 8.x+
Redis 6.x+
```

---

# 🐍 后端启动

进入后端目录：

```bash
cd back_end
```

创建虚拟环境：

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

Linux / macOS：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

---

# 🗄️ 数据库初始化

首先创建数据库：

```sql
CREATE DATABASE hkz_market
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

然后执行项目中的数据库建表 SQL。

例如：

```text
Marketz_Table.sql
```

初始化商品分类：

```sql
INSERT INTO categories (`key`, name, sort_order) VALUES
('electronics', '数码电子', 1),
('books', '书籍教材', 2),
('daily', '生活用品', 3);
```

---

# 👑 创建第一个超级管理员

生成密码哈希：

```bash
python -c "from tools_1.password_hash import password_hash; print(password_hash('你的管理员密码'))"
```

然后插入数据库：

```sql
INSERT INTO admins (username, password_hash, role)
VALUES ('admin', '上一步生成的密码哈希', 'super_admin');
```

---

# 🔑 环境变量

创建：

```text
back_end/keys.env
```

示例：

```env
# =========================
# MySQL
# =========================

DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306
DATABASE_NAME=hkz_market
DATABASE_USER=root
DATABASE_PASSWORD=YOUR_PASSWORD


# =========================
# Redis
# =========================

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

REDIS_MAX_CONNECTIONS=50

# Redis Key 加密密钥
REDIS_KEY_SECRET=YOUR_RANDOM_SECRET


# =========================
# JWT
# =========================

SECRET_KEY=YOUR_JWT_SECRET
ALGORITHM=HS256


# =========================
# Email
# =========================

EMAIL_HOST=smtp.qq.com
EMAIL_PORT=465

EMAIL_ADDRESS=YOUR_EMAIL@qq.com
EMAIL_AUTH_CODE=YOUR_SMTP_AUTH_CODE
```

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

# ▶️ 启动项目

需要启动两个服务。

## 图片服务器

```bash
python image_server/main.py
```

默认：

```text
http://0.0.0.0:8001
```

---

## FastAPI 后端

```bash
python main.py
```

默认：

```text
http://0.0.0.0:8000
```

接口文档：

```text
http://localhost:8000/docs
```

管理员后台：

```text
http://localhost:8000/admin
```

---

# 🎨 前端启动

进入：

```bash
cd front_end
```

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

默认：

```text
http://localhost:5173
```

生产构建：

```bash
npm run build
```

构建结果：

```text
front_end/dist
```

---

# 🌐 API 接口概览

完整接口文档请运行项目后访问：

```text
http://localhost:8000/docs
```

---

## 🔐 认证

| 方法 | 地址 | 功能 |
|---|---|---|
| POST | `/api/auth/send-code` | 发送验证码 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 当前用户信息 |

---

## 📦 商品

| 方法 | 地址 | 功能 |
|---|---|---|
| GET | `/api/products` | 商品列表 |
| GET | `/api/products/search` | 搜索商品 |
| GET | `/api/products/categories` | 商品分类 |
| GET | `/api/products/{id}` | 商品详情 |
| POST | `/api/products` | 发布商品 |
| PATCH | `/api/products/{id}` | 修改商品 |
| PATCH | `/api/products/{id}/sold` | 标记售出 |
| DELETE | `/api/products/{id}` | 删除商品 |

---

## ❤️ 收藏

| 方法 | 地址 | 功能 |
|---|---|---|
| GET | `/api/favorite` | 收藏列表 |
| POST | `/api/favorite` | 收藏商品 |
| DELETE | `/api/favorite/{id}` | 取消收藏 |

---

## 🛒 订单

| 方法 | 地址 | 功能 |
|---|---|---|
| POST | `/api/orders` | 创建订单 |
| GET | `/api/orders/my` | 我的订单 |
| GET | `/api/sales/my` | 我的销售 |
| PATCH | `/api/orders/{id}/cancel` | 取消订单 |
| PATCH | `/api/orders/{id}/receive` | 确认收货 |
| PATCH | `/api/orders/{id}/complete` | 完成订单 |

---

## 💬 聊天

| 方法 | 地址 | 功能 |
|---|---|---|
| POST | `/api/chat/conversations` | 创建会话 |
| GET | `/api/chat/conversations` | 获取会话 |
| GET | `/api/chat/conversations/{id}/messages` | 获取历史消息 |
| POST | `/api/chat/conversations/{id}/messages` | 发送消息 |
| WebSocket | `/api/chat/ws/{id}` | 实时聊天 |

---

# 🚀 生产环境部署

推荐架构：

```text
                    Internet
                        │
                        ▼
                     Nginx
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
      Vue            FastAPI       Image Server
                                     
                        │
                ┌───────┴───────┐
                │               │
                ▼               ▼
              MySQL           Redis
```

推荐：

```text
Nginx
├── 前端静态文件
├── /api/
├── /admin/
└── /images/
```

其中：

- `/api/` 转发 FastAPI
- `/admin/` 转发 FastAPI 管理后台
- `/images/` 转发图片服务器
- WebSocket 需要配置 Upgrade 请求头

---

# ⚠️ 安全建议

生产环境请注意：

- 不要提交 `keys.env`
- 不要将数据库密码上传 GitHub
- 使用强随机 JWT Secret
- Redis 设置密码
- 图片服务器端口不要直接暴露公网
- 使用 HTTPS
- 管理员使用强密码
- 日志文件不要公开
- 不要将 `node_modules` 提交到 GitHub

建议 `.gitignore`：

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/

# Environment
.env
*.env
keys.env

# Node
node_modules/
dist/

# Logs
*.log
Log/

# IDE
.idea/
.vscode/

# OS
.DS_Store
Thumbs.db
```

---

# 🗺️ 后续计划

- [ ] 商品评价系统
- [ ] 用户信用等级系统
- [ ] 未读消息提醒
- [ ] 站内通知系统
- [ ] 最近浏览记录
- [ ] 商品推荐系统
- [ ] 图片缩略图与压缩
- [ ] 操作审计日志
- [ ] Alembic 数据库迁移
- [ ] Docker / Docker Compose 一键部署
- [ ] 自动化测试
- [ ] CI/CD
- [ ] 多实例部署支持
- [ ] Redis Pub/Sub WebSocket 广播

---

# 📸 项目展示

项目演示地址：

[点击查看项目演示](https://chuhlblog.top?utm_source=chatgpt.com)

> 如演示站点暂时无法访问，可能是服务器维护或项目已停止部署。

---

# 🙏 致谢

感谢以下开源项目：

- Vue
- FastAPI
- SQLAlchemy
- Redis
- MySQL
- Vite
- ip2region

---

# 👨‍💻 作者

**Honglin Chu**

GitHub：

[chuhonglin2006](https://github.com/chuhonglin2006?utm_source=chatgpt.com)

项目地址：

[Trading_Platform](https://github.com/chuhonglin2006/Trading_Platform?utm_source=chatgpt.com)

---

## ⭐ Star

如果这个项目对你有帮助，欢迎 Star ⭐ 支持一下！

```text
⭐ Star
🍴 Fork
🐛 Issue
💡 Pull Request
```
