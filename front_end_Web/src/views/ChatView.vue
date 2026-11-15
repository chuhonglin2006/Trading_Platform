<template>
  <div class="chat-page">
    <!-- 顶部 -->
    <header class="chat-header">
      <button class="back-btn" @click="goBack">
        ←
      </button>

      <div class="header-info">
        <div class="title">
          {{ otherUserName || '聊天' }}
        </div>

        <div class="connection-status">
          <span
            class="status-dot"
            :class="{
              connected: wsConnected,
              connecting: wsConnecting,
              disconnected: !wsConnected && !wsConnecting
            }"
          ></span>

          <span v-if="wsConnected">实时连接</span>
          <span v-else-if="wsConnecting">连接中...</span>
          <span v-else>连接断开</span>
        </div>
      </div>

      <button
        class="refresh-btn"
        :disabled="loading"
        @click="loadMessages(true)"
      >
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </header>

    <!-- 消息区域 -->
    <main
      ref="messageContainer"
      class="message-container"
      @scroll="handleScroll"
    >
      <!-- 加载 -->
      <div v-if="loadingMore" class="loading">加载更早消息...</div>
      <div v-if="loading && messages.length === 0" class="loading">
        正在加载消息...
      </div>

      <!-- 没有消息 -->
      <div
        v-else-if="!loading && messages.length === 0"
        class="empty"
      >
        暂无消息
      </div>

      <!-- 消息 -->
      <div v-else class="message-list">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-wrapper"
          :class="{
            mine: isMyMessage(message),
            other: !isMyMessage(message)
          }"
        >
          <!-- 对方头像 -->
          <div
            v-if="!isMyMessage(message)"
            class="avatar"
          >
            {{ getAvatarText(message) }}
          </div>

          <div class="message-content">
            <!-- 时间 -->
            <div
              v-if="shouldShowTime(message)"
              class="message-time"
            >
              {{ formatMessageTime(message.created_at) }}
            </div>

            <!-- 气泡 -->
            <div
              class="message-bubble"
              :class="{
                'my-bubble': isMyMessage(message),
                'other-bubble': !isMyMessage(message)
              }"
            >
              {{ message.content }}
            </div>

            <!-- 自己消息的已读状态 -->
            <div
              v-if="isMyMessage(message)"
              class="read-status"
            >
              <span
                :class="{
                  read: message.is_read,
                  unread: !message.is_read
                }"
              >
                {{ message.is_read ? '已读' : '未读' }}
              </span>
            </div>
          </div>

          <!-- 自己头像 -->
          <div
            v-if="isMyMessage(message)"
            class="avatar my-avatar"
          >
            {{ currentUserName ? currentUserName.charAt(0) : '我' }}
          </div>
        </div>
      </div>

      <!-- 滚到底部按钮 -->
      <button
        v-if="showScrollBottom"
        class="scroll-bottom-btn"
        @click="scrollToBottom(true)"
      >
        ↓
      </button>
    </main>

    <!-- 连接提示 -->
    <div
      v-if="!wsConnected"
      class="connection-tip"
      :class="{ connecting: wsConnecting }"
    >
      <span v-if="wsConnecting">
        正在连接聊天服务器...
      </span>

      <span v-else-if="reconnectExhausted">
        聊天连接失败，请检查服务器 WebSocket 配置。
      </span>

      <span v-else>
        聊天连接已断开，正在重新连接...
      </span>

      <button
        v-if="reconnectExhausted"
        class="connection-retry"
        type="button"
        @click="reconnectNow"
      >
        重新连接
      </button>
    </div>

    <!-- 输入区域 -->
    <footer class="input-area">
      <textarea
        ref="textareaRef"
        v-model="inputMessage"
        class="message-input"
        placeholder="输入消息..."
        rows="1"
        :disabled="sending"
        @keydown="handleInputKeydown"
        @input="autoResizeTextarea"
      ></textarea>

      <button
        class="send-btn"
        :disabled="
          sending ||
          !inputMessage.trim() ||
          !wsConnected
        "
        @click="sendMessage"
      >
        <span v-if="sending">发送中...</span>
        <span v-else>发送</span>
      </button>
    </footer>
  </div>
</template>

