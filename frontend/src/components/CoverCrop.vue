<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue"

const props = defineProps<{ file: File }>()
const emit = defineEmits<{ use: [file: File]; cancel: [] }>()
const url = URL.createObjectURL(props.file)
const img = ref<HTMLImageElement | null>(null)
const box = ref({ width: 100, height: 130 })
const frame = ref({ x: 0, y: 0 })
let drag: { x: number; y: number; fx: number; fy: number } | null = null

onBeforeUnmount(() => URL.revokeObjectURL(url))

function layout() {
  const image = img.value
  if (!image) return
  let width = Math.min(image.naturalWidth, 420)
  let height = image.naturalHeight * (width / image.naturalWidth)
  const scaleUp = Math.max(100 / width, 130 / height, 1)
  width *= scaleUp
  height *= scaleUp
  box.value = { width, height }
  frame.value = { x: Math.max(0, (width - 100) / 2), y: Math.max(0, (height - 130) / 2) }
}

function down(event: PointerEvent) {
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  drag = { x: event.clientX, y: event.clientY, fx: frame.value.x, fy: frame.value.y }
}

function move(event: PointerEvent) {
  if (!drag) return
  frame.value = {
    x: Math.min(Math.max(0, drag.fx + event.clientX - drag.x), box.value.width - 100),
    y: Math.min(Math.max(0, drag.fy + event.clientY - drag.y), box.value.height - 130),
  }
}

function up() {
  drag = null
}

function confirmCrop() {
  const image = img.value
  if (!image) return
  const scale = image.naturalWidth / box.value.width
  const canvas = document.createElement("canvas")
  canvas.width = 100
  canvas.height = 130
  const context = canvas.getContext("2d")
  if (!context) return
  context.drawImage(
    image,
    frame.value.x * scale,
    frame.value.y * scale,
    100 * scale,
    130 * scale,
    0,
    0,
    100,
    130,
  )
  canvas.toBlob((blob) => {
    if (!blob) return
    emit("use", new File([blob], "cover.png", { type: "image/png" }))
  }, "image/png")
}
</script>

<template>
  <div>
    <p class="muted">拖动方框，从图片里截取 100×130 的封面。</p>
    <div class="actions">
      <button class="quiet-button" type="button" @click="confirmCrop">使用截取</button>
      <button class="text-button" type="button" @click="emit('cancel')">取消</button>
    </div>
    <div class="crop-stage" :style="{ width: `${box.width}px`, height: `${box.height}px` }">
      <img ref="img" :src="url" alt="待截取的封面" @load="layout" />
      <div
        class="crop-frame"
        :style="{ transform: `translate(${frame.x}px, ${frame.y}px)` }"
        @pointerdown="down"
        @pointermove="move"
        @pointerup="up"
      />
    </div>
  </div>
</template>
