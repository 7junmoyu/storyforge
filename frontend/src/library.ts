import { ref } from "vue"

export const libraryTick = ref(0)

export function touchLibrary() {
  libraryTick.value += 1
}