<script setup>
import {
  ref,
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  watch
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { chatApi } from '../api/chat'

const route = useRoute()
const router = useRouter()

/*
|--------------------------------------------------------------------------
| 基础状态
|--------------------------------------------------------------------------
*/

const messages = ref([])
const hasMore = ref(false)
const loadingMore = ref(false)

const loading = ref(false)
const sending = ref(false)

const inputMessage = ref('')

const messageContainer = ref(null)
const textareaRef = ref(null)

const showScrollBottom = ref(false)

/*
|--------------------------------------------------------------------------
| 当前用户
|--------------------------------------------------------------------------
*/

const currentUser = ref(null)

const currentUserId = computed(() => {
  if (!currentUser.value) {
    return null
  }

  return Number(currentUser.value.id)
})

const currentUserName = computed(() => {
  return currentUser.value?.username || ''
})

/*
|--------------------------------------------------------------------------
| 会话 ID
|--------------------------------------------------------------------------
*/

const conversationId = computed(() => {
  const value =
    route.params.id ||
    route.params.conversationId ||
    route.params.conversation_id ||
    route.query.id ||
    route.query.conversationId ||
    route.query.conversation_id

  const id = Number(value)

  return Number.isFinite(id) && id > 0
    ? id
    : null
})

/*
|--------------------------------------------------------------------------
| 对方用户
|--------------------------------------------------------------------------
*/

const otherUserName = ref('')

/*
|--------------------------------------------------------------------------
| WebSocket
|--------------------------------------------------------------------------
*/

const socket = ref(null)

const wsConnected = ref(false)
const wsConnecting = ref(false)
const reconnectExhausted = ref(false)

let reconnectTimer = null
let heartbeatTimer = null

let reconnectAttempts = 0

const MAX_RECONNECT_DELAY = 30000
const MAX_RECONNECT_ATTEMPTS = 5

/*
|--------------------------------------------------------------------------
| 防止重复发送
|--------------------------------------------------------------------------
|
| WebSocket 发送成功后，真正的消息会由服务器广播回来。
| 所以这里不直接把消息塞进 messages。
|
| 等服务器广播回来后再加入消息列表。
|--------------------------------------------------------------------------
*/

const pendingSend = ref(null)

/*
|--------------------------------------------------------------------------
| 初始化当前用户
|--------------------------------------------------------------------------
*/

function loadCurrentUser() {
  try {
    const userString = localStorage.getItem('cm_user')

    if (!userString) {
      currentUser.value = null
      return
    }

    currentUser.value = JSON.parse(userString)
  } catch (error) {
    console.error('读取用户信息失败:', error)
    currentUser.value = null
  }
}

/*
|--------------------------------------------------------------------------
| 判断是不是自己的消息
|--------------------------------------------------------------------------
*/

function isMyMessage(message) {
  if (!message || currentUserId.value === null) {
    return false
  }

  return Number(message.sender_id) === currentUserId.value
}

/*
|--------------------------------------------------------------------------
| 获取头像文字
|--------------------------------------------------------------------------
*/

function getAvatarText(message) {
  if (message?.sender_name) {
    return message.sender_name.charAt(0)
  }

  return '对方'
}

/*
|--------------------------------------------------------------------------
| 获取 Token
|--------------------------------------------------------------------------
*/

function getToken() {
  return localStorage.getItem('cm_token') || ''
}

/*
|--------------------------------------------------------------------------
| 创建 WebSocket 地址
|--------------------------------------------------------------------------
*/

function getWebSocketUrl() {
  const token = getToken()

  if (!token) {
    return null
  }

  const protocol =
    window.location.protocol === 'https:'
      ? 'wss:'
      : 'ws:'

  return `${protocol}//${window.location.host}/api/chat/ws/${conversationId.value}`
}

/*
|--------------------------------------------------------------------------
| 建立 WebSocket
|--------------------------------------------------------------------------
*/

function connectWebSocket() {
  /*
   * 没有会话 ID，不连接
   */
  if (!conversationId.value) {
    return
  }

  /*
   * 没有 Token，不连接
   */
  const token = getToken()

  if (!token) {
    console.warn('没有登录 Token，无法连接聊天 WebSocket')
    return
  }

  /*
   * 已经连接
   */
  if (
    socket.value &&
    socket.value.readyState === WebSocket.OPEN
  ) {
    return
  }

  /*
   * 正在连接
   */
  if (
    socket.value &&
    socket.value.readyState === WebSocket.CONNECTING
  ) {
    return
  }

  clearReconnectTimer()

  wsConnecting.value = true
  wsConnected.value = false

  const url = getWebSocketUrl()

  if (!url) {
    wsConnecting.value = false
    return
  }

  console.log('正在连接 WebSocket:', url)

  try {
    const ws = new WebSocket(url)

    socket.value = ws

    /*
    |--------------------------------------------------------------------------
    | WebSocket 连接成功
    |--------------------------------------------------------------------------
    */

    ws.onopen = () => {
      console.log('WebSocket 连接成功')

      wsConnecting.value = true

      /*
       * 第一条消息必须进行认证
       */
      ws.send(
        JSON.stringify({
          type: 'auth',
          token
        })
      )
    }

    /*
    |--------------------------------------------------------------------------
    | 接收服务器消息
    |--------------------------------------------------------------------------
    */

    ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data)

        console.log('WebSocket 收到消息:', data)

        handleSocketMessage(data)
      } catch (error) {
        console.error(
          '解析 WebSocket 消息失败:',
          error
        )
      }
    }

    /*
    |--------------------------------------------------------------------------
    | WebSocket 错误
    |--------------------------------------------------------------------------
    */

    ws.onerror = error => {
      console.error('WebSocket 错误:', error)

      wsConnected.value = false
      wsConnecting.value = false
    }

    /*
    |--------------------------------------------------------------------------
    | WebSocket 关闭
    |--------------------------------------------------------------------------
    */

    ws.onclose = event => {
      console.log(
        'WebSocket 已关闭:',
        event.code,
        event.reason
      )

      wsConnected.value = false
      wsConnecting.value = false

      stopHeartbeat()

      if (socket.value === ws) {
        socket.value = null
      }

      /*
       * 非正常关闭才自动重连
       */
      if (event.code !== 1000) {
        scheduleReconnect()
      }
    }
  } catch (error) {
    console.error(
      '创建 WebSocket 失败:',
      error
    )

    wsConnected.value = false
    wsConnecting.value = false

    scheduleReconnect()
  }
}

