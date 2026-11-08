# 校园二手交易平台 · 源码审查报告

> 审查对象：`Trading_Platform.zip`（back_end + front_end，约 3.1 万行）
> 审查方式：逐个阅读了后端的 `main.py`、`tools_1/*`、`database_1/*`、`crud_1/orders.py`、`crud_1/produces.py`、`crud_1/users.py`、`crud_1/chat.py`、`routers_1/*`、`modles_1/*`、管理端 `admin/*`（含静态页 JS）、`image_server/main.py`，以及前端的 `router`、`stores`、`api/request.js`、`App.vue`、`ChatView`、`PublishView` 的关键部分。
> **没有逐行读完的部分**：前端 `ProfileView`、`OrderDetailView`、`DetailView` 的模板与样式（共约 9000 行）、管理端其余 curd 文件（用户 / 订单 / 举报 / 公告）、`crud_1/reports.py`、`crud_1/announcements.py`。这些文件里的问题本报告没有覆盖。
> 结论按严重程度排序，每条标明文件位置。「已确认」= 我在代码里直接看到；「需验证」= 取决于你的部署配置。

---

## 0. 先更正我之前的说法

| 之前的说法 | 实际情况 |
|---|---|
| 路线图第 1 项「下单可能超卖，需核查」 | **已确认没有问题**。`create_order` 用了 `SELECT ... FOR UPDATE` 锁商品行，并在同一事务内改状态、建订单，提交之后才清缓存。这部分写得对。 |
| 路线图第 6 项「多进程下自动收货会重复处理」 | 因为查询带 `FOR UPDATE` 且按 `status='pending'` 过滤，重复执行是幂等的，**不会出错**。真正的问题是缺索引（见 B9）。 |
| README「只在请求来自 127.0.0.1 时才读取 X-Forwarded-For」 | **只对一半成立**，见 B7。 |

---

## 1. 后端问题（按严重程度）

### P0：建议马上处理

#### B1. 图片服务器没有任何认证，且默认监听所有网卡
- 位置：`image_server/main.py`（`HOST` 默认 `0.0.0.0`，CORS `allow_origins=["*"]`，上传 / 删除接口无任何鉴权）
- 影响：只要 8001 端口能从外网访问，任何人都可以
  - 对任意 `product_id` 上传文件（只检查扩展名，大小上限 10MB，没有数量和总量限制）→ 可以写满磁盘；
  - 调用 `DELETE /api/images/product/{id}` 删光任意商品的图片。
- 附带问题：`PUBLIC_BASE_URL` 默认值写死了 `http://120.26.37.94:8001`，说明你的服务器公网 IP 暴露在公开仓库里，并且从这个默认值看，部署时 8001 很可能是对外开放的（**需验证**：从外网访问 `http://你的IP:8001/health` 是否通）。
- 另：`data = await file.read()` 先把整个请求体读进内存，**之后**才检查 10MB 上限，攻击者可以发超大请求耗内存。
- 修复建议：
  1. `IMAGE_SERVER_HOST` 默认改为 `127.0.0.1`，防火墙只放行 80 / 443；
  2. 后端调用图片服务器时加共享密钥请求头（如 `X-Internal-Token`），图片服务器校验；
  3. 用 Pillow 真正打开并校验图片（不能只看扩展名），限制像素尺寸，重新编码保存（顺便去掉 EXIF 里的 GPS）；
  4. 流式读取并限制大小；
  5. 删掉仓库里写死的 IP。

#### B2. 管理员登录没有任何限流或锁定
- 位置：`routers_1/admin` 的 `/api/admin/login`、`admin/curd_a/admins.py: admin_login`
- 用户登录有 IP + 邮箱的失败计数，管理员登录**完全没有**。管理员是最高权限，且第一个超级管理员是手动插入数据库的，密码强度没有程序约束。
- 叠加 B6（bcrypt 阻塞事件循环），攻击者连续发登录请求，还能让整个服务（包括聊天）卡顿。
- 修复：复用 `ip_rate_limit` + 按用户名的失败计数；管理端最好再限制来源 IP（Nginx `allow`）或加二次验证。

