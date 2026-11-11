<template>
  <div class="order-detail-page">

    <!-- ==================== 页面头部 ==================== -->
    <div class="page-header">
      <button
        class="back-btn"
        type="button"
        @click="goBack"
      >
        ← 返回
      </button>

      <h1>订单详情</h1>
    </div>


    <!-- ==================== 加载中 ==================== -->
    <div
      v-if="loading"
      class="loading"
    >
      <div class="loading-spinner"></div>
      <p>正在加载订单...</p>
    </div>


    <!-- ==================== 加载失败 ==================== -->
    <div
      v-else-if="error"
      class="error-card"
    >
      <div class="error-icon">
        !
      </div>

      <p>{{ error }}</p>

      <div class="error-actions">

        <button
          class="btn btn-ghost"
          type="button"
          @click="loadOrder"
        >
          重新加载
        </button>

        <button
          class="btn btn-primary"
          type="button"
          @click="goBack"
        >
          返回
        </button>

      </div>
    </div>


    <!-- ==================== 订单详情 ==================== -->
    <div
      v-else-if="order"
      class="order-card"
    >

      <!-- ==================== 订单状态 ==================== -->
      <div class="order-status">

        <div>

          <div class="status-title">
            订单状态
          </div>

          <div class="status-description">
            {{ statusDescription }}
          </div>

        </div>


        <span
          class="status"
          :class="statusClass"
        >
          {{ statusText }}
        </span>

      </div>


      <!-- ==================== 订单信息 ==================== -->
      <div class="section">

        <h2>
          订单信息
        </h2>


        <div class="info-row">

          <span>
            订单编号
          </span>

          <span class="value order-no">
            {{ order.order_no || '—' }}
          </span>

        </div>


        <div class="info-row">

          <span>
            订单 ID
          </span>

          <span class="value">
            {{ order.id ?? '—' }}
          </span>

        </div>


        <div class="info-row">

          <span>
            商品 ID
          </span>

          <span class="value">
            {{ order.product_id ?? '—' }}
          </span>

        </div>


        <div class="info-row">

          <span>
            买家 ID
          </span>

          <span class="value">
            {{ order.buyer_id ?? '—' }}
          </span>

        </div>


        <div class="info-row">

          <span>
            卖家 ID
          </span>

          <span class="value">
            {{ order.seller_id ?? '—' }}
          </span>

        </div>


        <div class="info-row">

          <span>
            订单金额
          </span>

          <span class="value price">
            ¥{{ formatPrice(order.price) }}
          </span>

        </div>

      </div>


      <!-- ================================================= -->
      <!-- 交易信息 -->
      <!-- ================================================= -->
      <div class="section">

        <div class="section-title-row">

          <h2>
            交易信息
          </h2>

          <!-- 设置/修改交易安排按钮 -->
          <button
            v-if="canSetMeeting"
            class="meeting-edit-btn"
            type="button"
            :disabled="meetingSaving"
            @click="toggleMeetingForm"
          >
            {{ showMeetingForm ? '取消设置' : meetingExists ? '修改交易安排' : '设置交易安排' }}
          </button>

        </div>


        <!-- ==================== 当前交易地点 ==================== -->

        <div class="info-row">

          <span>
            交易地点
          </span>

          <span
            class="value"
            :class="{
              'empty-value': !order.meeting_location
            }"
          >
            {{
              order.meeting_location ||
              '暂未约定'
            }}
          </span>

        </div>


        <!-- ==================== 当前交易时间 ==================== -->

        <div class="info-row">

          <span>
            交易时间
          </span>

          <span
            class="value"
            :class="{
              'empty-value': !order.meeting_time
            }"
          >
            {{ formatDate(order.meeting_time) }}
          </span>

        </div>


        <!-- ================================================= -->
        <!-- 设置/修改交易安排表单 -->
        <!-- ================================================= -->

        <div
          v-if="showMeetingForm"
          class="meeting-form"
        >

          <div class="meeting-form-title">
            {{ meetingExists ? '修改交易安排' : '设置交易安排' }}
          </div>


          <div class="meeting-tip">
            修改交易时间或地点后，双方需要重新确认交易安排。
          </div>


          <!-- 交易时间 -->

          <div class="form-group">

            <label>
              交易时间
            </label>

            <input
              v-model="meetingForm.meeting_time"
              type="datetime-local"
              class="form-input"
              :disabled="meetingSaving"
            />

          </div>


          <!-- 交易地点 -->

          <div class="form-group">

            <label>
              交易地点
            </label>

            <input
              v-model="meetingForm.meeting_location"
              type="text"
              class="form-input"
              maxlength="100"
              placeholder="例如：关山校区东门"
              :disabled="meetingSaving"
            />

            <div class="input-count">
              {{ meetingForm.meeting_location.length }}/100
            </div>

          </div>


          <!-- 表单按钮 -->

          <div class="meeting-form-actions">

            <button
              class="btn btn-ghost"
              type="button"
              :disabled="meetingSaving"
              @click="cancelMeetingForm"
            >
              取消
            </button>


            <button
              class="btn btn-primary"
              type="button"
              :disabled="meetingSaving"
              @click="handleSetMeeting"
            >

              <span v-if="meetingSaving">
                正在保存...
              </span>

              <span v-else>
                保存交易安排
              </span>

            </button>

          </div>

        </div>


        <!-- ================================================= -->
        <!-- 双方确认状态 -->
        <!-- ================================================= -->

        <div
          v-if="meetingExists"
          class="meeting-confirm-box"
        >

          <div class="meeting-confirm-header">

            <div class="meeting-confirm-title">
              交易安排确认
            </div>

            <span
              v-if="meetingConfirmed"
              class="meeting-all-confirmed"
            >
              ✓ 双方已确认
            </span>

            <span
              v-else
              class="meeting-waiting"
            >
              等待双方确认
            </span>

          </div>


          <!-- 买家确认状态 -->

          <div class="meeting-confirm-row">

            <span>
              买家确认
            </span>

            <span
              class="confirm-status"
              :class="{
                confirmed:
                  order.buyer_meeting_confirmed,
                unconfirmed:
                  !order.buyer_meeting_confirmed
              }"
            >

              {{
                order.buyer_meeting_confirmed
                  ? '✓ 已确认'
                  : '待确认'
              }}

            </span>

          </div>


          <!-- 卖家确认状态 -->

          <div class="meeting-confirm-row">

            <span>
              卖家确认
            </span>

            <span
              class="confirm-status"
              :class="{
                confirmed:
                  order.seller_meeting_confirmed,
                unconfirmed:
                  !order.seller_meeting_confirmed
              }"
            >

              {{
                order.seller_meeting_confirmed
                  ? '✓ 已确认'
                  : '待确认'
              }}

            </span>

          </div>


          <!-- ================================================= -->
          <!-- 当前用户确认按钮 -->
          <!-- ================================================= -->

          <div
            v-if="
              !meetingConfirmed &&
              canConfirmMeeting
            "
            class="meeting-confirm-action"
          >

            <div class="confirm-tip">

              <span v-if="isBuyer && !order.buyer_meeting_confirmed">
                请确认交易时间和地点无误。
              </span>

              <span v-else-if="isSeller && !order.seller_meeting_confirmed">
                请确认交易时间和地点无误。
              </span>

              <span v-else>
                已确认，等待对方确认。
              </span>

            </div>


            <button
              v-if="
                (isBuyer &&
                  !order.buyer_meeting_confirmed) ||
                (isSeller &&
                  !order.seller_meeting_confirmed)
              "
              class="btn btn-confirm-meeting"
              type="button"
              :disabled="meetingConfirming"
              @click="handleConfirmMeeting"
            >

              <span v-if="meetingConfirming">
                正在确认...
              </span>

              <span v-else>
                确认交易安排
              </span>

            </button>

          </div>


          <!-- 双方确认完成 -->

          <div
            v-if="
              meetingConfirmed &&
              ['pending', 'received'].includes(order.status)
            "
            class="meeting-success"
          >
            ✓ 双方已经确认交易时间和地点，可以按照约定进行交易。
          </div>

          <div
            v-else-if="
              meetingConfirmed &&
              ['cancelled', 'completed'].includes(order.status)
            "
            class="meeting-cancelled"
          >
            订单已{{ order.status === 'cancelled' ? '取消' : '完成' }}，交易安排不再生效。
          </div>

        </div>


        <!-- 尚未设置交易安排 -->

        <div
          v-else
          class="meeting-empty"
        >

          <div class="meeting-empty-icon">
            📍
          </div>

          <div>
            <div class="meeting-empty-title">
              尚未设置交易安排
            </div>

            <div class="meeting-empty-text">
              双方可以协商交易时间和地点。
            </div>
          </div>

        </div>

      </div>


      <!-- ==================== 时间信息 ==================== -->
      <div class="section">

        <h2>
          时间信息
        </h2>


        <div class="info-row">

          <span>
            创建时间
          </span>

          <span class="value">
            {{ formatDate(order.created_at) }}
          </span>

        </div>


        <div
          v-if="order.received_at"
          class="info-row"
        >

          <span>
            确认收货时间
          </span>

          <span class="value">
            {{ formatDate(order.received_at) }}
          </span>

        </div>


        <div
          v-if="order.auto_receive_at"
          class="info-row"
        >

          <span>
            自动确认收货时间
          </span>

          <span class="value">
            {{ formatDate(order.auto_receive_at) }}
          </span>

        </div>


        <div
          v-if="order.completed_at"
          class="info-row"
        >

          <span>
            完成时间
          </span>

          <span class="value">
            {{ formatDate(order.completed_at) }}
          </span>

        </div>


        <div
          v-if="order.cancelled_at"
          class="info-row"
        >

          <span>
            取消时间
          </span>

          <span class="value">
            {{ formatDate(order.cancelled_at) }}
          </span>

        </div>

      </div>


      <!-- ================================================= -->
      <!-- 操作区域 -->
      <!-- ================================================= -->

      <div class="order-actions">

        <!-- ================================================= -->
        <!-- 买家：联系卖家 -->
        <!-- ================================================= -->

        <button
          v-if="isBuyer"
          class="btn btn-chat"
          type="button"
          :disabled="openingChat"
          @click="handleContact"
        >

          <span v-if="openingChat">
            正在进入...
          </span>

          <span v-else>
            联系卖家
          </span>

        </button>


        <!-- ================================================= -->
        <!-- 卖家：联系买家 -->
        <!-- ================================================= -->

        <button
          v-if="isSeller"
          class="btn btn-chat"
          type="button"
          :disabled="openingChat"
          @click="handleContact"
        >

          <span v-if="openingChat">
            正在进入...
          </span>

          <span v-else>
            联系买家
          </span>

        </button>


        <!-- ================================================= -->
        <!-- 买家：确认收货 -->
        <!-- ================================================= -->

        <button
          v-if="
            order.status === 'pending' &&
            isBuyer
          "
          class="btn btn-primary"
          type="button"
          :disabled="
            receiving ||
            cancelling
          "
          @click="handleReceiveOrder"
        >

          <span v-if="receiving">
            正在确认...
          </span>

          <span v-else>
            确认收货
          </span>

        </button>


        <!-- ================================================= -->
        <!-- 取消订单 -->
        <!-- ================================================= -->

        <button
          v-if="
            order.status === 'pending' &&
            (
              isBuyer ||
              isSeller
            )
          "
          class="btn btn-danger"
          type="button"
          :disabled="
            cancelling ||
            receiving
          "
          @click="handleCancelOrder"
        >

          <span v-if="cancelling">
            正在取消...
          </span>

          <span v-else>
            取消订单
          </span>

        </button>


        <!-- ================================================= -->
        <!-- 卖家：确认交易完成 -->
        <!-- ================================================= -->

        <button
          v-if="
            order.status === 'received' &&
            isSeller
          "
          class="btn btn-primary"
          type="button"
          :disabled="completing"
          @click="handleCompleteOrder"
        >

          <span v-if="completing">
            正在完成...
          </span>

          <span v-else>
            确认交易完成
          </span>

        </button>


        <!-- ================================================= -->
        <!-- 买家：已经确认收货 -->
        <!-- ================================================= -->

        <div
          v-if="
            order.status === 'received' &&
            isBuyer
          "
          class="action-message received-message"
        >
          已确认收货，等待卖家完成交易
        </div>


        <!-- ================================================= -->
        <!-- 已取消 -->
        <!-- ================================================= -->

        <div
          v-if="
            order.status === 'cancelled'
          "
          class="action-message cancelled-message"
        >
          该订单已经取消
        </div>


        <!-- ================================================= -->
        <!-- 已完成 -->
        <!-- ================================================= -->

        <div
          v-if="
            order.status === 'completed'
          "
          class="action-message completed-message"
        >
          该订单已经完成
        </div>

      </div>

    </div>

  </div>