/*
|--------------------------------------------------------------------------
| 处理 WebSocket 消息
|--------------------------------------------------------------------------
*/

function handleSocketMessage(data) {
  if (!data || typeof data !== 'object') {
    return
  }

  /*
  |--------------------------------------------------------------------------
  | 认证成功
  |--------------------------------------------------------------------------
  */

  if (data.type === 'auth_success') {
    console.log(
      'WebSocket 认证成功，用户:',
      data.user_id
    )

    wsConnected.value = true
    wsConnecting.value = false
    reconnectExhausted.value = false

    reconnectAttempts = 0

    startHeartbeat()

    /*
     * 认证成功后重新加载一次历史消息
     */
    void loadMessages(false)

    return
  }

  /*
  |--------------------------------------------------------------------------
  | 新消息
  |--------------------------------------------------------------------------
  */

  if (data.type === 'message') {
    const message = data.data

    if (!message) {
      return
    }

    /*
     * 如果是自己发送的消息，
     * 清除发送中的状态
     */
    if (
      pendingSend.value &&
      Number(message.sender_id) === currentUserId.value &&
      message.content === pendingSend.value.content
    ) {
      resetPendingSend()
    }

    /*
     * 加入消息列表
     */
    void appendMessage(message)

    return
  }

  /*
  |--------------------------------------------------------------------------
  | 已读通知
  |--------------------------------------------------------------------------
  |
  | 后端发送：
  |
  | {
  |   type: "read",
  |   data: {
  |     message_ids: [19],
  |     reader_id: 3
  |   }
  | }
  |
  | 这里收到之后，把自己发送的消息改成已读。
  |--------------------------------------------------------------------------
  */

  if (data.type === 'read') {
    const messageIds =
      data.data?.message_ids || []

    const readIds = new Set(
      messageIds.map(id => Number(id))
    )

    messages.value.forEach(message => {
      if (
        isMyMessage(message) &&
        readIds.has(Number(message.id))
      ) {
        message.is_read = true
      }
    })

    return
  }

  /*
  |--------------------------------------------------------------------------
  | 心跳
  |--------------------------------------------------------------------------
  */

  if (data.type === 'pong') {
    return
  }

  /*
  |--------------------------------------------------------------------------
  | 后端错误
  |--------------------------------------------------------------------------
  */

  if (data.type === 'error') {
    console.error(
      'WebSocket 服务端错误:',
      data.message
    )

    /*
     * 如果正在发送，恢复发送按钮
     */
    if (sending.value) {
      sending.value = false
      pendingSend.value = null
    }

    return
  }
}

