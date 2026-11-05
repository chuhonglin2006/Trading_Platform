(() => {
    'use strict';

    const API = {
        me: '/api/admin/me',
        overview: '/api/admin/overview',
        admins: '/api/admin/accounts',
        users: '/api/admin/users',
        products: '/api/admin/products',
        orders: '/api/admin/orders',
        reports: '/api/admin/reports',
        announcements: '/api/admin/announcements'
    };

    const MODULES = {
        overview: { title: '数据概览', icon: '▦' },
        users: { title: '用户管理', icon: '♙' },
        products: { title: '商品审核', icon: '▣' },
        orders: { title: '订单管理', icon: '▤' },
        reports: { title: '举报管理', icon: '⚑' },
        announcements: { title: '公告管理', icon: '◈' },
        admins: { title: '管理员管理', icon: '♛' }
    };

    const state = {
        admin: null,
        view: 'overview',
        page: 1,
        pageSize: 20,
        total: 0,
        keyword: '',
        status: '',
        rows: [],
        loading: false,
        requestId: 0
    };

    const $ = selector => document.querySelector(selector);
    const $$ = selector => [...document.querySelectorAll(selector)];

    /* ==================== 通用工具 ==================== */

    function escapeHTML(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function formatDate(value) {
        if (!value) return '—';

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return escapeHTML(value);
        }

        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatMoney(value) {
        const number = Number(value);

        return Number.isFinite(number)
            ? `¥${number.toFixed(2)}`
            : '—';
    }

    function showMessage(message, type = 'success') {
        let container = $('#admin-toast-container');

        if (!container) {
            container = document.createElement('div');
            container.id = 'admin-toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `admin-toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3500);
    }

    function statusBadge(value) {
        const labels = {
            normal: '正常',
            banned: '已封禁',
            pending: '待审核',
            approved: '已通过',
            rejected: '已拒绝',
            on_sale: '出售中',
            off_sale: '已下架',
            sold: '已售出',
            completed: '已完成',
            cancelled: '已取消',
            paid: '已支付',
            unpaid: '待支付',
            resolved: '已处理',
            dismissed: '已驳回',
            super_admin: '超级管理员',
            admin: '普通管理员'
        };

        const safeValue = String(value ?? 'unknown');

        return `
            <span class="dash-badge"
                  data-status="${escapeHTML(safeValue)}">
                ${escapeHTML(labels[safeValue] ?? safeValue)}
            </span>
        `;
    }

    function buildQuery(params = {}) {
        const search = new URLSearchParams();

        Object.entries(params).forEach(([key, value]) => {
            if (
                value !== null &&
                value !== undefined &&
                value !== ''
            ) {
                search.set(key, String(value));
            }
        });

        const query = search.toString();

        return query ? `?${query}` : '';
    }

    function getToken() {
        return sessionStorage.getItem('admin_token');
    }

    function logout() {
        sessionStorage.removeItem('admin_token');
        sessionStorage.removeItem('admin_profile');

        window.location.replace('/admin/login.html');
    }

    async function request(url, options = {}) {
        const token = getToken();

        if (!token) {
            logout();
            throw new Error('请先登录');
        }

        const headers = {
            Authorization: `Bearer ${token}`,
            ...options.headers
        };

        if (
            options.body !== undefined &&
            !(options.body instanceof FormData)
        ) {
            headers['Content-Type'] = 'application/json';
        }

        let response;

        try {
            response = await fetch(url, {
                ...options,
                headers
            });
        } catch {
            throw new Error('网络连接失败，请检查服务器');
        }

        if (response.status === 401) {
            logout();
            throw new Error('登录已过期');
        }

        let result;

        try {
            result = await response.json();
        } catch {
            throw new Error(`服务器返回异常：HTTP ${response.status}`);
        }

        if (!response.ok || (result.code && result.code !== 200)) {
            const detail = result.detail;
            const message =
                result.message ||
                (typeof detail === 'string' ? detail : null) ||
                `请求失败：HTTP ${response.status}`;

            throw new Error(message);
        }

        return result;
    }

    const get = url => request(url);

    const post = (url, data) => request(url, {
        method: 'POST',
        body: JSON.stringify(data)
    });

    const patch = (url, data) => request(url, {
        method: 'PATCH',
        body: JSON.stringify(data)
    });

    const del = url => request(url, {
        method: 'DELETE'
    });

    /* ==================== 图片处理 ==================== */

    /**
     * 商品图片支持：
     * 1. https://example.com/xxx.jpg
     * 2. /uploads/xxx.jpg
     * 3. uploads/xxx.jpg
     *
     * 相对图片路径使用当前后台同源地址；
     * 主服务会挂载 /images，生产环境也可由 Nginx 代理到图片服务。
     */
    function productImageUrl(image) {
        let url = '';

        if (typeof image === 'string') {
            url = image;
        } else if (image && typeof image === 'object') {
            url =
                image.url ||
                image.image_url ||
                image.imageUrl ||
                image.path ||
                '';
        }

        if (!url) return '';

        url = String(url).trim();

        // 禁止 javascript: 等不安全协议
        if (/^https?:\/\//i.test(url)) {
            return url;
        }

        if (url.startsWith('//')) {
            return `${window.location.protocol}${url}`;
        }

        if (/^[a-z][a-z\d+.-]*:/i.test(url)) {
            return '';
        }

        try {
            return new URL(
                url.startsWith('/') ? url : `/${url}`,
                window.location.origin
            ).href;
        } catch {
            return '';
        }
    }

    function getProductImages(product) {
        const images = product.images;

        if (!Array.isArray(images)) {
            return [];
        }

        return images
            .map(productImageUrl)
            .filter(Boolean);
    }

    function productThumbnail(product) {
        const image = getProductImages(product)[0];

        if (!image) {
            return `
                <div class="product-no-image">
                    暂无图片
                </div>
            `;
        }

        return `
            <button
                type="button"
                class="product-image-button"
                data-action="product-detail"
                data-id="${escapeHTML(product.id)}"
                title="查看商品全部图片"
            >
                <img
                    src="${escapeHTML(image)}"
                    class="product-thumbnail"
                    alt="商品主图"
                    loading="lazy"
                    onerror="this.style.display='none';this.parentElement.textContent='图片加载失败'"
                >
            </button>
        `;
    }

    /* ==================== 弹窗 ==================== */

    function closeModal() {
        $('#admin-modal-mask')?.remove();
    }

    function openModal({
        title,
        content,
        confirmText = '',
        onConfirm = null,
        width = '680px'
    }) {
        closeModal();

        const mask = document.createElement('div');

        mask.id = 'admin-modal-mask';
        mask.className = 'admin-modal-mask';

        mask.innerHTML = `
            <div class="admin-modal"
                 style="max-width:${escapeHTML(width)}">
                <div class="admin-modal-header">
                    <h3>${escapeHTML(title)}</h3>
                    <button
                        type="button"
                        class="admin-modal-close"
                        aria-label="关闭"
                    >×</button>
                </div>

                <div class="admin-modal-body">
                    ${content}
                </div>

                <div class="admin-modal-footer">
                    <button
                        type="button"
                        class="dash-btn secondary"
                        data-modal-close
                    >关闭</button>

                    ${onConfirm
                ? `
                                <button
                                    type="button"
                                    class="dash-btn primary"
                                    id="admin-modal-confirm"
                                >
                                    ${escapeHTML(confirmText || '确定')}
                                </button>
                            `
                : ''
            }
                </div>
            </div>
        `;

        document.body.appendChild(mask);

        mask.querySelector('.admin-modal-close')
            .addEventListener('click', closeModal);

        mask.querySelector('[data-modal-close]')
            .addEventListener('click', closeModal);

        mask.addEventListener('click', event => {
            if (event.target === mask) {
                closeModal();
            }
        });

        if (onConfirm) {
            const button = mask.querySelector('#admin-modal-confirm');

            button.addEventListener('click', async () => {
                if (button.disabled) return;

                button.disabled = true;
                button.textContent = '处理中...';

                try {
                    const shouldClose = await onConfirm(mask);

                    if (shouldClose !== false) {
                        closeModal();
                    }
                } catch (error) {
                    showMessage(error.message, 'error');
                } finally {
                    if (button.isConnected) {
                        button.disabled = false;
                        button.textContent = confirmText || '确定';
                    }
                }
            });
        }

        return mask;
    }

    function detailRows(data) {
        return `
            <dl class="admin-detail-list">
                ${Object.entries(data).map(([key, value]) => `
                        <dt>${escapeHTML(key)}</dt>
                        <dd>${escapeHTML(value ?? '—')}</dd>
                    `).join('')
            }
            </dl>
        `;
    }

    /* ==================== 商品详情和图片预览 ==================== */

    function showProductDetail(product) {
        const images = getProductImages(product);

        const gallery = images.length
            ? `
                <div class="product-detail-gallery">
                    ${images.map((url, index) => `
                            <button
                                type="button"
                                class="product-gallery-item"
                                data-preview-index="${index}"
                                title="点击放大图片"
                            >
                                <img
                                    src="${escapeHTML(url)}"
                                    alt="商品图片 ${index + 1}"
                                    loading="lazy"
                                >
                            </button>
                        `).join('')
            }
                </div>
            `
            : `
                <div class="product-empty-gallery">
                    该商品暂无图片
                </div>
            `;

        const mask = openModal({
            title: `商品详情 #${product.id}`,
            width: '900px',
            content: `
                <h4 class="product-section-title">
                    商品图片（${images.length}）
                </h4>

                ${gallery}

                <h4 class="product-section-title">
                    商品信息
                </h4>

                ${detailRows({
                商品ID: product.id,
                商品名称: product.name ?? product.product_name,
                商品价格: formatMoney(product.price),
                原价: product.original_price == null
                    ? '—'
                    : formatMoney(product.original_price),
                卖家: product.seller?.username ??
                    product.seller_username,
                商品分类: product.category?.name,
                所属校区: product.campus,
                商品描述: product.description,
                商品状态: product.status,
                审核状态: product.review_status,
                发布时间: formatDate(product.created_at)
            })}
            `
        });

        mask.querySelectorAll('[data-preview-index]')
            .forEach(button => {
                button.addEventListener('click', () => {
                    const index = Number(button.dataset.previewIndex);

                    showImagePreview(images, index);
                });
            });
    }

    function showImagePreview(images, startIndex = 0) {
        if (!images.length) return;

        let index = startIndex;

        const preview = document.createElement('div');
        preview.className = 'product-image-preview';

        preview.innerHTML = `
            <button
                type="button"
                class="preview-close"
                aria-label="关闭图片预览"
            >×</button>

            <button
                type="button"
                class="preview-arrow"
                data-direction="-1"
                aria-label="上一张"
            >‹</button>

            <div class="preview-main">
                <img alt="商品大图">
                <div class="preview-counter"></div>
                <a
                    class="preview-original"
                    target="_blank"
                    rel="noopener noreferrer"
                >在新窗口打开原图</a>
            </div>

            <button
                type="button"
                class="preview-arrow"
                data-direction="1"
                aria-label="下一张"
            >›</button>
        `;

        function update() {
            const url = images[index];

            preview.querySelector('img').src = url;

            preview.querySelector('.preview-counter').textContent =
                `${index + 1} / ${images.length}`;

            preview.querySelector('.preview-original').href = url;

            preview.querySelectorAll('[data-direction]')
                .forEach(button => {
                    button.hidden = images.length <= 1;
                });
        }

        function close() {
            document.removeEventListener('keydown', onKeydown);
            preview.remove();
        }

        function onKeydown(event) {
            if (event.key === 'Escape') close();

            if (event.key === 'ArrowLeft') {
                index = (index - 1 + images.length) % images.length;
                update();
            }

            if (event.key === 'ArrowRight') {
                index = (index + 1) % images.length;
                update();
            }
        }

        preview.querySelector('.preview-close')
            .addEventListener('click', close);

        preview.querySelectorAll('[data-direction]')
            .forEach(button => {
                button.addEventListener('click', () => {
                    index = (
                        index +
                        Number(button.dataset.direction) +
                        images.length
                    ) % images.length;

                    update();
                });
            });

        preview.addEventListener('click', event => {
            if (event.target === preview) close();
        });

        document.addEventListener('keydown', onKeydown);
        document.body.appendChild(preview);

        update();
    }

    /* ==================== 表格 ==================== */

    function renderTable(columns, rows, actions = null) {
        if (!rows.length) {
            return `
                <div class="dash-empty">
                    暂无符合条件的数据
                </div>
            `;
        }

        return `
            <div class="dash-table-wrap">
                <table class="dash-table">
                    <thead>
                        <tr>
                            ${columns.map(column => `
                                    <th>${escapeHTML(column.title)}</th>
                                `).join('')
            }
                            ${actions ? '<th>操作</th>' : ''}
                        </tr>
                    </thead>

                    <tbody>
                        ${rows.map(row => `
                                <tr>
                                    ${columns.map(column => `
                                            <td>
                                                ${column.render
                    ? column.render(row)
                    : escapeHTML(
                        row[column.key] ?? '—'
                    )
                }
                                            </td>
                                        `).join('')
                }

                                    ${actions
                    ? `
                                                <td>
                                                    <div class="dash-actions">
                                                        ${actions(row)}
                                                    </div>
                                                </td>
                                            `
                    : ''
                }
                                </tr>
                            `).join('')
            }
                    </tbody>
                </table>
            </div>
        `;
    }

    function actionButton(label, action, id, variant = '') {
        return `
            <button
                type="button"
                class="dash-btn small ${escapeHTML(variant)}"
                data-action="${escapeHTML(action)}"
                data-id="${escapeHTML(id)}"
            >
                ${escapeHTML(label)}
            </button>
        `;
    }

    function renderPagination() {
        const totalPages = Math.max(
            1,
            Math.ceil(state.total / state.pageSize)
        );

        return `
            <div class="dash-pagination">
                <span>
                    共 ${state.total} 条，
                    第 ${state.page} / ${totalPages} 页
                </span>

                <div>
                    <button
                        type="button"
                        class="dash-btn secondary"
                        data-page="${state.page - 1}"
                        ${state.page <= 1 ? 'disabled' : ''}
                    >上一页</button>

                    <button
                        type="button"
                        class="dash-btn secondary"
                        data-page="${state.page + 1}"
                        ${state.page >= totalPages ? 'disabled' : ''}
                    >下一页</button>
                </div>
            </div>
        `;
    }

    function normalizeList(data, key) {
        if (Array.isArray(data)) {
            return {
                rows: data,
                total: data.length
            };
        }

        const rows =
            data?.[key] ??
            data?.items ??
            data?.list ??
            [];

        return {
            rows: Array.isArray(rows) ? rows : [],
            total: Number(data?.total ?? rows.length ?? 0)
        };
    }

    /* ==================== 页面框架 ==================== */

    function renderModuleShell({
        title,
        placeholder = '输入关键词搜索',
        filters = [],
        createLabel = ''
    }) {
        const container = $('#dashboard-content');

        if (!container) return;

        container.innerHTML = `
            <div class="dash-panel">
                <div class="dash-panel-header">
                    <h3>${escapeHTML(title)}</h3>
                </div>

                <div class="dash-toolbar">
                    <input
                        type="search"
                        id="dash-keyword"
                        class="dash-input"
                        placeholder="${escapeHTML(placeholder)}"
                        value="${escapeHTML(state.keyword)}"
                    >

                    ${filters.length
                ? `
                                <select
                                    id="dash-status"
                                    class="dash-select"
                                >
                                    ${filters.map(item => `
                                            <option
                                                value="${escapeHTML(item.value)}"
                                                ${state.status === item.value
                        ? 'selected'
                        : ''
                    }
                                            >
                                                ${escapeHTML(item.label)}
                                            </option>
                                        `).join('')
                }
                                </select>
                            `
                : ''
            }

                    <button
                        type="button"
                        class="dash-btn primary"
                        id="dash-search"
                    >搜索</button>

                    <button
                        type="button"
                        class="dash-btn secondary"
                        id="dash-refresh"
                    >刷新</button>

                    ${createLabel
                ? `
                                <button
                                    type="button"
                                    class="dash-btn primary"
                                    id="dash-create"
                                >
                                    ${escapeHTML(createLabel)}
                                </button>
                            `
                : ''
            }
                </div>

                <div id="dash-list">
                    <div class="dash-empty">正在加载...</div>
                </div>

                <div id="dash-pagination"></div>
            </div>
        `;

        $('#dash-search')?.addEventListener('click', () => {
            state.keyword = $('#dash-keyword').value.trim();
            state.status = $('#dash-status')?.value ?? '';
            state.page = 1;

            loadModule();
        });

        $('#dash-keyword')?.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                $('#dash-search').click();
            }
        });

        $('#dash-status')?.addEventListener('change', () => {
            state.status = $('#dash-status').value;
            state.keyword = $('#dash-keyword').value.trim();
            state.page = 1;

            loadModule();
        });

        $('#dash-refresh')?.addEventListener('click', () => {
            loadModule();
        });

        $('#dash-create')?.addEventListener('click', () => {
            if (state.view === 'admins') {
                showCreateAdminModal();
            } else if (state.view === 'announcements') {
                showAnnouncementModal();
            }
        });

        $('#dash-list')?.addEventListener(
            'click',
            handleModuleAction
        );

        $('#dash-pagination')?.addEventListener(
            'click',
            event => {
                const button = event.target.closest('[data-page]');

                if (!button || button.disabled) return;

                state.page = Number(button.dataset.page);

                loadModule();
            }
        );
    }

    function setTable(html, paginated = true) {
        const list = $('#dash-list');
        const pagination = $('#dash-pagination');

        if (list) list.innerHTML = html;

        if (pagination) {
            pagination.innerHTML = paginated
                ? renderPagination()
                : '';
        }
    }

    /* ==================== 管理员验证 ==================== */

    async function verifyAdmin() {
        if (!getToken()) {
            logout();
            return false;
        }

        try {
            const result = await get(API.me);

            state.admin = result.data;

            sessionStorage.setItem(
                'admin_profile',
                JSON.stringify(state.admin)
            );

            const username = state.admin.username || '管理员';
            const isSuper = state.admin.role === 'super_admin';

            if ($('#admin-name')) {
                $('#admin-name').textContent = username;
            }

            if ($('#welcome-name')) {
                $('#welcome-name').textContent = username;
            }

            if ($('#avatar')) {
                $('#avatar').textContent = username[0].toUpperCase();
            }

            if ($('#admin-role')) {
                $('#admin-role').textContent =
                    isSuper ? '超级管理员' : '普通管理员';
            }

            $$('.super-only').forEach(element => {
                element.hidden = !isSuper;
            });

            return true;
        } catch (error) {
            showMessage(error.message, 'error');
            return false;
        }
    }

    /* ==================== 数据概览 ==================== */

    async function loadOverview() {
        const container = $('#dashboard-overview-extra');

        if (!container) return;

        container.innerHTML = `
            <div class="dash-empty">
                正在加载平台统计数据...
            </div>
        `;

        try {
            const result = await get(API.overview);
            const data = result.data ?? {};

            const cards = [
                ['用户总数', data.total_users ?? 0],
                ['在售商品', data.on_sale_products ?? 0],
                ['待审核商品', data.pending_products ?? 0],
                ['订单总数', data.total_orders ?? 0],
                ['待处理举报', data.pending_reports ?? 0]
            ];

            container.innerHTML = `
                <div class="admin-stat-grid">
                    ${cards.map(([label, value]) => `
                            <div class="admin-stat-card">
                                <span>${escapeHTML(label)}</span>
                                <strong>${escapeHTML(value)}</strong>
                            </div>
                        `).join('')
                }
                </div>
            `;
        } catch (error) {
            container.innerHTML = `
                <div class="dash-empty">
                    统计接口暂不可用：
                    ${escapeHTML(error.message)}
                </div>
            `;
        }
    }

    /* ==================== 用户管理 ==================== */

    async function loadUsers() {
        const result = await get(
            API.users + buildQuery({
                page: state.page,
                page_size: state.pageSize,
                keyword: state.keyword,
                user_status: state.status
            })
        );

        const data = normalizeList(result.data, 'users');

        state.rows = data.rows;
        state.total = data.total;

        const columns = [
            { title: 'ID', key: 'id' },
            { title: '用户名', key: 'username' },
            { title: '邮箱', key: 'email' },
            { title: '学号', key: 'student_id' },
            { title: '校区', key: 'campus' },
            {
                title: '信用分',
                render: row => escapeHTML(row.credit_score)
            },
            {
                title: '状态',
                render: row => statusBadge(row.status)
            },
            {
                title: '注册时间',
                render: row => formatDate(row.created_at)
            }
        ];

        setTable(renderTable(columns, data.rows, row => `
            ${actionButton('详情', 'user-detail', row.id)}
            ${row.status === 'banned'
                ? actionButton(
                    '解封',
                    'user-unban',
                    row.id,
                    'success'
                )
                : actionButton(
                    '封禁',
                    'user-ban',
                    row.id,
                    'danger'
                )
            }
        `));
    }

    function showUserDetail(user) {
        openModal({
            title: `用户详情 #${user.id}`,
            content: detailRows({
                ID: user.id,
                用户名: user.username,
                邮箱: user.email,
                学号: user.student_id,
                校区: user.campus,
                信用分: user.credit_score,
                状态: user.status,
                封禁截止: user.status === 'banned'
                    ? (user.banned_until
                        ? formatDate(user.banned_until)
                        : '永久封禁')
                    : '—',
                注册时间: formatDate(user.created_at),
                最近登录: formatDate(user.last_login_at)
            })
        });
    }

    async function changeUserStatus(user, status) {
        const action = status === 'banned' ? '封禁' : '解封';

        if (!window.confirm(
            `确定${action}用户「${user.username}」吗？`
        )) {
            return;
        }

        await patch(
            `${API.users}/${user.id}/status`,
            { status }
        );

        showMessage(`用户${action}成功`);

        await loadModule();
    }

    /* ==================== 商品审核 ==================== */

    async function loadProducts() {
        const result = await get(
            API.products + buildQuery({
                page: state.page,
                page_size: state.pageSize,
                keyword: state.keyword,
                review_status: state.status
            })
        );

        const data = normalizeList(result.data, 'products');

        state.rows = data.rows;
        state.total = data.total;

        const columns = [
            {
                title: '图片',
                render: productThumbnail
            },
            {
                title: '商品ID',
                key: 'id'
            },
            {
                title: '商品名称',
                render: row => escapeHTML(
                    row.name ?? row.product_name ?? '—'
                )
            },
            {
                title: '商品分类',
                render: row => escapeHTML(
                    row.category?.name ??
                    row.category_name ??
                    '未分类'
                )
            },
            {
                title: '售价',
                render: row => formatMoney(row.price)
            },
            {
                title: '原价',
                render: row => row.original_price == null
                    ? '—'
                    : formatMoney(row.original_price)
            },
            {
                title: '卖家',
                render: row => escapeHTML(
                    row.seller?.username ??
                    row.seller_username ??
                    row.seller_id ??
                    '—'
                )
            },
            {
                title: '审核状态',
                render: row => statusBadge(row.review_status)
            },
            {
                title: '商品状态',
                render: row => statusBadge(row.status)
            },
            {
                title: '发布时间',
                render: row => formatDate(row.created_at)
            }
        ];

        setTable(renderTable(columns, data.rows, row => `
            ${actionButton('查看图片/详情', 'product-detail', row.id)}

            ${row.review_status === 'pending'
                ? `
                        ${actionButton(
                    '通过',
                    'product-approve',
                    row.id,
                    'success'
                )}

                        ${actionButton(
                    '拒绝',
                    'product-reject',
                    row.id,
                    'danger'
                )}
                    `
                : ''
            }

            ${row.status === 'on_sale'
                ? actionButton(
                    '强制下架',
                    'product-off-sale',
                    row.id,
                    'danger'
                )
                : ''
            }
        `));
    }

    async function reviewProduct(product, reviewStatus) {
        const isApproved = reviewStatus === 'approved';

        if (isApproved) {
            if (!window.confirm(
                `确定通过商品「${product.name ?? product.product_name}」的审核吗？`
            )) {
                return;
            }

            await patch(
                `${API.products}/${product.id}/review`,
                {
                    review_status: 'approved',
                    reason: null
                }
            );

            showMessage('商品审核通过');
            await loadModule();

            return;
        }

        openModal({
            title: '拒绝商品审核',
            content: `
                <p>
                    商品：
                    ${escapeHTML(product.name ?? product.product_name)}
                </p>

                <label class="dash-form-label"
                       for="reject-reason">
                    拒绝原因
                </label>

                <textarea
                    id="reject-reason"
                    class="dash-textarea"
                    rows="4"
                    maxlength="500"
                    placeholder="请填写拒绝原因"
                ></textarea>
            `,
            confirmText: '确认拒绝',
            onConfirm: async mask => {
                const reason = mask
                    .querySelector('#reject-reason')
                    .value
                    .trim();

                if (!reason) {
                    showMessage('请填写拒绝原因', 'error');
                    return false;
                }

                await patch(
                    `${API.products}/${product.id}/review`,
                    {
                        review_status: 'rejected',
                        reason
                    }
                );

                showMessage('已拒绝商品审核');

                await loadModule();
            }
        });
    }

    async function forceOffSale(product) {
        if (!window.confirm(
            `确定强制下架商品「${product.name ?? product.product_name}」吗？`
        )) {
            return;
        }

        await patch(
            `${API.products}/${product.id}/status`,
            { status: 'off_sale' }
        );

        showMessage('商品已下架');

        await loadModule();
    }

    /* ==================== 订单管理 ==================== */

    async function loadOrders() {
        const result = await get(
            API.orders + buildQuery({
                page: state.page,
                page_size: state.pageSize,
                order_status: state.status
            })
        );

        const data = normalizeList(result.data, 'orders');

        state.rows = data.rows;
        state.total = data.total;

        setTable(renderTable([
            { title: '订单ID', key: 'id' },
            {
                title: '商品',
                render: row => escapeHTML(
                    row.product?.name ??
                    row.product_name ??
                    row.product_id
                )
            },
            {
                title: '买家',
                render: row => escapeHTML(
                    row.buyer?.username ??
                    row.buyer_username ??
                    row.buyer_id
                )
            },
            {
                title: '金额',
                render: row => formatMoney(
                    row.total_amount ?? row.price ?? row.amount
                )
            },
            {
                title: '状态',
                render: row => statusBadge(row.status)
            },
            {
                title: '创建时间',
                render: row => formatDate(row.created_at)
            }
        ], data.rows, row => `
            ${actionButton('详情', 'order-detail', row.id)}
        `));
    }

    async function showOrderDetail(order) {
        const result = await get(`${API.orders}/${order.id}`);
        const data = result.data ?? order;

        openModal({
            title: `订单详情 #${order.id}`,
            content: detailRows({
                订单ID: data.id,

                订单号: data.order_no ?? '—',

                商品: data.product?.name
                    ?? data.product_name
                    ?? data.product_id
                    ?? '—',

                买家: data.buyer?.username
                    ?? data.buyer_username
                    ?? data.buyer_id
                    ?? '—',

                卖家: data.seller?.username
                    ?? data.seller_username
                    ?? data.seller_id
                    ?? '—',

                订单金额: formatMoney(
                    data.price
                    ?? data.total_amount
                    ?? data.amount
                ),

                订单状态: data.status ?? '—',

                交易地点: data.meeting_location ?? '—',

                交易时间: formatDate(data.meeting_time),

                买家确认交易: data.buyer_meeting_confirmed ? '是' : '否',

                卖家确认交易: data.seller_meeting_confirmed ? '是' : '否',

                创建时间: formatDate(data.created_at),

                收货时间: formatDate(data.received_at),

                完成时间: formatDate(data.completed_at),

                取消时间: formatDate(data.cancelled_at),

                自动确认收货时间: formatDate(data.auto_receive_at)
            })
        });
    }

    /* ==================== 举报管理 ==================== */

    async function loadReports() {
        const result = await get(API.reports);

        const data = normalizeList(result.data, 'reports');

        const keyword = state.keyword.trim().toLowerCase();

        let rows = data.rows.filter(row => {
            const matchesStatus =
                !state.status ||
                row.status === state.status;

            const text = [
                row.id,
                row.reporter?.username,
                row.reporter_username,
                row.reporter_id,
                row.target_type,
                row.target_id,
                row.reason
            ]
                .filter(value => value !== null && value !== undefined)
                .join(' ')
                .toLowerCase();

            const matchesKeyword =
                !keyword || text.includes(keyword);

            return matchesStatus && matchesKeyword;
        });

        state.total = rows.length;

        const startIndex = (state.page - 1) * state.pageSize;
        const pageRows = rows.slice(
            startIndex,
            startIndex + state.pageSize
        );

        state.rows = pageRows;

        setTable(renderTable([
            { title: '举报ID', key: 'id' },
            {
                title: '举报人',
                render: row => escapeHTML(
                    row.reporter?.username ??
                    row.reporter_username ??
                    row.reporter_id
                )
            },
            {
                title: '举报目标',
                render: row => row.target_type === 'product'
                    ? `商品 #${escapeHTML(row.target_id)}`
                    : `用户 #${escapeHTML(row.target_id)}`
            },
            {
                title: '举报原因',
                render: row => escapeHTML(row.reason ?? '—')
            },
            {
                title: '状态',
                render: row => statusBadge(row.status)
            },
            {
                title: '提交时间',
                render: row => formatDate(row.created_at)
            }
        ], pageRows, row => `
            ${actionButton('详情', 'report-detail', row.id)}

            ${row.status === 'pending'
                ? actionButton(
                    '处理',
                    'report-resolve',
                    row.id,
                    'success'
                )
                : ''
            }
        `));
    }

    async function showReportDetail(report) {
        const result = await get(`${API.reports}/${report.id}`);
        const data = result.data ?? report;

        const targetLabel =
            data.target_type === 'product'
                ? `商品 #${data.target?.id ?? data.target_id} ${data.target?.product_name ?? ''}`
                : `用户 #${data.target?.id ?? data.target_id} ${data.target?.username ?? ''}`;

        const reportedUser =
            data.reported_user ??
            data.seller ??
            data.target;

        openModal({
            title: `举报详情 #${report.id}`,
            content: detailRows({
                举报ID: data.id,
                举报人: data.reporter?.username ?? data.reporter_username ?? data.reporter_id,
                举报目标类型: data.target_type === 'product' ? '商品' : '用户',
                举报目标: targetLabel,
                被举报用户: reportedUser
                    ? `${reportedUser.username ?? '—'}（ID: ${reportedUser.id ?? '—'}）`
                    : '—',
                举报原因: data.reason,
                处理状态: data.status,
                处理方式: data.handle_type ?? '—',
                扣除信用分: data.punish_score ?? '—',
                封禁天数: data.ban_days === -1 ? '永久' : (data.ban_days ?? '—'),
                处理备注: data.handle_note ?? '—',
                提交时间: formatDate(data.created_at)
            })
        });
    }

    function showReportHandleModal(report) {
        openModal({
            title: `处理举报 #${report.id}`,
            width: '720px',
            content: `
                <p>
                    举报原因：
                    ${escapeHTML(report.reason ?? '—')}
                </p>

                <label class="dash-form-label"
                       for="report-handle-type">
                    处理方式
                </label>

                <select
                    id="report-handle-type"
                    class="dash-select full"
                >
                    <option value="deduct_score">扣除信用分</option>
                    <option value="ban">封号</option>
                </select>

                <div id="report-punish-score-wrap">
                    <label class="dash-form-label"
                           for="report-punish-score">
                        扣除信用分
                    </label>

                    <input
                        id="report-punish-score"
                        class="dash-input full"
                        type="number"
                        min="1"
                        step="1"
                        placeholder="请输入扣除分数"
                    >
                </div>

                <div id="report-ban-days-wrap" hidden>
                    <label class="dash-form-label"
                           for="report-ban-days">
                        封禁时间
                    </label>

                    <select
                        id="report-ban-days"
                        class="dash-select full"
                    >
                        <option value="1">1天</option>
                        <option value="3">3天</option>
                        <option value="7">7天</option>
                        <option value="15">15天</option>
                        <option value="30">30天</option>
                        <option value="-1">永久封禁</option>
                    </select>
                </div>

                <label class="dash-form-label"
                       for="report-handle-note">
                    处理备注
                </label>

                <textarea
                    id="report-handle-note"
                    class="dash-textarea"
                    rows="4"
                    maxlength="500"
                    placeholder="可填写处理原因或备注"
                ></textarea>

                <div id="report-reject-area"
                     style="margin-top:18px;padding-top:18px;border-top:1px solid #e5e7eb;">
                    <button
                        type="button"
                        class="dash-btn danger"
                        id="report-reject-button"
                    >
                        直接驳回举报
                    </button>
                </div>
            `,
            confirmText: '确认处理',
            onConfirm: async mask => {
                const handleType =
                    mask.querySelector('#report-handle-type').value;

                const handleNote =
                    mask.querySelector('#report-handle-note').value.trim();

                if (handleType === 'deduct_score') {
                    const punishScore = Number(
                        mask.querySelector('#report-punish-score').value
                    );

                    if (!Number.isInteger(punishScore) || punishScore <= 0) {
                        showMessage('请输入大于0的整数信用分', 'error');
                        return false;
                    }

                    await patch(
                        `${API.reports}/${report.id}/handle`,
                        {
                            handle_type: 'deduct_score',
                            punish_score: punishScore,
                            ban_days: null,
                            handle_note: handleNote || null
                        }
                    );
                } else {
                    const banDays = Number(
                        mask.querySelector('#report-ban-days').value
                    );

                    await patch(
                        `${API.reports}/${report.id}/handle`,
                        {
                            handle_type: 'ban',
                            punish_score: null,
                            ban_days: banDays,
                            handle_note: handleNote || null
                        }
                    );
                }

                showMessage('举报处理成功');
                await loadModule();
            }
        });

        const typeSelect = $('#report-handle-type', $('#admin-modal-mask'));
        const scoreWrap = $('#report-punish-score-wrap', $('#admin-modal-mask'));
        const banWrap = $('#report-ban-days-wrap', $('#admin-modal-mask'));
        const rejectButton = $('#report-reject-button', $('#admin-modal-mask'));

        typeSelect?.addEventListener('change', () => {
            const isBan = typeSelect.value === 'ban';

            if (scoreWrap) scoreWrap.hidden = isBan;
            if (banWrap) banWrap.hidden = !isBan;
        });

        rejectButton?.addEventListener('click', async () => {
            if (!window.confirm(`确定驳回举报 #${report.id} 吗？`)) {
                return;
            }

            const handleNote =
                $('#report-handle-note', $('#admin-modal-mask'))?.value.trim() ?? '';

            try {
                await patch(
                    `${API.reports}/${report.id}/status`,
                    {
                        status: 'rejected',
                        handle_note: handleNote || null
                    }
                );

                closeModal();
                showMessage('举报已驳回');
                await loadModule();
            } catch (error) {
                showMessage(error.message, 'error');
            }
        });
    }

    /* ==================== 公告管理 ==================== */

    async function loadAnnouncements() {
        const result = await get(
            API.announcements + buildQuery({
                page: state.page,
                page_size: state.pageSize,
                keyword: state.keyword
            })
        );

        const data = normalizeList(
            result.data,
            'announcements'
        );

        state.rows = data.rows;
        state.total = data.total;

        setTable(renderTable([
            { title: '公告ID', key: 'id' },
            { title: '标题', key: 'title' },
            {
                title: '发布时间',
                render: row => formatDate(row.created_at)
            }
        ], data.rows, row => `
            ${actionButton('查看', 'announcement-detail', row.id)}
            ${actionButton('编辑', 'announcement-edit', row.id)}
            ${actionButton(
            '删除',
            'announcement-delete',
            row.id,
            'danger'
        )}
        `));
    }

    function showAnnouncementModal(announcement = null) {
        const editing = Boolean(announcement);

        openModal({
            title: editing ? '编辑公告' : '发布公告',
            content: `
                <label class="dash-form-label"
                       for="announcement-title">
                    公告标题
                </label>

                <input
                    id="announcement-title"
                    class="dash-input full"
                    maxlength="100"
                    value="${escapeHTML(announcement?.title ?? '')}"
                    placeholder="请输入公告标题"
                >

                <label class="dash-form-label"
                       for="announcement-content">
                    公告内容
                </label>

                <textarea
                    id="announcement-content"
                    class="dash-textarea"
                    rows="8"
                    placeholder="请输入公告内容"
                >${escapeHTML(announcement?.content ?? '')}</textarea>
            `,
            confirmText: editing ? '保存修改' : '发布公告',
            onConfirm: async mask => {
                const title = mask
                    .querySelector('#announcement-title')
                    .value
                    .trim();

                const content = mask
                    .querySelector('#announcement-content')
                    .value
                    .trim();

                if (!title || !content) {
                    showMessage('标题和内容不能为空', 'error');
                    return false;
                }

                if (editing) {
                    await patch(
                        `${API.announcements}/${announcement.id}`,
                        { title, content }
                    );
                } else {
                    await post(API.announcements, {
                        title,
                        content
                    });
                }

                showMessage(editing ? '公告修改成功' : '公告发布成功');

                await loadModule();
            }
        });
    }

    async function deleteAnnouncement(announcement) {
        if (!window.confirm(
            `确定删除公告「${announcement.title}」吗？`
        )) {
            return;
        }

        await del(`${API.announcements}/${announcement.id}`);

        showMessage('公告删除成功');

        await loadModule();
    }

    /* ==================== 管理员管理 ==================== */

    async function loadAdmins() {
        if (state.admin?.role !== 'super_admin') {
            throw new Error('只有超级管理员可以管理管理员账户');
        }

        const result = await get(API.admins);

        const data = normalizeList(result.data, 'admins');

        const keyword = state.keyword.toLowerCase();

        const rows = data.rows.filter(row => {
            const matchesKeyword =
                !keyword ||
                String(row.username ?? '')
                    .toLowerCase()
                    .includes(keyword);

            const matchesStatus =
                !state.status ||
                row.status === state.status;

            return matchesKeyword && matchesStatus;
        });

        state.rows = rows;
        state.total = rows.length;

        setTable(renderTable([
            { title: 'ID', key: 'id' },
            { title: '用户名', key: 'username' },
            {
                title: '角色',
                render: row => statusBadge(row.role)
            },
            {
                title: '状态',
                render: row => statusBadge(row.status)
            },
            {
                title: '最近登录',
                render: row => formatDate(row.last_login_at)
            },
            {
                title: '创建时间',
                render: row => formatDate(row.created_at)
            }
        ], rows, row => `
            ${actionButton('修改角色', 'admin-role', row.id)}

            ${row.status === 'banned'
                ? actionButton(
                    '解封',
                    'admin-unban',
                    row.id,
                    'success'
                )
                : actionButton(
                    '封禁',
                    'admin-ban',
                    row.id,
                    'danger'
                )
            }
        `), false);
    }

    function showCreateAdminModal() {
        openModal({
            title: '创建管理员',
            content: `
                <label class="dash-form-label"
                       for="new-admin-name">
                    用户名
                </label>

                <input
                    id="new-admin-name"
                    class="dash-input full"
                    maxlength="50"
                    autocomplete="off"
                >

                <label class="dash-form-label"
                       for="new-admin-password">
                    密码
                </label>

                <input
                    id="new-admin-password"
                    class="dash-input full"
                    type="password"
                    autocomplete="new-password"
                >

                <label class="dash-form-label"
                       for="new-admin-role">
                    角色
                </label>

                <select
                    id="new-admin-role"
                    class="dash-select full"
                >
                    <option value="admin">普通管理员</option>
                    <option value="super_admin">超级管理员</option>
                </select>
            `,
            confirmText: '创建',
            onConfirm: async mask => {
                const username = mask
                    .querySelector('#new-admin-name')
                    .value
                    .trim();

                const password = mask
                    .querySelector('#new-admin-password')
                    .value;

                const role = mask
                    .querySelector('#new-admin-role')
                    .value;

                if (!username || !password) {
                    showMessage('用户名和密码不能为空', 'error');
                    return false;
                }

                await post(API.admins, {
                    username,
                    password,
                    role
                });

                showMessage('管理员创建成功');

                await loadModule();
            }
        });
    }

    function showAdminRoleModal(admin) {
        openModal({
            title: `修改管理员角色：${admin.username}`,
            content: `
                <label class="dash-form-label"
                       for="edit-admin-role">
                    管理员角色
                </label>

                <select
                    id="edit-admin-role"
                    class="dash-select full"
                >
                    <option
                        value="admin"
                        ${admin.role === 'admin' ? 'selected' : ''}
                    >普通管理员</option>

                    <option
                        value="super_admin"
                        ${admin.role === 'super_admin' ? 'selected' : ''}
                    >超级管理员</option>
                </select>
            `,
            confirmText: '保存',
            onConfirm: async mask => {
                const role = mask
                    .querySelector('#edit-admin-role')
                    .value;

                await patch(
                    `${API.admins}/${admin.id}/role`,
                    { role }
                );

                showMessage('管理员角色修改成功');

                await loadModule();
            }
        });
    }

    async function changeAdminStatus(admin, status) {
        const action = status === 'banned' ? '封禁' : '解封';

        if (!window.confirm(
            `确定${action}管理员「${admin.username}」吗？`
        )) {
            return;
        }

        await patch(
            `${API.admins}/${admin.id}/status`,
            { status }
        );

        showMessage(`管理员${action}成功`);

        await loadModule();
    }

    /* ==================== 表格操作事件 ==================== */

    async function handleModuleAction(event) {
        const button = event.target.closest('[data-action]');

        if (!button || button.disabled) return;

        const { action, id } = button.dataset;

        const row = state.rows.find(
            item => String(item.id) === String(id)
        );

        if (!row) {
            showMessage('没有找到对应数据，请刷新页面', 'error');
            return;
        }

        button.disabled = true;

        try {
            switch (action) {
                case 'user-detail':
                    showUserDetail(row);
                    break;

                case 'user-ban':
                    await changeUserStatus(row, 'banned');
                    break;

                case 'user-unban':
                    await changeUserStatus(row, 'normal');
                    break;

                case 'product-detail':
                    showProductDetail(row);
                    break;

                case 'product-approve':
                    await reviewProduct(row, 'approved');
                    break;

                case 'product-reject':
                    await reviewProduct(row, 'rejected');
                    break;

                case 'product-off-sale':
                    await forceOffSale(row);
                    break;

                case 'order-detail':
                    await showOrderDetail(row);
                    break;

                case 'report-detail':
                    await showReportDetail(row);
                    break;

                case 'report-resolve':
                    showReportHandleModal(row);
                    break;

                case 'announcement-detail':
                    openModal({
                        title: row.title ?? '公告详情',
                        content: `
                            <div class="announcement-content">
                                ${escapeHTML(row.content)}
                            </div>
                        `
                    });
                    break;

                case 'announcement-edit':
                    showAnnouncementModal(row);
                    break;

                case 'announcement-delete':
                    await deleteAnnouncement(row);
                    break;

                case 'admin-role':
                    showAdminRoleModal(row);
                    break;

                case 'admin-ban':
                    await changeAdminStatus(row, 'banned');
                    break;

                case 'admin-unban':
                    await changeAdminStatus(row, 'normal');
                    break;

                default:
                    break;
            }
        } catch (error) {
            showMessage(error.message, 'error');
        } finally {
            if (button.isConnected) {
                button.disabled = false;
            }
        }
    }

    /* ==================== 模块切换 ==================== */

    async function loadModule() {
        const view = state.view;

        if (view === 'overview') {
            await loadOverview();
            return;
        }

        const requestId = ++state.requestId;

        state.loading = true;

        const list = $('#dash-list');

        if (list) {
            list.innerHTML = `
                <div class="dash-empty">正在加载...</div>
            `;
        }

        try {
            switch (view) {
                case 'users':
                    await loadUsers();
                    break;

                case 'products':
                    await loadProducts();
                    break;

                case 'orders':
                    await loadOrders();
                    break;

                case 'reports':
                    await loadReports();
                    break;

                case 'announcements':
                    await loadAnnouncements();
                    break;

                case 'admins':
                    await loadAdmins();
                    break;
            }
        } catch (error) {
            if (requestId !== state.requestId) return;

            const currentList = $('#dash-list');

            if (currentList) {
                currentList.innerHTML = `
                    <div class="dash-empty error">
                        ${escapeHTML(error.message)}
                    </div>
                `;
            }

            showMessage(error.message, 'error');
        } finally {
            if (requestId === state.requestId) {
                state.loading = false;
            }
        }
    }

    async function showView(view) {
        if (!MODULES[view]) return;

        if (
            view === 'admins' &&
            state.admin?.role !== 'super_admin'
        ) {
            showMessage('无权访问管理员管理', 'error');
            return;
        }

        state.view = view;
        state.page = 1;
        state.total = 0;
        state.keyword = '';
        state.status = '';
        state.rows = [];

        // 使旧请求失效
        state.requestId++;

        $$('.nav-item').forEach(button => {
            button.classList.toggle(
                'active',
                button.dataset.view === view
            );
        });

        const overview = $('#overview');
        const moduleView = $('#module-view');

        overview?.classList.toggle(
            'active',
            view === 'overview'
        );

        moduleView?.classList.toggle(
            'active',
            view !== 'overview'
        );

        if (overview) {
            overview.hidden = view !== 'overview';
        }

        if (moduleView) {
            moduleView.hidden = view === 'overview';
        }

        if ($('#page-title')) {
            $('#page-title').textContent =
                MODULES[view].title;
        }

        if (view === 'overview') {
            await loadOverview();
            return;
        }

        if ($('#module-title')) {
            $('#module-title').textContent =
                MODULES[view].title;
        }

        if ($('#module-icon')) {
            $('#module-icon').textContent =
                MODULES[view].icon;
        }

        if ($('#module-description')) {
            $('#module-description').textContent = '';
        }

        let content = $('#dashboard-content');

        if (!content) {
            content = document.createElement('div');
            content.id = 'dashboard-content';

            moduleView.appendChild(content);
        }

        const configs = {
            users: {
                title: '平台用户',
                placeholder: '搜索用户名、邮箱或学号',
                filters: [
                    { value: '', label: '全部状态' },
                    { value: 'normal', label: '正常' },
                    { value: 'banned', label: '已封禁' }
                ]
            },

            products: {
                title: '商品审核',
                placeholder: '搜索商品名称',
                filters: [
                    { value: '', label: '全部审核状态' },
                    { value: 'pending', label: '待审核' },
                    { value: 'approved', label: '已通过' },
                    { value: 'rejected', label: '已拒绝' }
                ]
            },

            orders: {
                title: '平台订单',
                placeholder: '搜索订单',
                filters: [
                    { value: '', label: '全部状态' },
                    { value: 'pending', label: '待处理' },
                    { value: 'received', label: '已收货' },
                    { value: 'completed', label: '已完成' },
                    { value: 'cancelled', label: '已取消' }
                ]
            },

            reports: {
                title: '举报处理',
                placeholder: '搜索举报',
                filters: [
                    { value: '', label: '全部状态' },
                    { value: 'pending', label: '待处理' },
                    { value: 'resolved', label: '已处理' },
                    { value: 'rejected', label: '已驳回' }
                ]
            },

            announcements: {
                title: '公告管理',
                placeholder: '搜索公告标题',
                createLabel: '发布公告'
            },

            admins: {
                title: '管理员账户',
                placeholder: '搜索管理员用户名',
                filters: [
                    { value: '', label: '全部状态' },
                    { value: 'normal', label: '正常' },
                    { value: 'banned', label: '已封禁' }
                ],
                createLabel: '创建管理员'
            }
        };

        renderModuleShell(configs[view]);

        await loadModule();

        if (window.innerWidth <= 768) {
            document.body.classList.remove('sidebar-open');
        }
    }

    /* ==================== 动态样式 ==================== */

    function installStyles() {
        if ($('#admin-dashboard-extra-styles')) return;

        const style = document.createElement('style');

        style.id = 'admin-dashboard-extra-styles';

        style.textContent = `
            [hidden] {
                display: none !important;
            }

            #dashboard-content {
                width: 100%;
                margin-top: 20px;
            }

            .dash-panel {
                background: #fff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 20px;
            }

            .dash-panel-header {
                margin-bottom: 18px;
            }

            .dash-panel-header h3 {
                margin: 0;
                font-size: 19px;
            }

            .dash-toolbar {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }

            .dash-input,
            .dash-select,
            .dash-textarea {
                box-sizing: border-box;
                padding: 10px 12px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background: #fff;
                color: #111827;
                font: inherit;
            }

            .dash-input {
                min-width: 220px;
                flex: 1;
            }

            .dash-input.full,
            .dash-select.full {
                display: block;
                width: 100%;
                margin-bottom: 16px;
            }

            .dash-textarea {
                display: block;
                width: 100%;
                resize: vertical;
                margin-bottom: 16px;
            }

            .dash-form-label {
                display: block;
                font-weight: 600;
                margin: 14px 0 8px;
            }

            .dash-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 5px;
                padding: 9px 14px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background: #fff;
                color: #374151;
                font: inherit;
                cursor: pointer;
                white-space: nowrap;
            }

            .dash-btn.small {
                padding: 6px 10px;
                font-size: 12px;
            }

            .dash-btn.primary {
                color: #fff;
                background: #2563eb;
                border-color: #2563eb;
            }

            .dash-btn.success {
                color: #15803d;
                background: #f0fdf4;
                border-color: #bbf7d0;
            }

            .dash-btn.danger {
                color: #dc2626;
                background: #fef2f2;
                border-color: #fecaca;
            }

            .dash-btn:disabled {
                opacity: .5;
                cursor: not-allowed;
            }

            .dash-table-wrap {
                width: 100%;
                overflow-x: auto;
            }

            .dash-table {
                width: 100%;
                border-collapse: collapse;
                text-align: left;
                font-size: 14px;
            }

            .dash-table th,
            .dash-table td {
                padding: 13px 12px;
                border-bottom: 1px solid #e5e7eb;
                vertical-align: middle;
            }

            .dash-table th {
                background: #f9fafb;
                color: #6b7280;
                font-weight: 600;
                white-space: nowrap;
            }

            .dash-table tbody tr:hover {
                background: #f9fafb;
            }

            .dash-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                min-width: 160px;
            }

            .dash-badge {
                display: inline-block;
                padding: 4px 9px;
                border-radius: 20px;
                font-size: 12px;
                background: #f3f4f6;
                color: #4b5563;
                white-space: nowrap;
            }

            .dash-badge[data-status="approved"],
            .dash-badge[data-status="normal"],
            .dash-badge[data-status="on_sale"],
            .dash-badge[data-status="resolved"] {
                background: #dcfce7;
                color: #166534;
            }

            .dash-badge[data-status="pending"] {
                background: #fef3c7;
                color: #92400e;
            }

            .dash-badge[data-status="rejected"],
            .dash-badge[data-status="banned"],
            .dash-badge[data-status="off_sale"] {
                background: #fee2e2;
                color: #991b1b;
            }

            .dash-pagination {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 20px;
                font-size: 13px;
                color: #6b7280;
            }

            .dash-pagination > div {
                display: flex;
                gap: 8px;
            }

            .dash-empty {
                padding: 45px 20px;
                text-align: center;
                color: #6b7280;
            }

            .dash-empty.error {
                color: #dc2626;
            }

            .admin-stat-grid {
                display: grid;
                grid-template-columns: repeat(
                    auto-fit,
                    minmax(180px, 1fr)
                );
                gap: 16px;
            }

            .admin-stat-card {
                display: flex;
                flex-direction: column;
                gap: 14px;
                padding: 24px;
                background: #fff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }

            .admin-stat-card span {
                color: #6b7280;
            }

            .admin-stat-card strong {
                font-size: 30px;
            }

            /* 商品列表主图 */

            .product-image-button {
                display: block;
                width: 76px;
                height: 76px;
                padding: 0;
                overflow: hidden;
                border: 0;
                border-radius: 9px;
                background: #f3f4f6;
                cursor: pointer;
                color: #9ca3af;
                font-size: 11px;
            }

            .product-thumbnail {
                display: block;
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform .2s;
            }

            .product-image-button:hover .product-thumbnail {
                transform: scale(1.08);
            }

            .product-no-image {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 76px;
                height: 76px;
                border-radius: 9px;
                background: #f3f4f6;
                color: #9ca3af;
                font-size: 12px;
            }

            /* 商品详情全部图片 */

            .product-section-title {
                margin: 0 0 14px;
                font-size: 16px;
            }

            .product-detail-gallery {
                display: grid;
                grid-template-columns: repeat(
                    auto-fill,
                    minmax(135px, 1fr)
                );
                gap: 12px;
                margin-bottom: 28px;
            }

            .product-gallery-item {
                display: block;
                padding: 0;
                overflow: hidden;
                aspect-ratio: 1;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background: #f9fafb;
                cursor: zoom-in;
            }

            .product-gallery-item img {
                display: block;
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform .2s;
            }

            .product-gallery-item:hover img {
                transform: scale(1.05);
            }

            .product-empty-gallery {
                padding: 45px;
                margin-bottom: 25px;
                text-align: center;
                border: 1px dashed #d1d5db;
                border-radius: 10px;
                color: #9ca3af;
            }

            /* 弹窗 */

            .admin-modal-mask {
                position: fixed;
                inset: 0;
                z-index: 9998;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                background: rgba(15, 23, 42, .55);
            }

            .admin-modal {
                width: 100%;
                max-height: 90vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                background: #fff;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,.2);
            }

            .admin-modal-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 18px 22px;
                border-bottom: 1px solid #e5e7eb;
            }

            .admin-modal-header h3 {
                margin: 0;
                font-size: 19px;
            }

            .admin-modal-close {
                border: 0;
                background: transparent;
                color: #6b7280;
                font-size: 28px;
                cursor: pointer;
            }

            .admin-modal-body {
                padding: 22px;
                overflow-y: auto;
            }

            .admin-modal-footer {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 16px 22px;
                border-top: 1px solid #e5e7eb;
            }

            .admin-detail-list {
                display: grid;
                grid-template-columns: 110px minmax(0, 1fr);
                gap: 14px 18px;
                margin: 0;
                font-size: 14px;
            }

            .admin-detail-list dt {
                color: #6b7280;
            }

            .admin-detail-list dd {
                min-width: 0;
                margin: 0;
                color: #111827;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
            }

            .announcement-content {
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                line-height: 1.8;
            }

            /* 全屏图片预览 */

            .product-image-preview {
                position: fixed;
                inset: 0;
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 18px;
                padding: 30px;
                background: rgba(0, 0, 0, .93);
            }

            .preview-close {
                position: absolute;
                top: 18px;
                right: 25px;
                border: 0;
                background: transparent;
                color: white;
                font-size: 38px;
                cursor: pointer;
            }

            .preview-arrow {
                flex-shrink: 0;
                border: 0;
                background: rgba(255,255,255,.15);
                color: white;
                width: 44px;
                height: 56px;
                border-radius: 8px;
                font-size: 36px;
                cursor: pointer;
            }

            .preview-main {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 14px;
                min-width: 0;
            }

            .preview-main img {
                display: block;
                max-width: min(80vw, 1100px);
                max-height: 75vh;
                object-fit: contain;
            }

            .preview-counter {
                color: #fff;
            }

            .preview-original {
                color: #93c5fd;
                text-decoration: none;
            }

            /* 提示消息 */

            #admin-toast-container {
                position: fixed;
                z-index: 11000;
                top: 22px;
                right: 22px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .admin-toast {
                padding: 12px 18px;
                border-radius: 9px;
                background: #15803d;
                color: #fff;
                box-shadow: 0 8px 25px rgba(0,0,0,.15);
            }

            .admin-toast.error {
                background: #dc2626;
            }

            @media (max-width: 768px) {
                .dash-panel {
                    padding: 14px;
                }

                .dash-input,
                .dash-select {
                    width: 100%;
                    min-width: 0;
                }

                .admin-modal-mask {
                    padding: 10px;
                }

                .admin-modal-body {
                    padding: 16px;
                }

                .product-detail-gallery {
                    grid-template-columns: repeat(2, 1fr);
                }

                .product-image-preview {
                    gap: 5px;
                    padding: 10px;
                }

                .preview-arrow {
                    width: 30px;
                    height: 45px;
                    font-size: 25px;
                }

                .preview-main img {
                    max-width: 75vw;
                }
            }
        `;

        document.head.appendChild(style);
    }

    /* ==================== 初始化 ==================== */

    async function init() {
        installStyles();

        $('#logout')?.addEventListener('click', logout);

        $('#menu-toggle')?.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-open');
        });

        $('#overlay')?.addEventListener('click', () => {
            document.body.classList.remove('sidebar-open');
        });

        $$('.nav-item[data-view]').forEach(button => {
            button.addEventListener('click', () => {
                showView(button.dataset.view);
            });
        });

        $$('[data-jump]').forEach(button => {
            button.addEventListener('click', () => {
                showView(button.dataset.jump);
            });
        });

        const verified = await verifyAdmin();

        if (!verified) return;

        await showView('overview');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