</template>


<script setup>

import {
  ref,
  computed,
  onMounted
} from 'vue'

import {
  useRoute,
  useRouter
} from 'vue-router'

import {
  ordersApi
} from '../api/orders'

import {
  chatApi
} from '../api/chat'

import {
  orderStatusText
} from '../constants/status'

import { getApiErrorMessage } from '../utils/apiError'


const route = useRoute()

const router = useRouter()


/* =========================================================
   订单数据
   ========================================================= */

const order = ref(null)

const loading = ref(false)

const error = ref('')


/* =========================================================
   操作状态
   ========================================================= */

const cancelling = ref(false)

const receiving = ref(false)

const completing = ref(false)

const openingChat = ref(false)

const meetingSaving = ref(false)

const meetingConfirming = ref(false)


/* =========================================================
   当前用户
   ========================================================= */

const currentUser = ref(null)


function loadCurrentUser() {

  try {

    const userJson =
      localStorage.getItem('cm_user')


    if (!userJson) {

      currentUser.value = null

      return

    }


    currentUser.value =
      JSON.parse(userJson)

  } catch (err) {

    console.error(
      '读取当前用户信息失败:',
      err
    )

    currentUser.value = null

  }

}


/* =========================================================
   交易安排表单
   ========================================================= */

const showMeetingForm = ref(false)