/*
|--------------------------------------------------------------------------
| 启动心跳
|--------------------------------------------------------------------------
*/

function startHeartbeat() {
  stopHeartbeat()

  heartbeatTimer = setInterval(() => {
    if (
      socket.value &&
      socket.value.readyState === WebSocket.OPEN
    ) {
      socket.value.send(
        JSON.stringify({
          type: 'ping'
        })
      )
    }
  }, 25000)
}

/*
|--------------------------------------------------------------------------
| 停止心跳
|--------------------------------------------------------------------------
*/

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

/*
|--------------------------------------------------------------------------
| 自动重连
|--------------------------------------------------------------------------
*/

function scheduleReconnect() {
  if (reconnectTimer) {
    return
  }

  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    wsConnecting.value = false
    reconnectExhausted.value = true
    return
  }

  /*
   * 指数退避
   *
   * 1s
   * 2s
   * 4s
   * 8s
   * 16s
   * 30s
   */
  const delay = Math.min(
    1000 * Math.pow(2, reconnectAttempts),
    MAX_RECONNECT_DELAY
  )

  reconnectAttempts++

  console.log(
    `${delay}ms 后重新连接 WebSocket`
  )

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null

    connectWebSocket()
  }, delay)
}

function reconnectNow() {
  clearReconnectTimer()
  reconnectAttempts = 0
  reconnectExhausted.value = false
  connectWebSocket()
}

/*
|--------------------------------------------------------------------------
| 清理重连定时器
|--------------------------------------------------------------------------
*/

function clearReconnectTimer() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

/*
|--------------------------------------------------------------------------
| 关闭 WebSocket
|--------------------------------------------------------------------------
*/

function closeWebSocket() {
  clearReconnectTimer()
  stopHeartbeat()

  if (socket.value) {
    try {
      socket.value.close(1000, '页面关闭')
    } catch (error) {
      console.error(
        '关闭 WebSocket 失败:',
        error
      )
    }
  }

  socket.value = null

  wsConnected.value = false
  wsConnecting.value = false
}

/*
|--------------------------------------------------------------------------
| 加载历史消息
|--------------------------------------------------------------------------
*/

async function loadMessages(scrollToEnd = false) {
  if (!conversationId.value) {
    return
  }

  try {
    loading.value = true

    const result =
      await chatApi.getMessages(
        conversationId.value
      )

    /*
     * 兼容：
     *
     * {
     *   code: 200,
     *   data: [...]
     * }
     *
     * 或
     *
     * {
     *   data: {
     *      messages: [...]
     *   }
     * }
     */
    let list = []

    if (Array.isArray(result?.data)) {
      list = result.data
    } else if (
      Array.isArray(result?.data?.messages)
    ) {
      list = result.data.messages
    } else if (
      Array.isArray(result)
    ) {
      list = result
    }

    messages.value = normalizeMessages(list)
    hasMore.value = Boolean(result?.has_more)

    /*
     * 获取对方名字
     */
    updateOtherUserName()

    /*
     * 下一帧滚到底部
     */
    await nextTick()

    if (
      scrollToEnd ||
      messages.value.length > 0
    ) {
      scrollToBottom(false)
    }

    /*
     * 把对方发来的未读消息标记为已读
     */
    await markMessagesRead()

  } catch (error) {
    console.error(
      '加载聊天记录失败:',
      error
    )
  } finally {
    loading.value = false
  }
}