#### B3. `SECRET_KEY` 缺失时会静默变成字符串 `"None"`
- 位置：`tools_1/create_token.py`：`jwt.encode(to_encode, str(SECRET_KEY), ...)`
- 如果环境变量没读到，`str(None)` 就是 `"None"`，任何人都可以用这个密钥伪造任意用户和管理员 token。你的 `email_hash.py` 已经有「缺少就直接报错」的写法，这里应当保持一致。
- 修复：启动时检查 `SECRET_KEY` 非空且长度足够、`ALGORITHM` 在白名单内，否则抛错退出。

#### B4. 商品状态机有两个真实 bug（已确认）
`products.status` 只有 `on_sale / off_sale / sold`，而 `off_sale` 同时表示三种完全不同的情况：被订单占用、被审核驳回、被管理员强制下架。结果：

1. **被驳回的商品，修改后永远无法重新上架。**
   全仓库只有两处会把 `status` 设成 `on_sale`：发布商品（`publish_produce`）和取消订单（`cancel_order`）。驳回时 `review_product` 把 `status` 设成 `off_sale`；卖家修改后 `change_my_product` 只把 `review_status` 改回 `pending`；管理员通过时只改 `review_status`。三步下来 `status` 一直是 `off_sale`，商品既不能被购买也不会出现在列表里。卖家只能删除重发。
2. **取消订单会无条件把商品改回 `on_sale`**（`crud_1/orders.py` 的 `cancel_order`），会撤销管理员的强制下架或驳回。同时，商品有待完成订单时本来就是 `off_sale`，管理员去强制下架会得到「该商品已经下架」，无法操作。
- 修复：新增状态 `reserved`（被订单占用），取消订单时只把 `reserved` 改回 `on_sale`；审核通过时，如果商品没有活动订单，把 `off_sale` 恢复为 `on_sale`；强制下架时如有待完成订单，同时处理订单。

#### B5. 商品删除 / 标记售出存在逻辑漏洞和竞态
- 位置：`crud_1/produces.py` 的 `delete_my_product`、`mark_as_sold`
- `delete_my_product` 只拦截了 `pending` 和未满 6 个月的 `completed` 订单，**`received` 状态的订单没有拦截**（买家已确认收货、卖家还没点完成）。卖家此时删除商品，会连订单、聊天记录一起被物理删除，买家的交易记录凭空消失。
- 删除流程没有对商品行加锁，与并发下单交叉时，刚创建的订单可能被后面的 `delete(Order)` 一并删掉。
- 删除流程**先删图片服务器上的文件，再提交数据库**；如果提交失败，数据库里的图片记录会指向已不存在的文件。
- `mark_as_sold` 没有 `FOR UPDATE`，与 `create_order` 并发时，可能出现「商品已 sold 但存在 pending 订单」。
- 修复：这两个函数都用 `with_for_update()` 并重新检查状态；删除前拦截所有非终态订单；先提交数据库再异步清理图片；订单和聊天建议软删除而不是物理删除。

#### B6. bcrypt 在 async 接口里同步执行，会阻塞整个事件循环
- 位置：`tools_1/password_hash.py` 被 `user_login`、`user_register`、`admin_login`、`create_admin` 直接调用
- bcrypt 每次约 100–300ms 的纯 CPU 计算，期间事件循环被占住，所有请求（包括 WebSocket 聊天、缓存命中的读请求）一起卡住。
- 修复：`await asyncio.to_thread(check_password, ...)` / `asyncio.to_thread(password_hash, ...)`。

### P1：近期应该处理

#### B7. 客户端 IP 的获取方式前后不一致
- `tools_1/client_ip.py: get_client_ip` **无条件信任** `X-Forwarded-For` / `X-Real-IP`，没有检查请求是否来自可信代理。它被用于登录失败计数、注册、发验证码、发布商品的归属地。
- 而 `ip_rate_limit` 和搜索接口用的是 `request.client.host`，它之所以是真实 IP，是因为 uvicorn 默认开启 `proxy_headers` 且默认只信任 `127.0.0.1`（**这是隐式依赖**）。
- 后果：
  - 如果有人能直接访问 8000 端口，可以伪造请求头绕过登录锁和验证码 IP 限流；
  - 迁移到 Docker 后，Nginx 容器的 IP 不再是 `127.0.0.1`，`request.client.host` 会变成容器 IP，**所有用户共用一个限流桶**，登录和浏览很快就会被限流。