const meetingForm = ref({
  meeting_time: '',
  meeting_location: ''
})


/* =========================================================
   是否已经存在交易安排
   ========================================================= */

const meetingExists = computed(() => {

  if (!order.value) {
    return false
  }


  return Boolean(
    order.value.meeting_time ||
    order.value.meeting_location
  )

})


/* =========================================================
   是否双方都确认
   ========================================================= */

const meetingConfirmed = computed(() => {

  if (!order.value) {
    return false
  }


  return Boolean(
    order.value.buyer_meeting_confirmed &&
    order.value.seller_meeting_confirmed
  )

})


/* =========================================================
   当前用户是不是买家
   ========================================================= */

const isBuyer = computed(() => {

  if (
    !order.value ||
    !currentUser.value
  ) {
    return false
  }


  return (
    Number(currentUser.value.id) ===
    Number(order.value.buyer_id)
  )

})


/* =========================================================
   当前用户是不是卖家
   ========================================================= */

const isSeller = computed(() => {

  if (
    !order.value ||
    !currentUser.value
  ) {
    return false
  }


  return (
    Number(currentUser.value.id) ===
    Number(order.value.seller_id)
  )

})


/* =========================================================
   是否允许设置交易安排
   ========================================================= */

const canSetMeeting = computed(() => {

  if (!order.value) {
    return false
  }


  if (
    !isBuyer.value &&
    !isSeller.value
  ) {
    return false
  }


  if (
    order.value.status === 'completed' ||
    order.value.status === 'cancelled'
  ) {
    return false
  }


  return true

})


