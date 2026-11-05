# 校园二手交易平台

面向高校学生的二手交易平台：**Vue 3 前端 + FastAPI 后端 + MySQL + Redis**，包含商品发布与审核、订单与面交、实时聊天、举报处理、管理员后台和独立的图片服务器。
展示界面: (chuhlblog.top) (这个域名以前拿来做个人博客的)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![MySQL](https://img.shields.io/badge/MySQL-8.x-4479A1)
![Redis](https://img.shields.io/badge/Redis-cache%20%26%20rate%20limit-DC382D)

## 功能

**用户端（`front_end`）**

- 邮箱验证码注册（校验学号）、登录、个人中心
- 商品发布（多图上传）、修改、标记售出、删除；修改后重新进入审核
- 商品浏览：分类、分页列表、关键词搜索、详情、卖家主页；商品显示发布地（按发布者 IP 解析省份）
- 收藏 / 取消收藏
- 订单：下单、取消、确认收货、卖家完成、约定面交时间地点并双方确认、7 天未确认自动收货
- 订单聊天：HTTP + WebSocket 实时消息、已读回执
- 举报用户 / 商品、公告、销售统计图表、深色 / 浅色主题

**管理端（后端内置页面，访问 `/admin`）**

- 管理员登录；超级管理员可管理管理员账号与角色
- 用户管理：查看、封禁 / 解封
- 商品审核：通过 / 驳回、强制下架
- 订单查看、举报处理（扣信用分 / 封禁）、公告增删改、数据概览

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vite、Pinia、Vue Router、Axios |
| 后端 | FastAPI、Uvicorn、SQLAlchemy 2.x（异步）、aiomysql |
| 数据库 | MySQL |
| 缓存 / 限流 | Redis（redis-py asyncio）、cachetools、pybloom-live |
| 鉴权 | JWT（python-jose）、bcrypt（passlib） |
| IP 归属地 | py-ip2region（离线库 `ip2region_v4.xdb`） |
| 邮件 | SMTP（默认 QQ 邮箱） |
| 图片 | 独立 FastAPI 图片服务器，后端通过 httpx 上传 |

## Redis 设计

**读缓存（多级）**

- 商品详情：布隆过滤器 → 进程内本地缓存 → Redis → MySQL
  - 布隆过滤器拦截不存在的商品 ID（防穿透），不存在的商品额外缓存空值
  - 非公开商品（审核中 / 已下架 / 已售出）写入状态标记，游客请求直接返回 404，不再查库
  - TTL 带随机抖动（防雪崩），分片锁 + 双重检查（防击穿）
  - 启动时预热浏览量最高的一批商品
- 商品列表、搜索结果、他人商品、我的商品、分类、公告：本地缓存 + Redis 两级
- **版本号失效**：列表 / 搜索 / 他人商品的缓存 key 带全局版本号（`product:cache:version`），商品变更时 `INCR` 一次即可让旧缓存整体失效，不需要 `SCAN` 删 key；我的商品列表使用按用户的版本号

**写后失效**

- 下单 / 取消 / 完成订单、商品修改 / 售出 / 删除、管理员审核 / 强制下架，在 **MySQL 提交成功之后** 清理详情缓存并递增版本号
- 封禁用户、扣信用分后清理用户缓存；公告增删改后清理公告缓存

**限流与防刷**

- 通用限流用 Redis 事务（`SET NX EX` + `INCR` + `TTL`）原子执行，避免 key 丢失过期时间
- 公开接口按 IP 限流；搜索按用户 / IP 限流；聊天消息按用户限流（HTTP 与 WebSocket 共用计数）
- 登录失败按「IP + 邮箱哈希」计数，达到上限后锁定一段时间
- 发送验证码按邮箱和 IP 限制频率；验证码校验有错误次数上限
- 发布商品：每小时数量限制 + 带随机令牌的防重复提交锁

**计数与其他**

- 商品浏览量先累加到 Redis Hash，再由后台任务每分钟 `RENAME` 后批量回写 MySQL；回写失败时保留临时 key，下一轮重试
- 同一用户 / IP 10 分钟内重复浏览不重复计数
- IP 归属省份查询结果缓存 7 天
- Redis 中的邮箱一律使用带密钥的哈希（`REDIS_KEY_SECRET`），不出现明文
- Redis 异常时读路径降级为直接查 MySQL，限流放行（可用性优先）

## 项目结构

```text
Trading_Platform/
├── front_end/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # 接口封装（axios，baseURL 为 /api）
│   │   ├── views/               # 页面：首页、详情、发布、聊天、订单、个人中心 ...
│   │   ├── components/          # 通用组件
│   │   ├── stores/              # Pinia 状态
│   │   └── router/
│   ├── vite.config.js           # 开发代理：/api → 8000，/images → 8001
│   └── package.json
└── back_end/
    ├── main.py                  # 应用入口：路由、CORS、请求日志、管理端静态页与图片挂载
    ├── keys.env                 # 环境变量
    ├── requirements.txt
    ├── routers_1/               # 用户端路由
    ├── crud_1/                  # 用户端业务逻辑
    ├── modles_1/                # 数据库模型（SQLAlchemy）
    ├── schemas_1/               # 请求 / 响应模型（Pydantic）
    ├── tools_1/                 # 工具：JWT、密码哈希、限流、缓存预热与版本号、浏览量回写、
    │                            #       IP 归属地、日志、WebSocket 管理、邮件、后台定时任务 ...
    ├── database_1/              # MySQL / Redis 连接配置
    ├── ip_data/                 # ip2region 离线 IP 库
    ├── Log/                     # 运行日志（Python / Redis / MySQL / Image，按大小轮转）
    ├── admin/                   # 管理端：路由、业务逻辑、模型、静态页面
    └── image_server/            # 独立图片服务器（默认 8001 端口）
```

## 快速开始

### 1. 环境要求

- Python 3.12 及以上
- Node.js 18 及以上
- MySQL 8.x、Redis 6.x 及以上

### 2. 后端

```bash
cd back_end
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

cp keys.env.example keys.env      # 然后编辑 keys.env，见下方「环境变量」
```

**初始化数据库**

先创建空库（库名与 `DATABASE_NAME` 一致，字符集建议 `utf8mb4`）。

> 仓库**暂未提供建表 SQL 或迁移脚本**，表结构以 `modles_1/` 和 `admin/modles_a/` 中的模型为准，共 11 张表：
> `users`、`products`、`product_images`、`categories`、`favorites`、`orders`、
> `chat_conversations`、`chat_messages`、`reports`、`announcements`、`admins`。
>
> 另外，后端启动时会检查 `products.publish_province` 列，缺失则自动 `ALTER TABLE` 补上，
> 所以 MySQL 账号需要有 `ALTER` 权限。

建表后需要两份初始数据：

```sql
-- 商品分类（示例，按需调整；没有分类时无法发布商品）
INSERT INTO categories (`key`, name, sort_order) VALUES
  ('electronics', '数码电子', 1),
  ('books',       '书籍教材', 2),
  ('daily',       '生活用品', 3);
```

```bash
# 首个超级管理员：创建管理员的接口本身要求超级管理员权限，所以第一个账号需要手动插入
python -c "from tools_1.password_hash import password_hash; print(password_hash('你的管理员密码'))"
```

```sql
INSERT INTO admins (username, password_hash, role)
VALUES ('admin', '上一步输出的哈希', 'super_admin');
```

**启动**（两个终端）：

```bash
python image_server/main.py     # 图片服务器，默认 0.0.0.0:8001
python main.py                  # 后端，默认 0.0.0.0:8000
```

- 接口文档：<http://localhost:8000/docs>
- 管理端：<http://localhost:8000/admin>

> 后端通过 `http://127.0.0.1:8001` 访问图片服务器上传 / 删除图片，因此两者需部署在同一台机器上，
> 图片服务器的 8001 端口**不要对公网开放**。

### 3. 前端

```bash
cd front_end
npm install
npm run dev          # 开发：http://localhost:5173，自动代理 /api 和 /images
npm run build        # 生产构建，产物在 dist/
```

开发模式下 `vite.config.js` 会把 `/api`（含 WebSocket）转发到 `127.0.0.1:8000`，把 `/images` 转发到 `127.0.0.1:8001`，需要先启动后端和图片服务器。

## 环境变量

后端在 `back_end/keys.env` 中配置：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DATABASE_HOST` / `DATABASE_PORT` | MySQL 地址、端口 | 无 |
| `DATABASE_NAME` / `DATABASE_USER` / `DATABASE_PASSWORD` | MySQL 库名、用户、密码 | 无 |
| `REDIS_HOST` / `REDIS_PORT` | Redis 地址、端口 | `127.0.0.1` / `6379` |
| `REDIS_PASSWORD` | Redis 密码（无密码留空） | 空 |
| `REDIS_MAX_CONNECTIONS` | Redis 连接池上限 | `50` |
| `REDIS_KEY_SECRET` | 邮箱哈希密钥（Redis key 里不出现明文邮箱），请使用足够长的随机字符串 | 空 |
| `SECRET_KEY` | JWT 签名密钥，请使用足够长的随机字符串 | 无 |
| `ALGORITHM` | JWT 算法，例如 `HS256` | 无 |
| `EMAIL_HOST` / `EMAIL_PORT` | SMTP 服务器、端口 | `smtp.qq.com` / `465` |
| `EMAIL_ADDRESS` | 发件邮箱 | 见 `tools_1/email.py` |
| `EMAIL_AUTH_CODE` | 邮箱 SMTP 授权码 | 空 |

可选（系统环境变量）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `CORS_ALLOWED_ORIGINS` | 允许跨域的前端地址，逗号分隔 | 见 `main.py` |
| `IMAGE_SERVER_HOST` / `IMAGE_SERVER_PORT` | 图片服务器监听地址、端口 | `0.0.0.0` / `8001` |
| `IMAGE_SERVER_PUBLIC_URL` | 图片服务器返回的图片地址前缀 | 见 `image_server/main.py` |

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 接口概览

完整的请求 / 响应格式请看运行后的 `/docs`。需要登录的接口使用 `Authorization: Bearer <token>`。

**认证与用户**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/send-code` | 发送注册验证码 |
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 当前用户信息 |
| GET | `/api/users/{user_id}` | 卖家公开信息 |

**商品与收藏**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/products` | 商品列表（分页） |
| GET | `/api/products/search` | 搜索商品 |
| GET | `/api/products/categories` | 分类列表 |
| GET | `/api/products/{product_id}` | 商品详情 |
| POST | `/api/products` | 发布商品（multipart，含图片） |
| PATCH | `/api/products/{product_id}` | 修改商品（重新审核） |
| PATCH | `/api/products/{product_id}/sold` | 标记售出 |
| DELETE | `/api/products/{product_id}` | 删除商品 |
| GET | `/api/my` | 我的商品 |
| GET | `/api/my/products/{product_id}` | 我的商品详情 |
| GET | `/api/users/{other_user_id}/products` | 他人的在售商品 |
| GET / POST / DELETE | `/api/favorite`、`/api/favorite/{product_id}` | 收藏列表 / 收藏 / 取消收藏 |

**订单**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/orders` | 下单 |
| GET | `/api/orders/my`、`/api/sales/my` | 我买到的 / 我卖出的 |
| GET | `/api/orders/{order_id}` | 订单详情 |
| PATCH | `/api/orders/{order_id}/cancel` | 取消订单 |
| PATCH | `/api/orders/{order_id}/receive` | 买家确认收货 |
| PATCH | `/api/orders/{order_id}/complete` | 卖家确认完成 |
| PUT / GET | `/api/orders/{order_id}/meeting` | 设置 / 查看面交时间地点 |
| POST | `/api/orders/{order_id}/meeting/confirm` | 确认面交安排 |
| GET | `/api/sales-statistics` | 销售统计 |

**聊天、举报、公告**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST / GET | `/api/chat/conversations` | 创建 / 获取订单会话；会话列表 |
| GET / POST | `/api/chat/conversations/{id}/messages` | 历史消息 / 发送消息 |
| POST | `/api/chat/messages/{message_id}/read` | 标记已读 |
| WebSocket | `/api/chat/ws/{conversation_id}` | 实时聊天 |
| POST | `/api/reports` | 提交举报 |
| GET | `/api/announcements` | 公告列表 |

**WebSocket 协议**：连接后 10 秒内先发送 `{"type": "auth", "token": "<JWT>"}`，成功后收到 `{"type": "auth_success"}`；之后发送 `{"type": "message", "content": "..."}` 发消息，`{"type": "ping"}` 保持心跳。

**管理端**（`/api/admin/...`，需管理员登录；账号管理仅超级管理员可用）

| 模块 | 路径 |
| --- | --- |
| 登录 / 自身信息 | `POST /api/admin/login`、`GET /api/admin/me` |
| 管理员账号 | `/api/admin/accounts`（创建、列表、改角色、改状态） |
| 用户 | `/api/admin/users`、`PATCH /api/admin/users/{id}/status` |
| 商品 | `/api/admin/products`、`PATCH .../{id}/review`、`PATCH .../{id}/status` |
| 订单 | `/api/admin/orders`、`/api/admin/orders/{id}` |
| 举报 | `/api/admin/reports`、`PATCH .../{id}/handle`、`PATCH .../{id}/status` |
| 公告 | `/api/admin/announcements`（增删改查） |
| 概览 | `GET /api/admin/overview` |

## 业务规则

| 规则 | 值 |
| --- | --- |
| 学号 | 9 位数字，入学年份为近三年 |
| 登录令牌有效期 | 60 分钟 |
| 登录失败限制 | 同一 IP + 邮箱 5 分钟内失败 5 次，暂时锁定 |
| 订单自动收货 | 下单后 7 天 |
| 商品发布频率 | 每人每小时最多 20 个 |
| 搜索频率 | 每分钟最多 20 次 |
| 聊天消息频率 | 每人每分钟最多 30 条 |
| 新用户信用分 | 100 |
| 商品审核流程 | 发布 / 修改后为「待审核」，管理员通过后才对外可见 |

## 部署建议

生产环境建议用 Nginx 做统一入口：前端静态文件由 Nginx 直接提供，`/api/`、`/admin/` 转发到后端，`/images/` 转发到图片服务器，WebSocket 需要升级头。

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端（npm run build 的产物）
    root /path/to/Trading_Platform/front_end/dist;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 图片：转给图片服务器（保留 /images/ 前缀）
    location /images/ {
        proxy_pass http://127.0.0.1:8001;
    }

    # WebSocket
    location /api/chat/ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    # 后端 API 与管理端页面
    location ~ ^/(api|admin)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

**真实 IP**：限流、登录锁定、IP 归属地都依赖客户端 IP。后端只会在请求直接来自本机反向代理（`127.0.0.1`）时才读取 `X-Real-IP` / `X-Forwarded-For`，所以 Nginx 要像上面这样用 `$remote_addr` **覆盖**这两个头，不要透传客户端自带的值。

## 安全提醒
- 生产环境请设置强随机的 `SECRET_KEY` 和 `REDIS_KEY_SECRET`，并给 Redis 设置密码。
- 图片服务器的 8001 端口只允许本机访问。
- 首个超级管理员请使用强密码。
- `Log/` 目录下的日志包含客户端 IP，不要公开。

## 后续计划

- [ ] 提供建表 SQL / 数据库迁移（Alembic）
- [ ] Docker / docker-compose 一键部署
- [ ] 自动化测试
- [ ] 多进程部署支持：布隆过滤器与 WebSocket 广播改用 Redis 共享

## 致谢

- IP 归属地使用 [ip2region](https://github.com/lionsoul2014/ip2region) 离线库。

## 许可证

发布前请补充 `LICENSE` 文件并在此说明。