- 修复：统一一个函数，显式配置 `forwarded_allow_ips`（或自己维护可信代理网段），所有地方只用它；删掉 `get_client_ip` 里对任意来源请求头的信任。

#### B8. 发布商品：图片在数据库事务内上传，失败会留下孤儿文件
- 位置：`publish_produce`
- 流程是：插入商品（未提交）→ 逐张调用图片服务器上传 → 最后才 `commit`。问题：
  - 第 3 张失败时事务回滚，但第 1、2 张已经写到磁盘，没有任何清理；
  - 上传期间一直占着数据库连接和行锁；
  - 图片张数没有上限（前端只限制单张 10MB，没有张数限制），每张超时 30 秒，而防重复提交的锁只有 60 秒，会过期；
  - 没有校验 `category_id` 是否存在（`change_my_product` 有，发布没有），外键失败只会得到 500 且留下孤儿图片；
  - `validate_product` 没有价格上限，`Numeric(10,2)` 超范围会直接 500；也没有检查「原价 ≥ 现价」。
- 修复：先上传图片、拿到文件名，再开事务写库；失败时补偿删除已上传的文件；加图片张数上限（如 9）和价格上限。

#### B9. 缺少关键索引（订单扫描会锁全表）
- `orders` 每 5 秒执行一次：`WHERE status='pending' AND auto_receive_at <= now ... FOR UPDATE`。`orders` 上只有 `buyer_id / seller_id / product_id` 的单列索引，这条查询没有可用索引，在 REPEATABLE READ 下会对扫描到的行逐行加锁，下单和取消订单也要锁订单行，规模变大后容易互相阻塞甚至死锁。
- 商品列表 `WHERE status='on_sale' AND review_status='approved' ORDER BY created_at DESC, id DESC` 同样没有复合索引，`review_status` 还是普通字符串、没有索引。
- `chat_messages` 缺 `(conversation_id, created_at)` 复合索引。
- 修复：
  ```python
  Index("ix_orders_auto_receive", Order.status, Order.auto_receive_at)
  Index("ix_products_list", Product.status, Product.review_status, Product.created_at, Product.id)
  Index("ix_chat_messages_conv_created", ChatMessage.conversation_id, ChatMessage.created_at)
  ```
  自动收货查询再加 `.limit(200)` 和 `with_for_update(skip_locked=True)`，扫描间隔从 5 秒改成 30–60 秒（自动收货时间是 7 天，不需要 5 秒精度）。

#### B10. 数据库连接池没有保活设置，且每条 SQL 都写 INFO 日志
- `database_1/mysql_config.py`：`create_async_engine` 没设 `pool_pre_ping=True`、`pool_recycle`。MySQL 默认 8 小时会断开空闲连接，凌晨低峰后的第一批请求会遇到 `MySQL server has gone away`。
- 同文件的 `after_cursor_execute` 对**每一条**查询都 `logger.info`，线上日志量会非常大，而且 SQL 文本里会带上业务数据。建议只记录慢查询（≥300ms）和错误。
- 修复：`create_async_engine(..., pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=20)`。

#### B11. 登录与注册的信息泄露、以及校园 NAT 下的误伤
- `user_login`：封禁检查**在密码校验之前**，任何人都可以用「账号已被封禁」这条提示探测某邮箱是否存在；不存在的账号直接返回、存在的账号要跑 bcrypt，响应时间差也能区分。修复：先校验密码，或对不存在的账号也做一次假哈希。
- `user_register`：先查「邮箱 / 用户名 / 学号是否已注册」再校验验证码，没验证码就能枚举学号和邮箱。
- 登录失败计数按「IP + 邮箱」，换 IP 就能对同一个邮箱无限尝试。建议再加一个只按邮箱的全局计数（例如 15 分钟 20 次）。
- 这是校园项目：学生大多经过校园网 NAT，**一个出口 IP 背后可能是几百人**。目前的 IP 阈值（详情 / 列表 120 次每分钟、注册 30 次每小时、发验证码 20 次每半小时、登录 60 次每 5 分钟）在开学季很容易误伤。建议提高 IP 维度阈值，增加按账号 / 邮箱维度的限制。