/* =========================================================
   是否允许确认交易安排
   ========================================================= */

const canConfirmMeeting = computed(() => {

  if (!order.value) {
    return false
  }


  if (!meetingExists.value) {
    return false
  }


  if (
    order.value.status === 'completed' ||
    order.value.status === 'cancelled'
  ) {
    return false
  }


  return (
    isBuyer.value ||
    isSeller.value
  )

})


/* =========================================================
   订单状态文字
   ========================================================= */

const statusText = computed(() => {

  if (!order.value) {
    return ''
  }

  return orderStatusText(order.value.status)

})


/* =========================================================
   状态 CSS
   ========================================================= */

const statusClass = computed(() => {

  if (!order.value) {
    return ''
  }


  return `status-${order.value.status}`

})


/* =========================================================
   状态说明
   ========================================================= */

const statusDescription = computed(() => {

  if (!order.value) {
    return ''
  }


  const descriptionMap = {

    pending:
      isBuyer.value
        ? '请确认收到商品后，再点击确认收货'
        : '等待买家确认收货',

    received:
      isSeller.value
        ? '买家已经确认收货，请确认交易完成'
        : '已确认收货，等待卖家确认交易完成',

    completed:
      '交易已经完成',

    cancelled:
      '订单已经取消，商品可以重新上架'

  }


  return (
    descriptionMap[
      order.value.status
    ] || ''
  )

})


/* =========================================================
   获取订单详情
   ========================================================= */

async function loadOrder() {

  loading.value = true

  error.value = ''

  order.value = null


  try {

    const orderId =
      route.params.id


    if (
      orderId === undefined ||
      orderId === null ||
      orderId === ''
    ) {

      throw new Error(
        '订单 ID 不存在'
      )

    }


    const response =
      await ordersApi.getDetail(
        orderId
      )


    if (
      response?.code !== undefined &&
      response.code !== 200
    ) {

      throw new Error(
        response.message ||
        '获取订单失败'
      )

    }


    order.value =
      response?.data ||
      response


    if (!order.value) {

      throw new Error(
        '订单不存在'
      )

    }

  } catch (err) {

    console.error(
      '获取订单详情失败:',
      err
    )


    error.value = getApiErrorMessage(err, '获取订单详情失败')

  } finally {

    loading.value = false

  }

}


/* =========================================================
   打开/关闭交易安排表单
   ========================================================= */

function toggleMeetingForm() {

  if (!order.value) {
    return
  }


  if (showMeetingForm.value) {

    cancelMeetingForm()

    return

  }


  /*
   * 已经有交易时间时，
   * 自动填充到 datetime-local
   */

  meetingForm.value.meeting_time =
    convertToDateTimeLocal(
      order.value.meeting_time
    )


  meetingForm.value.meeting_location =
    order.value.meeting_location ||
    ''


  showMeetingForm.value = true

}


/* =========================================================
   取消交易安排编辑
   ========================================================= */

function cancelMeetingForm() {

  showMeetingForm.value = false

  meetingForm.value = {
    meeting_time: '',
    meeting_location: ''
  }

}


/* =========================================================
   datetime 转 datetime-local
   ========================================================= */

function convertToDateTimeLocal(value) {

  if (!value) {
    return ''
  }


  const date =
    new Date(value)


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return ''
  }


  /*
   * datetime-local 不需要时区后缀
   */

  const year =
    date.getFullYear()


  const month =
    String(
      date.getMonth() + 1
    ).padStart(2, '0')


  const day =
    String(
      date.getDate()
    ).padStart(2, '0')


  const hours =
    String(
      date.getHours()
    ).padStart(2, '0')


  const minutes =
    String(
      date.getMinutes()
    ).padStart(2, '0')


  return (
    `${year}-${month}-${day}` +
    `T${hours}:${minutes}`
  )

}


