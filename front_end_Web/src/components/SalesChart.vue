<script setup>
import { computed } from 'vue'

const props = defineProps({
  // sales: [{ day: '9/10', amount: 25 }, ...]
  sales: { type: Array, default: () => [] },
})

const chart = computed(() => {
  if (!props.sales.length) return null
  const w = 560, h = 180, padL = 36, padR = 16, padT = 16, padB = 28
  let running = 0
  const cum = props.sales.map((s) => {
    running += s.amount
    return running
  })
  const max = Math.max(...cum, 1)
  const stepX = (w - padL - padR) / Math.max(cum.length - 1, 1)
  const pts = cum.map((v, i) => {
    const x = padL + stepX * i
    const y = padT + (h - padT - padB) * (1 - v / max)
    return { x, y, label: props.sales[i].day, value: v }
  })
  const points = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const areaPath =
    `M${padL},${h - padB} L` + points.split(' ').join(' L ') + ` L${pts[pts.length - 1].x.toFixed(1)},${h - padB} Z`
  return { w, h, padL, padB, points, areaPath, pts }
})
</script>

<template>
  <div v-if="chart" class="chart-wrap">
    <svg :viewBox="`0 0 ${chart.w} ${chart.h}`" preserveAspectRatio="none">
      <line
        :x1="chart.padL"
        :y1="chart.h - chart.padB"
        :x2="chart.w - 16"
        :y2="chart.h - chart.padB"
        stroke="var(--border)"
        stroke-width="1"
      />
      <path :d="chart.areaPath" fill="var(--panel)" stroke="none" />
      <polyline
        :points="chart.points"
        fill="none"
        stroke="var(--ink)"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <circle v-for="(p, i) in chart.pts" :key="i" :cx="p.x" :cy="p.y" r="3" fill="var(--ink)" />
      <text
        v-for="(p, i) in chart.pts"
        :key="'t' + i"
        :x="p.x"
        :y="chart.h - 8"
        font-size="10"
        fill="var(--muted-2)"
        text-anchor="middle"
      >{{ p.label }}</text>
    </svg>
  </div>
  <div v-else class="chart-empty">还没有售出记录，卖出第一件闲置后这里会显示收益走势</div>
</template>