#### B12. 订单可能永远停在 `received`
- 流程是 `pending → received → completed`，只有卖家点「完成」才会走到 `completed`，商品才会变成 `sold`。卖家一直不点，订单和商品就永远停在中间状态（商品是 `off_sale`，也无法删除订单）。
- 建议：`received` 之后超过 N 天自动完成，或允许买家确认后直接完成。

#### B13. 聊天模块
- `get_message` 一次返回会话的**全部**历史消息，没有分页。
- `read_message` 一次只能标记一条已读，前端的实现是对每条未读消息串行发一个请求（`ChatView.vue` 约 1119 行的 `for ... await`）。建议增加「整个会话标记已读」的批量接口。
- WebSocket 接收循环没有空闲超时，半开连接会一直占着；没有单用户连接数上限。
- `POST /api/chat/conversations/{id}/messages`（HTTP 发送）不会广播给 WebSocket 连接。当前前端只用 WebSocket 发送，所以暂时不会触发，但这是接口行为不一致的隐患。
- `get_my_message_list` 不返回最后一条消息和未读数，前端想做会话列表角标得多次请求。

#### B14. 列表接口缺分页，搜索是全表 LIKE
- `get_my_orders`、`get_my_sales`、`get_my_favorite`、`search_product_from_mysql`（最多 50 条，无翻页）都没有分页。
- 搜索用 `LIKE '%kw%'`，只匹配商品名，无法走索引。可以先加 MySQL `FULLTEXT ... WITH PARSER ngram`。

### P2：代码质量与维护性

- **死代码**：`crud_1/users.py` 里的 `_login_failures` / `_login_lock`（旧的内存限流，已被 Redis 取代）；`redis_config.py` 里的 `r = aioredis.Redis(...)  # 方便测试 最终要删除`；**用户名布隆过滤器只加载、只写入，没有任何地方查询**（`user_name_bloom` 全仓库只有 `.add`），启动时白白遍历全部用户。
- **命名拼写**：`modles_1`、`shemas_a`、`curd_a`、`uload_image_to_server`、`Logion`、`set_meting / get_meting / confirm_meting`、`create_my_order` 等。项目还小，现在改成本最低。
- **错误返回风格不统一**：有的返回 HTTP 200 + `{"code": 400}`（发布商品校验失败、搜索关键词、管理端审核），有的抛 `HTTPException`。前端必须同时处理两种。建议统一用 HTTP 状态码。
- **时间**：全站用 `datetime.now()`（无时区），只有管理端审核用了 `Asia/Shanghai`。服务器时区一变就会错。建议统一用 UTC 存储，或固定进程时区。
- **依赖**：`passlib` 和 `python-jose` 都已多年没有活跃维护；密码最长 64 字符，但 bcrypt 只取前 72 字节，含中文时可能被静默截断。可以考虑直接用 `bcrypt` / `argon2-cffi` 和 `PyJWT`。
- **登录 / 注册模型缺长度限制**：`Logion.user_email / password`、`Register.username / student_id / password` 没有 `max_length`，请求体可以很大。
- **配置写死**：`tools_1/uload_image_to_server.py` 里 `IMAGE_SERVER = "http://127.0.0.1:8001"` 写死；`tools_1/email.py` 里 `EMAIL_ADDRESS` 的默认值是一个真实邮箱。Docker 化时都要改成环境变量。
- **进程内状态**（上多 worker 前必须处理）：商品布隆过滤器、各类 `TTLCache`、WebSocket `ConnectionManager`、后台任务。