/* =========================================================
   设置交易安排
   ========================================================= */

async function handleSetMeeting() {

  if (!order.value) {
    return
  }


  if (!isBuyer.value && !isSeller.value) {

    window.alert(
      '你不是该订单的参与者'
    )

    return

  }


  if (
    order.value.status === 'completed' ||
    order.value.status === 'cancelled'
  ) {

    window.alert(
      '当前订单状态不能设置交易安排'
    )

    return

  }


  const meetingTime =
    meetingForm.value.meeting_time


  const meetingLocation =
    meetingForm.value.meeting_location.trim()


  if (!meetingTime) {

    window.alert(
      '请选择交易时间'
    )

    return

  }


  if (!meetingLocation) {

    window.alert(
      '请输入交易地点'
    )

    return

  }


  if (meetingLocation.length > 100) {

    window.alert(
      '交易地点不能超过100个字'
    )

    return

  }


  /*
   * datetime-local 是本地时间。
   *
   * 后端 datetime 接收后，
   * 会按照当前项目的时间处理方式保存。
   */

  const selectedDate =
    new Date(meetingTime)


  if (
    Number.isNaN(
      selectedDate.getTime()
    )
  ) {

    window.alert(
      '交易时间格式不正确'
    )

    return

  }


  if (
    selectedDate.getTime() <=
    Date.now()
  ) {

    window.alert(
      '交易时间必须晚于当前时间'
    )

    return

  }


  if (meetingSaving.value) {
    return
  }


  meetingSaving.value = true


  try {

    const response =
      await ordersApi.setMeeting(
        order.value.id,
        {
          meeting_time:
            meetingTime,

          meeting_location:
            meetingLocation
        }
      )


    if (
      response?.code !== undefined &&
      response.code !== 200
    ) {

      throw new Error(
        response.message ||
        '设置交易安排失败'
      )

    }


    /*
     * 后端返回新的交易安排
     */

    if (response?.data) {

      order.value = {
        ...order.value,
        meeting_time:
          response.data.meeting_time,
        meeting_location:
          response.data.meeting_location,
        buyer_meeting_confirmed:
          response.data.buyer_meeting_confirmed,
        seller_meeting_confirmed:
          response.data.seller_meeting_confirmed
      }

    } else {

      /*
       * 如果后端没有返回完整数据，
       * 重新请求订单详情。
       */

      await loadOrder()

    }


    cancelMeetingForm()


    window.alert(
      '交易安排保存成功，请双方重新确认'
    )

  } catch (err) {

    console.error(
      '设置交易安排失败:',
      err
    )


    window.alert(
      getApiErrorMessage(err, '设置交易安排失败，请稍后重试')
    )

  } finally {

    meetingSaving.value = false

  }

}


/* =========================================================
   确认交易安排
   ========================================================= */

async function handleConfirmMeeting() {

  if (!order.value) {
    return
  }


  if (!meetingExists.value) {

    window.alert(
      '请先设置交易时间和地点'
    )

    return

  }


  if (!isBuyer.value && !isSeller.value) {

    window.alert(
      '你不是该订单的参与者'
    )

    return

  }


  if (meetingConfirmed.value) {

    return

  }


  /*
   * 防止重复确认
   */

  if (isBuyer.value &&
      order.value.buyer_meeting_confirmed) {

    return

  }


  if (isSeller.value &&
      order.value.seller_meeting_confirmed) {

    return

  }


  if (meetingConfirming.value) {
    return
  }


  const confirmed =
    window.confirm(

      '请确认交易时间和地点无误。\n\n' +

      `交易地点：${
        order.value.meeting_location
      }\n` +

      `交易时间：${
        formatDate(order.value.meeting_time)
      }\n\n` +

      '确认后，如果对方也确认，交易安排就正式确定。'

    )


  if (!confirmed) {
    return
  }


  meetingConfirming.value = true


  try {

    const response =
      await ordersApi.confirmMeeting(
        order.value.id
      )


    if (
      response?.code !== undefined &&
      response.code !== 200
    ) {

      throw new Error(
        response.message ||
        '确认交易安排失败'
      )

    }


    if (response?.data) {

      order.value = {
        ...order.value,

        meeting_time:
          response.data.meeting_time,

        meeting_location:
          response.data.meeting_location,

        buyer_meeting_confirmed:
          response.data.buyer_meeting_confirmed,

        seller_meeting_confirmed:
          response.data.seller_meeting_confirmed
      }

    } else {

      await loadOrder()

    }


    if (
      response?.data?.confirmed
    ) {

      window.alert(
        '双方已确认交易安排，可以按照约定进行交易。'
      )

    } else {

      window.alert(
        '确认成功，等待对方确认。'
      )

    }

  } catch (err) {

    console.error(
      '确认交易安排失败:',
      err
    )


    window.alert(
      getApiErrorMessage(err, '确认交易安排失败，请稍后重试')
    )

  } finally {

    meetingConfirming.value = false

  }

}


