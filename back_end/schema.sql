-- 校园二手交易平台 建表脚本
-- 后端启动时发现数据库里一张业务表都没有，才会自动执行本文件。

create table admins
(
    id            bigint unsigned auto_increment
        primary key,
    username      varchar(50)                                             not null,
    password_hash varchar(255)                                            not null,
    role          enum ('super_admin', 'admin') default 'admin'           not null,
    status        enum ('normal', 'banned')     default 'normal'          not null,
    last_login_ip varchar(45)                                             null,
    last_login_at datetime                                                null,
    created_at    datetime                      default CURRENT_TIMESTAMP not null,
    updated_at    datetime                      default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint uk_admin_username
        unique (username)
) engine = InnoDB default charset = utf8mb4;

create table announcements
(
    id         bigint unsigned auto_increment comment '公告ID'
        primary key,
    title      varchar(100)                       not null comment '公告标题',
    content    text                               not null comment '公告正文',
    created_at datetime default CURRENT_TIMESTAMP not null comment '发布时间',
    updated_at datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间'
) engine = InnoDB default charset = utf8mb4 comment '平台公告表';

create index idx_created_at
    on announcements (created_at);

create table categories
(
    id         bigint unsigned auto_increment
        primary key,
    `key`      varchar(30)                        not null comment '分类标识，对应前端 category 字段',
    name       varchar(50)                        not null comment '分类名称',
    sort_order int      default 0                 not null,
    created_at datetime default CURRENT_TIMESTAMP not null,
    constraint `key`
        unique (`key`)
) engine = InnoDB default charset = utf8mb4 comment '商品分类表';

create table users
(
    id            bigint unsigned auto_increment
        primary key,
    username      varchar(50)                                         not null comment '用户名，唯一，不可重复',
    email         varchar(100)                                        not null comment '邮箱',
    password_hash varchar(255)                                        not null comment '密码哈希',
    student_id    varchar(30)                                         not null comment '学号，注册必填',
    campus        varchar(50)                                         null comment '所属校区',
    status        enum ('normal', 'banned') default 'normal'          not null comment '账号状态：正常/封禁',
    banned_until  datetime                                            null comment '封禁截止时间，NULL表示永久封禁',
    credit_score  int                       default 100               not null comment '信用分，默认100',
    register_ip   varchar(45)                                         null comment '注册IP',
    last_login_ip varchar(45)                                         null comment '最近登录IP',
    created_at    datetime                  default CURRENT_TIMESTAMP not null,
    updated_at    datetime                  default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    last_login_at datetime                                            null,
    constraint email
        unique (email),
    constraint username
        unique (username)
) engine = InnoDB default charset = utf8mb4 comment '用户表';

create index idx_campus
    on users (campus);

create index idx_status
    on users (status);

create table products
(
    id               bigint unsigned auto_increment
        primary key,
    seller_id        bigint unsigned                                                not null,
    category_id      bigint unsigned                                                not null,
    name             varchar(100)                                                   not null,
    price            decimal(10, 2)                                                 not null,
    original_price   decimal(10, 2)                                                 null,
    description      text                                                           null,
    status           enum ('on_sale', 'off_sale', 'sold') default 'on_sale'         not null,
    view_count       int unsigned                         default 0                 not null,
    campus           varchar(50)                                                    null,
    publish_province varchar(50)                                                    null comment '发布时的IP省份',
    created_at       datetime                             default CURRENT_TIMESTAMP not null,
    updated_at       datetime                             default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    sold_at          datetime                                                       null comment '标记为已售出的时间，用于销售统计',
    review_status    varchar(20)                          default 'pending'         not null comment '审核状态：pending待审核，approved通过，rejected拒绝',
    review_reason    varchar(500)                                                   null comment '审核原因',
    reviewed_at      datetime                                                       null comment '审核时间',
    reviewed_by      bigint unsigned                                                null comment '审核人ID',
    constraint fk_products_category
        foreign key (category_id) references categories (id),
    constraint fk_products_seller
        foreign key (seller_id) references users (id)
) engine = InnoDB default charset = utf8mb4 comment '商品表';

create index idx_campus
    on products (campus);

create index idx_category_id
    on products (category_id);

create index idx_seller_id
    on products (seller_id);

create index idx_sold_at
    on products (sold_at);

create index idx_status
    on products (status);

create table product_images
(
    id         bigint unsigned auto_increment
        primary key,
    product_id bigint unsigned                    not null,
    image_url  varchar(500)                       not null comment '商品图片访问地址',
    sort_order int      default 0                 not null comment '图片排序，0为主图',
    created_at datetime default CURRENT_TIMESTAMP not null,
    constraint fk_product_images_product
        foreign key (product_id) references products (id)
            on delete cascade
) engine = InnoDB default charset = utf8mb4 comment '商品图片表';

create index idx_product_images_product_id
    on product_images (product_id);

create index idx_product_images_sort_order
    on product_images (sort_order);

