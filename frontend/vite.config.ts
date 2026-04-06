import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      }
    }
  },
  build: {
    // 启用代码压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        // 生产环境移除console和debugger
        drop_console: true,
        drop_debugger: true
      }
    },
    // 代码分割配置
    rollupOptions: {
      output: {
        // 分割第三方库
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'antd-vendor': ['ant-design-vue', '@ant-design/icons-vue'],
          'utils': ['axios']
        },
        // 静态资源分类打包
        chunkFileNames: 'static/js/[name]-[hash].js',
        entryFileNames: 'static/js/[name]-[hash].js',
        assetFileNames: 'static/[ext]/[name]-[hash].[ext]'
      }
    },
    // 启用CSS代码分割
    cssCodeSplit: true,
    // 开启生产环境sourcemap（可选，建议关闭以提升构建速度和安全性）
    sourcemap: false,
    // 大于10kb的资源单独打包
    assetsInlineLimit: 10 * 1024
  },
  // 预编译依赖优化
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'ant-design-vue', 'axios']
  }
})