/* =========================================================
   联系买家 / 联系卖家
   ========================================================= */

async function handleContact() {

  if (!order.value) {
    return
  }


  if (
    !isBuyer.value &&
    !isSeller.value
  ) {

    window.alert(
      '你不是该订单的参与者'
    )

    return

  }


  if (openingChat.value) {
    return
  }


  openingChat.value = true


  try {

    const response =
      await chatApi.getOrCreate(
        order.value.id
      )


    if (
      response?.code !== undefined &&
      response.code !== 200
    ) {

      throw new Error(
        response.message ||
        '获取聊天失败'
      )

    }


    const conversation =
      response?.data


    if (
      !conversation?.conversation_id
    ) {

      throw new Error(
        '聊天会话不存在'
      )

    }


    router.push({

      name: 'chat',

      params: {
        conversationId:
          conversation.conversation_id
      }

    })

  } catch (err) {

    console.error(
      '进入聊天失败:',
      err
    )


    window.alert(
      getApiErrorMessage(err, '进入聊天失败，请稍后重试')
    )

  } finally {

    openingChat.value = false

  }

}


/* =========================================================
   买家确认收货
   ========================================================= */

async function handleReceiveOrder() {

  if (!order.value) {
    return
  }


  if (!isBuyer.value) {
    return
  }


  if (
    order.value.status !== 'pending'
  ) {

    return

  }


  if (receiving.value) {
    return
  }


  const confirmed =
    window.confirm(

      '确定要确认收货吗？\n\n' +

      '确认收货后，订单将进入“待交易完成”状态，' +

      '卖家可以确认交易完成。'

    )


  if (!confirmed) {
    return
  }


  receiving.value = true


  try {

    await ordersApi.receive(
      order.value.id
    )


    await loadOrder()

  } catch (err) {

    console.error(
      '确认收货失败:',
      err
    )


    window.alert(
      getApiErrorMessage(err, '确认收货失败，请稍后重试')
    )

  } finally {

    receiving.value = false

  }

}


/* =========================================================
   卖家确认交易完成
   ========================================================= */

async function handleCompleteOrder() {

  if (!order.value) {
    return
  }


  if (!isSeller.value) {
    return
  }


  if (
    order.value.status !== 'received'
  ) {

    return

  }


  if (completing.value) {
    return
  }


  const confirmed =
    window.confirm(

      '确定要完成这笔交易吗？\n\n' +

      '完成后商品将标记为已售出，' +

      '订单将无法再次操作。'

    )


  if (!confirmed) {
    return
  }


  completing.value = true


  try {

    await ordersApi.complete(
      order.value.id
    )


    await loadOrder()

  } catch (err) {

    console.error(
      '确认交易完成失败:',
      err
    )


    window.alert(
      getApiErrorMessage(err, '确认交易完成失败，请稍后重试')
    )

  } finally {

    completing.value = false

  }

}


/* =========================================================
   取消订单
   ========================================================= */

async function handleCancelOrder() {

  if (!order.value) {
    return
  }


  if (
    !isBuyer.value &&
    !isSeller.value
  ) {

    return

  }


  if (
    order.value.status !== 'pending'
  ) {

    return

  }


  if (cancelling.value) {
    return
  }


  const confirmed =
    window.confirm(

      '确定要取消这个订单吗？\n\n' +

      '取消后，该商品将重新上架，' +

      '其他用户可以再次购买。'

    )


  if (!confirmed) {
    return
  }


  cancelling.value = true


  try {

    await ordersApi.cancel(
      order.value.id
    )


    await loadOrder()

  } catch (err) {

    console.error(
      '取消订单失败:',
      err
    )


    window.alert(
      getApiErrorMessage(err, '取消订单失败，请稍后重试')
    )

  } finally {

    cancelling.value = false

  }

}


/* =========================================================
   返回
   ========================================================= */

function goBack() {

  router.back()

}


/* =========================================================
   格式化价格
   ========================================================= */

function formatPrice(value) {

  if (
    value === undefined ||
    value === null ||
    value === ''
  ) {

    return '0.00'

  }


  const number =
    Number(value)


  if (!Number.isFinite(number)) {

    return String(value)

  }


  return number.toFixed(2)

}


/* =========================================================
   格式化时间
   ========================================================= */

function formatDate(value) {

  if (!value) {

    return '暂未设置'

  }


  const date =
    new Date(value)


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return value

  }


  return date.toLocaleString(

    'zh-CN',

    {

      year: 'numeric',

      month: '2-digit',

      day: '2-digit',

      hour: '2-digit',

      minute: '2-digit'

    }

  )

}