create table favorites
(
    id         bigint unsigned auto_increment
        primary key,
    user_id    bigint unsigned                    not null,
    product_id bigint unsigned                    not null,
    created_at datetime default CURRENT_TIMESTAMP not null,
    constraint uk_user_product
        unique (user_id, product_id),
    constraint fk_favorites_product
        foreign key (product_id) references products (id),
    constraint fk_favorites_user
        foreign key (user_id) references users (id)
) engine = InnoDB default charset = utf8mb4 comment '商品收藏表';

create index idx_product_id
    on favorites (product_id);

create table orders
(
    id                       bigint unsigned auto_increment
        primary key,
    order_no                 varchar(32)                                                                      not null,
    buyer_id                 bigint unsigned                                                                  not null,
    seller_id                bigint unsigned                                                                  not null,
    product_id               bigint unsigned                                                                  not null,
    price                    decimal(10, 2)                                                                   not null,
    status                   enum ('pending', 'received', 'completed', 'cancelled') default 'pending'         not null,
    meeting_location         varchar(100)                                                                     null,
    meeting_time             datetime                                                                         null,
    created_at               datetime                                               default CURRENT_TIMESTAMP not null,
    completed_at             datetime                                                                         null,
    cancelled_at             datetime                                                                         null,
    received_at              datetime                                                                         null comment '买家确认收货时间',
    auto_receive_at          datetime                                                                         null comment '自动确认收货截止时间',
    buyer_meeting_confirmed  tinyint(1)                                             default 0                 not null,
    seller_meeting_confirmed tinyint(1)                                             default 0                 not null,
    constraint order_no
        unique (order_no),
    constraint fk_orders_buyer
        foreign key (buyer_id) references users (id),
    constraint fk_orders_product
        foreign key (product_id) references products (id),
    constraint fk_orders_seller
        foreign key (seller_id) references users (id)
) engine = InnoDB default charset = utf8mb4 comment '订单表';

create index idx_buyer_id
    on orders (buyer_id);

create index idx_product_id
    on orders (product_id);

create index idx_seller_id
    on orders (seller_id);

create index idx_status
    on orders (status);

create table chat_conversations
(
    id         bigint unsigned auto_increment
        primary key,
    order_id   bigint unsigned                    not null,
    buyer_id   bigint unsigned                    not null,
    seller_id  bigint unsigned                    not null,
    created_at datetime default CURRENT_TIMESTAMP not null,
    updated_at datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    constraint uk_chat_order
        unique (order_id),
    constraint fk_chat_conversation_buyer
        foreign key (buyer_id) references users (id),
    constraint fk_chat_conversation_order
        foreign key (order_id) references orders (id),
    constraint fk_chat_conversation_seller
        foreign key (seller_id) references users (id)
) engine = InnoDB default charset = utf8mb4;

create table chat_messages
(
    id              bigint unsigned auto_increment
        primary key,
    conversation_id bigint unsigned                       not null,
    sender_id       bigint unsigned                       not null,
    content         text                                  not null,
    message_type    varchar(20) default 'text'            not null,
    is_read         tinyint(1)  default 0                 not null,
    created_at      datetime    default CURRENT_TIMESTAMP not null,
    constraint fk_chat_message_conversation
        foreign key (conversation_id) references chat_conversations (id),
    constraint fk_chat_message_sender
        foreign key (sender_id) references users (id)
) engine = InnoDB default charset = utf8mb4;

create index idx_chat_messages_conversation_created
    on chat_messages (conversation_id, created_at);

create index idx_chat_messages_sender
    on chat_messages (sender_id);

create table reports
(
    id           bigint unsigned auto_increment
        primary key,
    reporter_id  bigint unsigned                                                    not null comment '举报人ID',
    target_type  enum ('user', 'product')                 default 'user'            not null comment '举报目标类型',
    target_id    bigint unsigned                                                    not null comment '被举报的用户ID或商品ID',
    reason       varchar(500)                                                       not null comment '举报原因',
    status       enum ('pending', 'resolved', 'rejected') default 'pending'         not null comment '处理状态',
    handle_type  enum ('deduct_score', 'ban')                                       null,
    punish_score int                                                                null,
    ban_days     int                                                                null,
    handle_note  varchar(500)                                                       null,
    created_at   datetime                                 default CURRENT_TIMESTAMP not null,
    constraint fk_reports_reporter
        foreign key (reporter_id) references users (id)
) engine = InnoDB default charset = utf8mb4 comment '举报表';

create index idx_reporter
    on reports (reporter_id);

create index idx_status
    on reports (status);

create index idx_target
    on reports (target_type, target_id);

-- 初始商品分类（与前端 CATEGORIES 保持一致）
insert into categories (`key`, name, sort_order) values
    ('book', '教材书籍', 1),
    ('digital', '数码电子', 2),
    ('clothes', '服装配饰', 3),
    ('life', '生活日用', 4),
    ('sport', '运动户外', 5),
    ('furniture', '家具家电', 6),
    ('other', '其他', 7);