async function loadOlderMessages() {
  if (loadingMore.value || !hasMore.value || !conversationId.value) return

  // 只取已保存到数据库的消息 id，跳过发送中的临时消息
  const oldest = messages.value.find(m => Number.isInteger(m.id))
  if (!oldest) return

  const container = messageContainer.value
  loadingMore.value = true

  try {
    const result = await chatApi.getMessages(conversationId.value, {
      before_id: oldest.id,
      limit: 50,
    })
    const list = Array.isArray(result?.data) ? result.data : []
    hasMore.value = Boolean(result?.has_more)

    const older = normalizeMessages(list)
    const existing = new Set(messages.value.map(m => m.id))
    const fresh = older.filter(m => !existing.has(m.id))

    // 记录当前滚动位置，加载后保持视线不跳动
    const prevHeight = container?.scrollHeight || 0
    const prevTop = container?.scrollTop || 0

    messages.value = [...fresh, ...messages.value]

    await nextTick()
    if (container) {
      container.style.scrollBehavior = 'auto'   // 关掉平滑滚动，否则会"滑"一下
      container.scrollTop = container.scrollHeight - prevHeight + prevTop
      container.style.scrollBehavior = ''
    }
  } catch (error) {
    console.error('加载更早消息失败:', error)
  } finally {
    loadingMore.value = false
  }
}

/*
|--------------------------------------------------------------------------
| 标准化消息
|--------------------------------------------------------------------------
*/

function normalizeMessages(list) {
  if (!Array.isArray(list)) {
    return []
  }

  /*
   * 去重
   */
  const map = new Map()

  list.forEach(message => {
    if (!message || message.id == null) {
      return
    }

    map.set(
      Number(message.id),
      {
        ...message,
        id: Number(message.id),
        conversation_id:
          Number(message.conversation_id),
        sender_id:
          Number(message.sender_id),
        is_read:
          Boolean(message.is_read)
      }
    )
  })

  return Array.from(map.values()).sort(
    (a, b) =>
      new Date(a.created_at).getTime() -
      new Date(b.created_at).getTime()
  )
}

/*
|--------------------------------------------------------------------------
| 更新对方名称
|--------------------------------------------------------------------------
*/

function updateOtherUserName() {
  /*
   * 如果后端消息里面带 sender_name，
   * 可以直接拿第一条对方消息。
   */
  const otherMessage =
    messages.value.find(
      message =>
        !isMyMessage(message) &&
        message.sender_name
    )

  if (otherMessage?.sender_name) {
    otherUserName.value =
      otherMessage.sender_name
  }
}

/*
|--------------------------------------------------------------------------
| 添加实时消息
|--------------------------------------------------------------------------
*/

async function appendMessage(message) {
  if (!message || message.id == null) {
    return
  }

  const messageId = Number(message.id)

  /*
   * 已经存在，不重复添加
   */
  const exists = messages.value.some(
    item => Number(item.id) === messageId
  )

  if (exists) {
    /*
     * 如果服务器广播的消息包含更新后的状态，
     * 同步一下。
     */
    const index =
      messages.value.findIndex(
        item =>
          Number(item.id) === messageId
      )

    if (index !== -1) {
      messages.value[index] = {
        ...messages.value[index],
        ...message
      }
    }

    return
  }

  messages.value.push({
    ...message,
    id: messageId,
    conversation_id:
      Number(message.conversation_id),
    sender_id:
      Number(message.sender_id),
    is_read:
      Boolean(message.is_read)
  })

  /*
   * 保证按照时间排序
   */
  messages.value.sort(
    (a, b) =>
      new Date(a.created_at).getTime() -
      new Date(b.created_at).getTime()
  )

  await nextTick()

  /*
   * 如果用户当前就在底部附近，
   * 新消息自动滚到底部。
   */
  if (!showScrollBottom.value) {
    scrollToBottom(true)
  }

  /*
   * 如果是对方发来的消息，
   * 自动标记已读。
   */
  if (!isMyMessage(message)) {
    await markMessageRead(message)
  }
}

/*
|--------------------------------------------------------------------------
| 标记单条消息已读
|--------------------------------------------------------------------------
*/

