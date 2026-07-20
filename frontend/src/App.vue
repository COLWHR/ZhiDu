<template>
  <a-config-provider :locale="zhCN" :theme="themeConfig">
    <div class="app-container">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useConfigStore } from '@/stores/config'
import { computed } from 'vue'

const configStore = useConfigStore()

const themeConfig = computed(() => ({
  algorithm: configStore.isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
  token: {
    colorPrimary: '#3bb36b',
    colorLink: '#3bb36b',
    colorSuccess: '#15803d',
    colorWarning: '#b45309',
    colorError: '#dc2626',
    colorInfo: '#3bb36b',
    borderRadius: 12,
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f2f7f3',
    colorText: '#1a1d1e',
    colorTextSecondary: '#6b7280',
    colorBorder: '#e8f0ea',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
}))
</script>

<style>
html, body, #app, .app-container {
  min-height: 100%;
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto;
}
</style>
