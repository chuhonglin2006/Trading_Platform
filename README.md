# Trading_Platform

一个基于 FastAPI 和 Vue 3 开发的校园二手物品交易与信息展示平台。

本项目主要面向校园用户，提供用户注册登录、商品发布、商品浏览与搜索、商品收藏、订单交易、在线聊天、评价、举报管理以及后台管理等功能。

项目采用前后端分离架构，后端使用 FastAPI 提供 RESTful API，前端使用 Vue 3 构建用户界面，并使用 MySQL 进行数据持久化、Redis 提供缓存和部分高并发场景优化。

[成品展示](https://chuhlblog.top) 

![Python](https://img.shields.io/badge/Python-3.14%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![MySQL](https://img.shields.io/badge/MySQL-8.x-4479A1)
![Redis](https://img.shields.io/badge/Redis-cache%20%26%20rate%20limit-DC382D)

---

# 项目介绍

随着校园二手物品交易需求不断增加，学生之间经常存在教材、数码产品、生活用品、服装配饰等闲置物品的交易需求。

Trading_Platform 提供一个校园二手物品展示与交易平台，功能有:

- 注册并登录平台
- 浏览其他用户发布的商品
- 搜索商品
- 查看商品详情
- 发布个人闲置物品
- 上传商品图片
- 收藏感兴趣的商品
- 创建交易订单
- 与交易对象进行在线聊天
- 修改交易时间和地点
- 确认收货和完成交易
- 举报违规用户或商品
- 完成交易后对卖家进行评价
- 信用分系统
- 下载Windows和Android App

管理员可以通过后台管理系统：

- 管理用户
- 管理商品
- 审核商品
- 管理订单
- 处理举报
- 发布公告
- 超级管理员查看日志
- 超级管理员查看服务器详情
- 超级管理员创建管理员账号

项目在部分接口中加入了 Redis 缓存、分布式锁、数据库行锁、接口限流等机制，以提高系统性能并减少部分高并发场景下的数据问题。

---

# 项目特点

## 前后端分离

前端和后端独立开发，通过 HTTP API 进行通信。

```text
Vue 3 Frontend
        │
        │ HTTP / HTTPS
        ▼
FastAPI Backend
        │
        ├──────── MySQL
        │
        ├──────── Redis
```

---

## 用户认证

系统使用 JWT 进行用户身份认证。

用户登录成功后，后端返回访问 Token，前端保存 Token，并在后续请求中自动携带：Authorization: Bearer <token>

后端通过 JWT 验证用户身份。

---

## Redis 缓存

项目使用 Redis 对部分热点数据进行缓存，例如：

- 商品列表
- 商品详情
- 热门商品
- 搜索结果
- 验证码
- 接口限流
- 分布式锁

通过 Redis 可以减少数据库压力，提高接口响应速度。

---

## 商品审核机制

用户发布商品后，商品默认不会直接展示给所有用户。

商品可以具有不同审核状态：

pending、approved、rejected

管理员审核通过后，商品才能正常展示。

---

## 并发控制

项目针对部分高并发场景进行了处理。

部分操作使用 Redis 分布式锁，减少重复提交的可能性。

---

## 图片上传

商品支持上传多张图片。

支持的图片格式包括：

jpg、jpeg、png、webp

系统会对上传文件进行：

- 文件大小限制
- 文件格式检查
- 文件头检查
- 文件数量限制

---

# 功能列表

## 普通用户功能

### 用户系统

用户注册、邮箱验证码、用户登录、JWT 身份认证、获取当前用户信息、退出登录、登录状态管理

---

### 商品系统

浏览商品、商品分页、商品详情、商品搜索、商品分类、发布商品、编辑商品、删除商品、上架商品、下架商品、商品图片上传、商品浏览次数统计

---

### 商品分类

系统支持多个商品分类，例如：
教材书籍、数码电子、服装配饰、生活日用、运动户外、家具家电、其他

---

### 收藏功能

用户可以：
收藏商品、取消收藏、查看收藏列表

---

### 订单系统

用户可以：
创建订单、查看购买订单、查看出售订单、修改交易信息、取消订单、确认交易、确认收货、完成订单
订单状态根据实际业务流程进行管理

---

### 在线聊天

交易双方可以在订单对应的聊天会话中进行交流。

聊天功能主要用于：
沟通交易细节、确认交易地点、确认交易时间、交流商品相关问题
聊天记录与交易订单关联

---

### 举报功能

用户可以举报：
用户、商品
举报提交后由管理员进行审核处理

---

# 管理员功能

系统提供独立的管理员后台

管理员可以进行以下操作

## 用户管理

查看用户列表、查看用户信息、修改用户状态、禁用用户、恢复用户、管理用户信用分

---

## 商品管理

查看商品、审核商品、通过商品审核、拒绝商品审核、查看商品详情、管理违规商品

---

## 订单管理

查看订单、查看订单状态、查看交易信息、管理异常订单

---

## 举报管理

查看举报列表、查看举报详情、处理举报、拒绝举报、对违规用户进行处理、对违规商品进行处理

---

## 公告管理

管理员可以发布和管理系统公告。

---

## 超级管理员

超级管理员可以查看服务器信息、查看日志、管理其他管理员账号

---

# 技术栈

## 后端

| 技术            | 用途          |
| ------------- | ----------- |
| Python        | 后端开发语言      |
| FastAPI       | Web 框架      |
| Uvicorn       | ASGI 服务器    |
| SQLAlchemy    | ORM 框架      |
| MySQL         | 关系型数据库      |
| Redis         | 缓存和分布式锁     |
| JWT           | 用户身份认证      |
| Pydantic      | 数据验证        |
| aiomysql      | MySQL 异步驱动  |
| redis.asyncio | Redis 异步客户端 |

---

## 前端

| 技术         | 用途      |
| ---------- | ------- |
| Vue 3      | 前端框架    |
| Vite       | 前端构建工具  |
| Vue Router | 前端路由    |
| Pinia      | 状态管理    |
| Axios      | HTTP 请求 |
| JavaScript | 前端开发语言  |

---

## 部署


推荐部署结构：

```text
Internet
    │
    ▼
Nginx
    │
    ├──────── Frontend Static Files
    │
    └──────── Reverse Proxy
                │
                ▼
              FastAPI
                │
        ┌───────┴────────┐
        ▼                ▼
      MySQL            Redis
```

---

# 项目结构

项目整体结构如下：

```text
Trading_Platform/
│
├── back_end/                 后端项目
│   │
│   ├── main.py               FastAPI 入口
│   │
│   ├── routers/              API 路由
│   │   ├── auth.py           用户认证
│   │   ├── products.py       商品相关接口
│   │   ├── orders.py         订单相关接口
│   │   ├── chat.py           聊天相关接口
│   │   ├── reports.py        举报相关接口
│   │   └── admin.py          管理员接口
│   │
│   ├── models/               数据库模型
│   │
│   ├── schemas/              Pydantic 数据模型
│   │
│   ├── tools/                工具函数
│   │
│   ├── static/               静态资源
│   │
│   ├── requirements.txt      Python 依赖
│   │
│   └── keys.env.example      环境变量示例
│
├── front_end/                前端项目(Android为构建Apk使用,Web和Win为网页端和exe使用)
│   │
│   ├── src/
│   │   ├── views/            页面
│   │   ├── components/       Vue 组件
│   │   ├── stores/           Pinia 状态管理
│   │   ├── router/           前端路由
│   │   └── utils/            工具函数
│   │
│   ├── package.json
│   └── vite.config.js
│
├── README.md
│
└── .gitignore
```

具体目录结构可能会随着项目版本更新而有所变化。

---

# 环境要求

推荐开发环境：

```text
Python 3.10+
Node.js 18+
MySQL 8.0+
Redis 6.0+
```

---

# Nginx 配置示例

下面是一个基本的 Nginx 配置示例。

```nginx
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    map $http_upgrade $connection_upgrade {
        default upgrade;
        ''      close;
    }

    server {
        listen 80;
        server_name localhost;

        client_max_body_size 100m;

        # FastAPI API
        location /api/ {
            proxy_pass http://127.0.0.1:8000;

            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 商品图片
        location /images/ {
            proxy_pass http://127.0.0.1:8000;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # 下载文件
        location /downloads/ {
            proxy_pass http://127.0.0.1:8000;

            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # 管理后台
        location /admin {
            proxy_pass http://127.0.0.1:8000;

            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # Vue 静态资源
        location ^~ /assets/ {
            root E:/PyProject/FastAPI/Trading_Platform/front_end_Web/dist;
            try_files $uri =404;
        }

        # Vue 前端
        location / {
            root E:/PyProject/FastAPI/Trading_Platform/front_end_Web/dist;
            index index.html;

            try_files $uri $uri/ /index.html;
        }
    }
}
```

实际部署时需要根据：

- 域名
- 前端路径
- FastAPI 端口
- 图片服务器
- SSL 证书

进行调整。

---

# HTTPS 配置

生产环境推荐使用 HTTPS。

Nginx 配置 SSL 后，用户访问：

```text
https://your-domain.com
```

API 也应该通过：

```text
https://your-domain.com/api/
```

进行访问。

不要让前端直接暴露：

```text
http://服务器IP:8000
```

---

# API 文档

FastAPI 提供自动 API 文档。

启动后端后访问：

```text
/api/docs
```

或者：

```text
/docs
```

具体地址取决于项目的 Nginx 代理配置。

Swagger UI 可以用于：

- 查看接口
- 查看请求参数
- 测试 API
- 查看返回数据

---

# 缓存机制

项目部分接口使用 Redis 缓存。

例如商品详情缓存可能使用：

```text
product:detail:{product_id}
```

包括：

```text
读取缓存
写入缓存
删除缓存
缓存预热
```

---


## JWT 密钥

不要使用简单的：

```text
123456
secret
test
```

作为 JWT 密钥。

应该使用足够长的随机字符串。

---

## 数据库密码

不要把数据库密码直接写入：

```python
main.py
config.py
database.py
```

应该使用环境变量。

---

## Redis 密码

Redis 如果暴露在公网环境中，必须：

- 设置密码
- 限制监听地址
- 配置防火墙
- 不直接暴露 6379 端口

---

## FastAPI

生产环境不建议：

```text
--reload
```

也不建议直接将 Uvicorn 的开发端口暴露到公网。

推荐：

```text
Internet
    │
    ▼
Nginx
    │
    ▼
Uvicorn / FastAPI
```

---


# 后续准备继续优化的方向

## 接口测试

对接口进行自动化测试。

重点测试：

- 用户注册
- 用户登录
- 商品发布
- 商品购买
- 订单取消
- 聊天创建
- 举报提交

---

---

## 缓存优化

- 缓存预热
- 缓存穿透保护
- 缓存击穿保护
- 缓存雪崩保护
- 本地缓存
- Redis 分布式锁

---

## 图片处理

- 自动生成缩略图
- 图片压缩
- WebP 转换
- 图片尺寸限制
- 图片内容审核
- CDN 加速

---

## 搜索功能

- 商品名称搜索
- 分类搜索
- 校区筛选
- 价格区间
- 排序
- 热门搜索

未来可以考虑接入专业搜索服务。

---

# 常见问题

## 访问 `/` 返回 404

FastAPI 后端主要提供 API 服务。

如果访问：

```text
http://127.0.0.1:8000/
```

返回：

```text
404
```

不一定代表项目启动失败。

可以访问：

```text
http://127.0.0.1:8000/docs
```

查看 API 文档。

---

## 图片无法显示

需要检查：

- 图片服务器是否启动
- Nginx 是否正确代理图片请求
- 图片 URL 是否正确
- 图片文件是否存在
- 浏览器是否存在跨域问题

---

## 手机登录后获取到 `127.0.0.1`

如果 FastAPI 位于 Nginx 反向代理之后，后端直接获取：

```python
request.client.host
```

可能得到：

```text
127.0.0.1
```

应该正确配置 Nginx：

```nginx
proxy_set_header X-Real-IP $remote_addr;

proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

并在 FastAPI/Uvicorn 中正确配置可信代理。

---

## Redis 无法连接

检查 Redis：

```bash
redis-cli ping
```

正常应该返回：

```text
PONG
```

然后检查：

- Redis 是否启动
- Redis 端口
- Redis 密码
- 防火墙
- Redis 配置文件

---


# 许可证

本项目仅用于学习、开发和技术研究。

如需用于生产环境，请根据实际业务需求进一步完善：

- 安全机制
- 权限控制
- 数据备份
- 日志系统
- 接口测试
- 并发测试
- 监控告警
- 数据库优化

---

# 作者

GitHub：

https://github.com/chuhonglin2006

项目仓库：

https://github.com/chuhonglin2006/Trading_Platform

---

# 总结

Trading_Platform 是一个基于 FastAPI、Vue 3、MySQL 和 Redis 开发的前后端分离校园二手交易平台。

项目包含：

```text
用户系统
商品系统
分类系统
收藏系统
订单系统
评价系统
在线聊天
举报系统
商品审核
管理员后台
Redis 缓存
JWT 身份认证
图片上传
并发控制
```

该项目适合作为 FastAPI、Vue 3、SQLAlchemy、Redis 和前后端分离开发的综合学习项目。

后续可以继续完善自动化测试、缓存优化、图片处理、搜索功能、系统监控和生产环境部署能力。