async function markMessageRead(message) {
  if (!message) {
    return
  }

  /*
   * 自己发送的消息不能标记
   */
  if (isMyMessage(message)) {
    return
  }

  /*
   * 已经读过了，不重复请求
   */
  if (message.is_read) {
    return
  }

  try {
    const result =
      await chatApi.readMessage(
        message.id
      )

    if (result?.code === 200) {
      message.is_read = true
    }
  } catch (error) {
    console.error(
      '标记消息已读失败:',
      error
    )
  }
}

/*
|--------------------------------------------------------------------------
| 标记所有对方未读消息
|--------------------------------------------------------------------------
*/

async function markMessagesRead() {
  const unreadMessages =
    messages.value.filter(
      message =>
        !isMyMessage(message) &&
        !message.is_read
    )

  if (
    unreadMessages.length === 0
  ) {
    return
  }

  /*
   * 当前后端接口是一条消息一个请求，
   * 所以这里逐条调用。
   */
  for (const message of unreadMessages) {
    try {
      const result =
        await chatApi.readMessage(
          message.id
        )

      if (result?.code === 200) {
        message.is_read = true
      }
    } catch (error) {
      console.error(
        `消息 ${message.id} 标记已读失败:`,
        error
      )
    }
  }
}

/*
|--------------------------------------------------------------------------
| 发送消息
|--------------------------------------------------------------------------
*/

async function sendMessage() {
  const content =
    inputMessage.value.trim()

  if (!content) {
    return
  }

  /*
   * WebSocket 没连接不能发送
   */
  if (
    !socket.value ||
    socket.value.readyState !==
      WebSocket.OPEN
  ) {
    console.warn(
      'WebSocket 尚未连接'
    )

    return
  }

  if (sending.value) {
    return
  }

  try {
    sending.value = true

    pendingSend.value = {
      content
    }

    /*
     * 发送给后端
     */
    socket.value.send(
      JSON.stringify({
        type: 'message',
        content
      })
    )

    /*
     * 立即清空输入框
     *
     * 真正的消息会等待服务器广播回来。
     */
    inputMessage.value = ''

    await nextTick()

    resetTextarea()

  } catch (error) {
    console.error(
      '发送消息失败:',
      error
    )

    sending.value = false
    pendingSend.value = null
  }
}

/*
|--------------------------------------------------------------------------
| 发送确认后恢复状态
|--------------------------------------------------------------------------
*/

function resetPendingSend() {
  pendingSend.value = null
  sending.value = false
}

/*
|--------------------------------------------------------------------------
| Enter 发送
|--------------------------------------------------------------------------
|
| Enter = 发送
| Shift + Enter = 换行
|--------------------------------------------------------------------------
*/

function handleInputKeydown(event) {
  if (
    event.key === 'Enter' &&
    !event.shiftKey
  ) {
    event.preventDefault()

    void sendMessage()
  }
}

/*
|--------------------------------------------------------------------------
| 自动调整 textarea 高度
|--------------------------------------------------------------------------
*/

function autoResizeTextarea() {
  const textarea = textareaRef.value

  if (!textarea) {
    return
  }

  textarea.style.height = 'auto'

  const maxHeight = 120

  textarea.style.height =
    Math.min(
      textarea.scrollHeight,
      maxHeight
    ) + 'px'
}

/*
|--------------------------------------------------------------------------
| 重置 textarea
|--------------------------------------------------------------------------
*/

function resetTextarea() {
  const textarea = textareaRef.value

  if (!textarea) {
    return
  }

  textarea.style.height = 'auto'
}

/*
|--------------------------------------------------------------------------
| 滚动到底部
|--------------------------------------------------------------------------
*/

function scrollToBottom(smooth = true) {
  const container =
    messageContainer.value

  if (!container) {
    return
  }

  container.scrollTo({
    top: container.scrollHeight,
    behavior: smooth
      ? 'smooth'
      : 'auto'
  })

  showScrollBottom.value = false
}

/*
|--------------------------------------------------------------------------
| 监听滚动
|--------------------------------------------------------------------------
*/

function handleScroll() {
  const container =
    messageContainer.value

  if (!container) {
    return
  }

  const distance =
    container.scrollHeight -
    container.scrollTop -
    container.clientHeight

  showScrollBottom.value =
    distance > 200

      // 滚到顶部附近，加载更早的消息
      if (container.scrollTop < 60) {
        loadOlderMessages()
      }
}