### 值得肯定的地方（保持这些写法）
- 下单 / 取消 / 确认收货都用了 `FOR UPDATE`，缓存失效放在提交之后，Redis 失败不会让已提交的订单返回 500。
- 浏览量回写用「重命名 + 基准值 + 绝对值写回」，重试不会重复累加，设计得很细。
- 商品详情的缓存穿透 / 击穿 / 雪崩防护完整（布隆、空值、状态标记、分片锁、TTL 抖动）。
- 验证码、邮箱哈希进 Redis key、验证码比较用 `compare_digest`、验证码错误次数上限，这些细节都做到了。
- 管理端静态页统一使用 `escapeHTML`，token 放 `sessionStorage`，管理员 token 带 `token_type` 并每次请求查库校验状态，这是好做法。
- WebSocket 先发 auth 消息再校验，并每条消息重新检查账号状态。

---

## 2. 前端问题与改进建议

### 先修的真实问题

#### F1. 退出登录和登录过期不会清理本地缓存的订单数据（已确认，隐私问题）
- `stores/market.js` 把 `cm_orders`、`cm_mysales`、`cm_reports` 持久化到 `localStorage`，并在 store 初始化时读回。
- 退出登录（`ProfileView.vue` 约 1796 行）只清了 `cm_token`、`cm_user` 和收藏；登录过期（`App.vue` 的 `handleAuthExpired`）只调用 `userStore.logout()`，**市场数据完全没清**。
- 在校园机房等共用电脑上，下一个用户登录前会短暂看到上一个人的订单、销售记录（含金额、面交地点）。
- 修复：写一个统一的 `resetSession()`，同时清理所有 `cm_*` 键和 Pinia store，退出登录与过期两条路径都调用；或者干脆不要把服务端数据持久化到 `localStorage`。

#### F2. 固定 60 分钟的 token，会让用户在填表中途被踢出
- `request.js` 遇到任何 401 就清 token 并跳登录页，发布商品这种要填很久、还要选多张图的页面，提交时才发现过期，表单内容全部丢失。
- 改进：后端加 refresh token（路线图第 7 项）；前端在拦截器里静默续期并重放请求；发布页把草稿存到 `sessionStorage`；过期时弹出提示，并保留 `redirect`。

#### F3. 启动时先等 `/auth/me` 返回才挂载应用
- `main.js` 里 `await userStore.restoreSession()` 之后才 `app.mount`。有 token 且接口慢时，用户会看到最长 10 秒（axios 超时）的白屏，`index.html` 里也没有任何占位内容。
- 改进：先挂载，后台恢复会话；用已缓存的 `cm_user` 先渲染，再静默校验。

### 体验与性能

| 方向 | 现状 | 建议 |
|---|---|---|
| **组件拆分** | `ProfileView` 约 3600 行、`OrderDetailView` 约 3100 行、`DetailView` 约 2500 行、`ChatView` 约 1900 行、`PublishView` 约 1800 行，`market.js` 约 1350 行 | 按功能拆成子组件和 composables（如 `useWebSocket`、`useImageUploader`、`useOrderActions`），样式拆出去。这是长期维护成本最高的一项 |
| **路由懒加载** | 只有订单详情和聊天是懒加载，其余页面都打进主包（主包约 240KB） | 全部改成 `() => import(...)`，并在 `vite.config.js` 里用 `manualChunks` 拆分 vue / axios 等 |
| **请求层** | 只处理 401 | 统一处理 403（被封禁）、429（弹「操作太频繁」）、网络错误、超时；搜索时取消上一次请求；对 GET 做有限重试 |
| **首页** | 滚动加载 + 搜索防抖已有 | 加骨架屏；筛选（价格区间、校区、排序）；搜索词和分类同步到 URL，后退时保留位置（`keep-alive`） |
| **图片** | 列表有 `loading="lazy"` | 给 `<img>` 加 `width/height` 防布局抖动；列表用缩略图（需后端配合）；加载失败时显示占位图 |
| **发布页** | 只检查类型和单张 10MB，没有张数上限 | 限制张数；上传前用 canvas 压缩到最长边 1600px、转 WebP；上传进度条；拖拽排序；用完 `URL.revokeObjectURL` 释放预览 |
| **聊天** | 重连、心跳、重连失败提示都已经有 | 增加历史分页（向上滚动加载）；用批量接口一次性标记已读；会话列表显示未读角标；页面不可见时暂停心跳 |
| **订单页** | — | 用步骤条展示 `pending → received → completed`；用 `auto_receive_at` 做自动收货倒计时；面交安排的确认状态更直观 |
| **无障碍** | 图标按钮多用 `v-html` 拼 SVG 字符串 | 改成 SVG 组件，并给图标按钮加 `aria-label`；检查键盘焦点和颜色对比度 |
| **移动端** | 有侧边栏导航 | 校园用户主要用手机，建议加底部导航栏，并在小屏上逐页验收 |