/* =========================================================
   页面加载
   ========================================================= */

onMounted(() => {

  loadCurrentUser()

  loadOrder()

})

</script>


<style scoped>

.order-detail-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 30px 20px 60px;
}


/* =========================================================
   页面头部
   ========================================================= */

.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 25px;
}


.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}


.back-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  padding: 8px 4px;
  transition: opacity 0.2s;
}


.back-btn:hover {
  opacity: 0.65;
}


/* =========================================================
   订单卡片
   ========================================================= */

.order-card {
  background: white;
  border-radius: 14px;
  padding: 28px;
  box-shadow:
    0 2px 10px rgba(0, 0, 0, 0.08);
}


/* =========================================================
   订单状态
   ========================================================= */

.order-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid #eee;
}


.status-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 7px;
}


.status-description {
  color: #888;
  font-size: 13px;
  line-height: 1.5;
}


.status {
  flex-shrink: 0;
  padding: 7px 14px;
  border-radius: 7px;
  font-size: 14px;
  font-weight: 600;
}


.status-pending {
  color: #d97706;
  background: #fff7ed;
}


.status-received {
  color: #2563eb;
  background: #eff6ff;
}


.status-completed {
  color: #16a34a;
  background: #f0fdf4;
}


.status-cancelled {
  color: #dc2626;
  background: #fef2f2;
}


/* =========================================================
   信息区域
   ========================================================= */

.section {
  padding: 24px 0;
  border-bottom: 1px solid #eee;
}


.section:last-of-type {
  border-bottom: none;
}


.section h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 15px;
}


.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}


.section-title-row h2 {
  margin: 0;
}


.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 30px;
  min-height: 42px;
  padding: 8px 0;
  font-size: 14px;
}


.info-row > span:first-child {
  flex-shrink: 0;
  color: #777;
}


.info-row .value {
  text-align: right;
  color: #333;
  word-break: break-all;
}


.empty-value {
  color: #999 !important;
}


.order-no {
  font-family:
    Consolas,
    Monaco,
    monospace;
  font-size: 13px;
}


.price {
  font-size: 18px;
  font-weight: 700;
  color: #f56c6c !important;
}


/* =========================================================
   设置交易安排按钮
   ========================================================= */

.meeting-edit-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  border-radius: 7px;
  padding: 7px 13px;
  font-size: 13px;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s;
}


.meeting-edit-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}


.meeting-edit-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}


/* =========================================================
   交易安排表单
   ========================================================= */

.meeting-form {
  margin-top: 18px;
  padding: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
}


.meeting-form-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 7px;
}


.meeting-tip {
  margin-bottom: 18px;
  color: #888;
  font-size: 12px;
  line-height: 1.5;
}


.form-group {
  position: relative;
  margin-bottom: 17px;
}


.form-group label {
  display: block;
  margin-bottom: 7px;
  color: #555;
  font-size: 13px;
  font-weight: 600;
}


.form-input {
  box-sizing: border-box;
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border: 1px solid #d1d5db;
  border-radius: 7px;
  outline: none;
  background: white;
  color: #333;
  font-size: 14px;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}


.form-input:focus {
  border-color: #111827;
  box-shadow:
    0 0 0 2px rgba(17, 24, 39, 0.08);
}


.form-input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}


.input-count {
  margin-top: 5px;
  text-align: right;
  color: #999;
  font-size: 11px;
}


.meeting-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 5px;
}


/* =========================================================
   交易安排确认
   ========================================================= */

.meeting-confirm-box {
  margin-top: 18px;
  padding: 17px;
  border-radius: 10px;
  background: #f8fafc;
}


.meeting-confirm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}


.meeting-confirm-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}


.meeting-all-confirmed {
  color: #16a34a;
  font-size: 13px;
  font-weight: 600;
}


.meeting-waiting {
  color: #d97706;
  font-size: 13px;
  font-weight: 600;
}


.meeting-confirm-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 34px;
  font-size: 13px;
  color: #666;
}


.confirm-status {
  font-weight: 600;
}


.confirmed {
  color: #16a34a;
}


.unconfirmed {
  color: #d97706;
}


/* =========================================================
   确认操作
   ========================================================= */

.meeting-confirm-action {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e5e7eb;
}


.confirm-tip {
  margin-bottom: 10px;
  color: #666;
  font-size: 12px;
  line-height: 1.5;
}


.btn-confirm-meeting {
  width: 100%;
  background: #111827;
  color: white;
  border-color: #111827;
}


.btn-confirm-meeting:hover {
  background: #1f2937;
}


.meeting-success {
  margin-top: 14px;
  padding: 11px 13px;
  border-radius: 7px;
  background: #f0fdf4;
  color: #16a34a;
  font-size: 13px;
  line-height: 1.5;
}