/*
|--------------------------------------------------------------------------
| 判断是否显示时间
|--------------------------------------------------------------------------
*/

function shouldShowTime(message) {
  const index =
    messages.value.findIndex(
      item =>
        Number(item.id) ===
        Number(message.id)
    )

  if (index <= 0) {
    return true
  }

  const previous =
    messages.value[index - 1]

  const currentTime =
    new Date(
      message.created_at
    ).getTime()

  const previousTime =
    new Date(
      previous.created_at
    ).getTime()

  /*
   * 相邻消息超过 5 分钟才显示时间
   */
  return (
    currentTime -
      previousTime >
    5 * 60 * 1000
  )
}

/*
|--------------------------------------------------------------------------
| 时间格式化
|--------------------------------------------------------------------------
*/

function formatMessageTime(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()

  const isToday =
    date.getFullYear() ===
      now.getFullYear() &&
    date.getMonth() ===
      now.getMonth() &&
    date.getDate() ===
      now.getDate()

  if (isToday) {
    return date.toLocaleTimeString(
      'zh-CN',
      {
        hour: '2-digit',
        minute: '2-digit'
      }
    )
  }

  return date.toLocaleString(
    'zh-CN',
    {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }
  )
}

/*
|--------------------------------------------------------------------------
| 返回上一页
|--------------------------------------------------------------------------
*/

function goBack() {
  router.back()
}

/*
|--------------------------------------------------------------------------
| 路由变化
|--------------------------------------------------------------------------
*/

watch(
  () => conversationId.value,
  async (
    newId,
    oldId
  ) => {
    if (!newId || newId === oldId) {
      return
    }

    /*
     * 关闭旧连接
     */
    closeWebSocket()

    /*
     * 清空当前消息
     */
    messages.value = []

    otherUserName.value = ''

    pendingSend.value = null
    sending.value = false

    /*
     * 加载新会话
     */
    await loadMessages(true)

    /*
     * 建立新连接
     */
    connectWebSocket()
  }
)

/*
|--------------------------------------------------------------------------
| 页面初始化
|--------------------------------------------------------------------------
*/

onMounted(async () => {
  loadCurrentUser()

  if (!conversationId.value) {
    console.warn(
      '没有获取到 conversationId'
    )

    return
  }

  /*
   * 先加载历史消息
   */
  await loadMessages(true)

  /*
   * 再建立 WebSocket
   */
  connectWebSocket()
})

/*
|--------------------------------------------------------------------------
| 页面销毁
|--------------------------------------------------------------------------
*/

onUnmounted(() => {
  closeWebSocket()

  pendingSend.value = null
})
</script>

<style scoped>
.chat-page {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  overflow: hidden;
}

/*
|--------------------------------------------------------------------------
| Header
|--------------------------------------------------------------------------
*/

.chat-header {
  flex-shrink: 0;
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8e8;
  box-sizing: border-box;
}

.back-btn,
.refresh-btn {
  border: none;
  background: transparent;
  cursor: pointer;
}

.back-btn {
  width: 40px;
  height: 40px;
  font-size: 25px;
  color: #333;
}

.refresh-btn {
  margin-left: auto;
  padding: 8px 12px;
  color: #666;
  font-size: 14px;
}

.refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.header-info {
  margin-left: 4px;
}

.title {
  font-size: 17px;
  font-weight: 600;
  color: #222;
}

.connection-status {
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #999;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #999;
}

.status-dot.connected {
  background: #52c41a;
}

.status-dot.connecting {
  background: #faad14;
}

.status-dot.disconnected {
  background: #999;
}

/*
|--------------------------------------------------------------------------
| Message container
|--------------------------------------------------------------------------
*/

.message-container {
  position: relative;
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  box-sizing: border-box;
  scroll-behavior: smooth;
}

.message-list {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

/*
|--------------------------------------------------------------------------
| Loading / Empty
|--------------------------------------------------------------------------
*/

.loading,
.empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100px;
  color: #999;
  font-size: 14px;
}

/*
|--------------------------------------------------------------------------
| Message
|--------------------------------------------------------------------------
*/

.message-wrapper {
  display: flex;
  width: 100%;
  margin-bottom: 14px;
  box-sizing: border-box;
}

