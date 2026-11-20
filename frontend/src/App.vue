<script setup lang="ts">
import { darkTheme, lightTheme, NConfigProvider, NDialogProvider, NMessageProvider } from "naive-ui"
import { computed, ref } from "vue"
import ShellLayout from "./components/ShellLayout.vue"

const themeName = ref(localStorage.getItem("sf-theme") === "light" ? "light" : "dark")
document.documentElement.dataset.theme = themeName.value

const theme = computed(() => (themeName.value === "dark" ? darkTheme : lightTheme))
const overrides = computed(() => {
  const dark = themeName.value === "dark"
  return {
    common: {
      primaryColor: "#cc785c",
      primaryColorHover: "#d4896d",
      primaryColorPressed: "#a9583e",
      primaryColorSuppl: "#cc785c",
      borderRadius: "8px",
      fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
      bodyColor: dark ? "#181715" : "#faf9f5",
      cardColor: dark ? "#252320" : "#faf9f5",
      modalColor: dark ? "#252320" : "#faf9f5",
      popoverColor: dark ? "#252320" : "#faf9f5",
      inputColor: dark ? "#1f1e1b" : "#faf9f5",
      actionColor: dark ? "#252320" : "#f5f0e8",
      borderColor: dark ? "#3a342c" : "#e6dfd8",
      dividerColor: dark ? "#3a342c" : "#ebe6df",
      hoverColor: dark ? "#252320" : "#f5f0e8",
      textColor1: dark ? "#faf9f5" : "#141413",
      textColor2: dark ? "#a09d96" : "#3d3d3a",
      textColor3: dark ? "#8e8b82" : "#6c6a64",
      placeholderColor: "#8e8b82",
    },
  }
})

function toggleTheme() {
  themeName.value = themeName.value === "dark" ? "light" : "dark"
  localStorage.setItem("sf-theme", themeName.value)
  document.documentElement.dataset.theme = themeName.value
}
</script>

<template>
  <NConfigProvider :theme="theme" :theme-overrides="overrides">
    <NMessageProvider>
      <NDialogProvider>
        <ShellLayout :theme-name="themeName" @toggle-theme="toggleTheme" />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