.meeting-cancelled {
  margin-top: 14px;
  padding: 11px 13px;
  border-radius: 7px;
  background: var(--panel);
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

:global([data-theme="dark"]) .meeting-success {
  background: #17351f;
  color: #86efac;
}


/* =========================================================
   没有交易安排
   ========================================================= */

.meeting-empty {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 15px;
  padding: 15px;
  border-radius: 9px;
  background: #f9fafb;
}


.meeting-empty-icon {
  font-size: 24px;
}


.meeting-empty-title {
  margin-bottom: 3px;
  color: #555;
  font-size: 13px;
  font-weight: 600;
}


.meeting-empty-text {
  color: #999;
  font-size: 12px;
}


/* =========================================================
   操作区域
   ========================================================= */

.order-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding-top: 25px;
  flex-wrap: wrap;
}


.btn {
  min-height: 42px;
  padding: 0 22px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 14px;
  transition:
    background 0.2s,
    opacity 0.2s,
    transform 0.1s;
}


.btn:active {
  transform: scale(0.98);
}


.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}


/* =========================================================
   普通按钮
   ========================================================= */

.btn-ghost {
  background: white;
  border-color: #ddd;
  color: #555;
}


.btn-ghost:hover {
  background: #f7f7f7;
}


/* =========================================================
   主要按钮
   ========================================================= */

.btn-primary {
  background: #111827;
  color: white;
}


.btn-primary:hover {
  background: #1f2937;
}


/* =========================================================
   聊天按钮
   ========================================================= */

.btn-chat {
  background: #f3f4f6;
  border-color: #d1d5db;
  color: #111827;
}


.btn-chat:hover {
  background: #e5e7eb;
}


/* =========================================================
   取消订单
   ========================================================= */

.btn-danger {
  background: #fff;
  border-color: #fca5a5;
  color: #dc2626;
}


.btn-danger:hover {
  background: #fef2f2;
}


/* =========================================================
   操作提示
   ========================================================= */

.action-message {
  width: 100%;
  padding: 12px 15px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
}


.received-message {
  color: #2563eb;
  background: #eff6ff;
}


.cancelled-message {
  color: #888;
  background: #f5f5f5;
}


.completed-message {
  color: #16a34a;
  background: #f0fdf4;
}


/* =========================================================
   加载
   ========================================================= */

.loading {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #777;
}


.loading p {
  margin-top: 15px;
}


.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #eee;
  border-top-color: #555;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}


@keyframes spin {

  to {
    transform: rotate(360deg);
  }

}


/* =========================================================
   错误
   ========================================================= */

.error-card {
  background: white;
  border-radius: 14px;
  padding: 50px 30px;
  text-align: center;
  box-shadow:
    0 2px 10px rgba(0, 0, 0, 0.08);
}


.error-icon {
  width: 42px;
  height: 42px;
  margin: 0 auto 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #fef2f2;
  color: #dc2626;
  font-size: 22px;
  font-weight: 700;
}


.error-card p {
  margin: 0 0 20px;
  color: #666;
}


.error-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}


/* =========================================================
   移动端
   ========================================================= */

@media (max-width: 768px) {

  .order-detail-page {
    padding: 20px 14px 40px;
  }


  .page-header {
    gap: 12px;
    margin-bottom: 18px;
  }


  .page-header h1 {
    font-size: 23px;
  }


  .order-card {
    padding: 20px 16px;
    border-radius: 12px;
  }


  .order-status {
    align-items: flex-start;
  }


  .status-description {
    max-width: 220px;
  }


  .info-row {
    gap: 15px;
  }


  .info-row .value {
    max-width: 60%;
  }


  .section-title-row {
    align-items: flex-start;
  }


  .meeting-edit-btn {
    flex-shrink: 0;
  }


  .meeting-form {
    padding: 15px;
  }


  .order-actions {
    justify-content: stretch;
  }


  .order-actions .btn {
    flex: 1;
  }


  .btn-danger {
    width: 100%;
  }

}


@media (max-width: 480px) {

  .order-status {
    flex-direction: column;
  }


  .status-description {
    max-width: none;
  }


  .status {
    align-self: flex-start;
  }


  .info-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }


  .info-row .value {
    max-width: 100%;
    text-align: left;
  }


  .section-title-row {
    flex-direction: column;
  }


  .meeting-edit-btn {
    width: 100%;
  }


  .meeting-confirm-header {
    align-items: flex-start;
    flex-direction: column;
  }


  .meeting-form-actions {
    flex-direction: column-reverse;
  }


  .meeting-form-actions .btn {
    width: 100%;
  }


  .order-actions {
    flex-direction: column;
  }


  .order-actions .btn {
    width: 100%;
    flex: none;
  }


  .meeting-empty {
    align-items: flex-start;
  }

}

</style>