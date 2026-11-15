<script setup>
import { computed } from 'vue'
import { catIconPath } from '../utils/icons'

const props = defineProps({
  category: { type: String, required: true },
})

const markup = computed(() => `<svg viewBox="0 0 24 24" fill="none">${catIconPath(props.category)}</svg>`)
</script>

<template>
  <span v-html="markup" style="display: contents"></span>
</template>