.message-wrapper.mine {
  justify-content: flex-end;
}

.message-wrapper.other {
  justify-content: flex-start;
}

.message-content {
  max-width: min(70%, 600px);
}

.avatar {
  width: 38px;
  height: 38px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: #e6e6e6;
  color: #555;

  font-size: 14px;
  font-weight: 500;
}

.other .avatar {
  margin-right: 9px;
}

.my-avatar {
  margin-left: 9px;
  background: #409eff;
  color: #ffffff;
}

/*
|--------------------------------------------------------------------------
| Time
|--------------------------------------------------------------------------
*/

.message-time {
  margin: 4px 0 8px;
  text-align: center;
  color: #aaa;
  font-size: 11px;
}

/*
|--------------------------------------------------------------------------
| Bubble
|--------------------------------------------------------------------------
*/

.message-bubble {
  padding: 10px 13px;
  border-radius: 8px;

  font-size: 14px;
  line-height: 1.5;

  word-break: break-word;
  white-space: pre-wrap;
}

.my-bubble {
  background: #95ec69;
  color: #222;
  border-top-right-radius: 3px;
}

.other-bubble {
  background: #ffffff;
  color: #222;
  border-top-left-radius: 3px;
}

/*
|--------------------------------------------------------------------------
| Read status
|--------------------------------------------------------------------------
*/

.read-status {
  margin-top: 3px;
  font-size: 10px;
  text-align: right;
}

.read-status .read {
  color: #999;
}

.read-status .unread {
  color: #bbb;
}

/*
|--------------------------------------------------------------------------
| Scroll bottom
|--------------------------------------------------------------------------
*/

.scroll-bottom-btn {
  position: fixed;
  right: 20px;
  bottom: 95px;

  width: 38px;
  height: 38px;

  border: none;
  border-radius: 50%;

  background: #ffffff;
  color: #555;

  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);

  cursor: pointer;

  font-size: 20px;
}

/*
|--------------------------------------------------------------------------
| Connection tip
|--------------------------------------------------------------------------
*/

.connection-tip {
  flex-shrink: 0;

  padding: 6px 12px;

  text-align: center;

  background: #fff1f0;
  color: #f5222d;

  font-size: 12px;
}

.connection-tip.connecting {
  background: #fffbe6;
  color: #d48806;
}

.connection-retry {
  margin-left: 8px;
  padding: 3px 8px;
  border: 1px solid currentColor;
  border-radius: 5px;
  background: transparent;
  color: inherit;
  font-size: 12px;
}

/*
|--------------------------------------------------------------------------
| Input
|--------------------------------------------------------------------------
*/

.input-area {
  flex-shrink: 0;

  display: flex;
  align-items: flex-end;
  gap: 10px;

  padding: 10px 12px;

  background: #ffffff;
  border-top: 1px solid #e8e8e8;

  box-sizing: border-box;
}

.message-input {
  flex: 1;

  min-height: 40px;
  max-height: 120px;

  padding: 10px 12px;

  border: 1px solid #ddd;
  border-radius: 8px;

  outline: none;

  resize: none;

  font-size: 14px;
  line-height: 20px;

  font-family: inherit;

  box-sizing: border-box;
}

.message-input:focus {
  border-color: #409eff;
}

.message-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-btn {
  flex-shrink: 0;

  width: 70px;
  height: 40px;

  border: none;
  border-radius: 8px;

  background: #409eff;
  color: #ffffff;

  cursor: pointer;

  font-size: 14px;
}

.send-btn:hover:not(:disabled) {
  background: #66b1ff;
}

.send-btn:disabled {
  background: #bfbfbf;
  cursor: not-allowed;
}

/*
|--------------------------------------------------------------------------
| Mobile
|--------------------------------------------------------------------------
*/

@media (max-width: 600px) {
  .chat-header {
    height: 54px;
    padding: 0 10px;
  }

  .message-container {
    padding: 12px 8px;
  }

  .message-content {
    max-width: 78%;
  }

  .avatar {
    width: 34px;
    height: 34px;
  }

  .message-bubble {
    padding: 9px 11px;
    font-size: 14px;
  }

  .input-area {
    padding: 8px;
  }

  .send-btn {
    width: 64px;
  }
}
</style>