### 工程化
- 目前 `package.json` 没有任何 lint、格式化和测试。建议加 **ESLint + Prettier**、**Vitest**（测 store 与工具函数）、**Playwright**（测「注册 → 发布 → 下单 → 聊天」主流程）。
- 逐步引入 **TypeScript**，或者至少用 JSDoc 加类型。可以用后端的 OpenAPI 文档自动生成接口类型，避免前后端字段对不上（现在 `market.js` 里需要 `convertProduct / convertOrder / normalizeList` 这么多兼容转换，就是接口格式不统一的代价）。
- API 基础地址、WebSocket 地址放进 `.env`，不要散落在代码里。
- 部署时在 Nginx 加 **CSP** 响应头。

### 安全层面（前端）
- 我检查了 `v-html` 的所有用法：数据源都是本地写死的 SVG 常量，**没有拼接用户输入**，这点是安全的。请把「不对用户内容使用 `v-html`」当作团队约定写进文档。
- token 存在 `localStorage`，在没有 XSS 的前提下可接受；配合短有效期 + refresh token 会更稳。
- 登录后的 `redirect` 参数已经做了 `startsWith('/')` 且排除 `//` 的校验，写得对。

---

## 3. 建议的修复顺序

**第一批（一两天内，影响安全或数据正确）**
1. B1 图片服务器：绑定 127.0.0.1、加内部密钥、删除写死的 IP（并确认 8001 没有对外开放）
2. B3 `SECRET_KEY` 缺失时启动失败
3. B2 管理员登录限流
4. B6 bcrypt 放进线程
5. B4 商品状态机（新增 `reserved` 状态）
6. F1 退出 / 过期时清理本地缓存

**第二批（一周内）**
7. B5 删除 / 标记售出加锁，拦截 `received` 订单
8. B7 统一客户端 IP 获取，显式配置可信代理
9. B9 / B10 补索引、连接池保活、精简 SQL 日志
10. B8 发布流程改为「先传图、再写库」，补偿删除
11. B11 登录注册信息泄露与 NAT 阈值
12. F2 / F3 token 续期与启动白屏

**第三批（之后）**
13. B12 订单自动完成；B13 / B14 聊天与列表分页
14. 前端组件拆分、懒加载、测试与 lint
15. 之前路线图中的 Docker Compose、自动化测试、压测、多进程支持、搜索升级等

---

## 4. 仓库卫生检查（你上传的压缩包里）

- `back_end/keys.env` 在压缩包里，**里面是真实的配置**。请确认它没有被提交到 GitHub；如果曾经提交过，需要把数据库密码、Redis 密码、`SECRET_KEY`、`REDIS_KEY_SECRET`、邮箱授权码全部更换，并清理 Git 历史。仓库里只应保留 `keys.env.example`。
- 压缩包里还有 `__pycache__/`、`Log/`、`front_end/dist/`、`node_modules/`，请确认 `.gitignore` 已覆盖（日志含客户端 IP，不应公开）。
- 压缩包里没有 `Market_Table.sql`，而 GitHub 首页的文件列表里有。请确认它和 `modles_1/`、`admin/modles_a/` 的模型一致，并同步修正 README 里「暂未提供建表 SQL」的说法。