<template>
  <div class="auth-wrapper">
    <div class="bg-decoration">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>
    
    <div class="auth-container fade-in-up">
      <div class="brand-section">
        <div class="logo float-animation">
          <img src="@/assets/logo.png" alt="智渡" class="logo-icon" />
        </div>
        <h1 class="brand-title">智渡</h1>
        <p class="brand-slogan">多智能体圆桌会议，让思维碰撞出火花</p>
      </div>
      
      <a-card :bordered="false" class="auth-card glass-card">
        <div class="auth-header">
          <div class="auth-title">欢迎回来</div>
          <div class="auth-subtitle">登录您的账户，继续精彩的讨论</div>
        </div>
        
        <a-alert
          v-if="authStore.error"
          :message="authStore.error"
          type="error"
          show-icon
          closable
          style="margin-bottom: 24px"
          @close="authStore.error = null"
        />

        <a-form
          layout="vertical"
          :model="formState"
          @finish="onFinish"
          hide-required-mark
          class="auth-form"
        >
          <a-form-item
            name="username"
            :rules="[{ required: true, message: '请输入用户名' }]"
          >
            <a-input
              v-model:value="formState.username"
              size="large"
              placeholder="输入用户名"
              class="custom-input"
            >
              <template #prefix>
                <user-outlined class="input-icon" />
              </template>
            </a-input>
          </a-form-item>

          <a-form-item
            name="password"
            :rules="[{ required: true, message: '请输入密码' }]"
          >
            <a-input-password
              v-model:value="formState.password"
              size="large"
              placeholder="输入密码"
              class="custom-input"
            >
              <template #prefix>
                <lock-outlined class="input-icon" />
              </template>
            </a-input-password>
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              size="large"
              block
              :loading="authStore.loading"
              class="submit-btn"
            >
              <span v-if="!authStore.loading">🚀 立即登录</span>
              <span v-else>登录中...</span>
            </a-button>
          </a-form-item>

          <div class="auth-footer">
            <span>还没有账号？</span>
            <router-link to="/auth/register" class="link-btn">
              立即注册 →
            </router-link>
          </div>
        </a-form>
      </a-card>
      
      <div class="disclaimer">
        <div class="disclaimer-content">
          <warning-outlined class="warning-icon" />
          <p>
            本系统生成的 AI 角色发言可能包含错误、误导性信息或虚构内容，不代表真实人物观点。
            本平台内容仅供学术研究与娱乐演示，请勿作为专业建议。
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { UserOutlined, LockOutlined, WarningOutlined } from '@ant-design/icons-vue'

const authStore = useAuthStore()
const formState = reactive({
  username: '',
  password: ''
})

const onFinish = async (values: any) => {
  await authStore.login(values)
}
</script>

<style scoped>
.auth-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  padding: 24px;
}

.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  z-index: 0;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.6;
}

.blob-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  top: -100px;
  left: -100px;
  animation: float 8s ease-in-out infinite;
}

.blob-2 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -50px;
  right: -50px;
  animation: float 10s ease-in-out infinite reverse;
}

.blob-3 {
  width: 250px;
  height: 250px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  top: 50%;
  right: 10%;
  animation: float 12s ease-in-out infinite;
}

.auth-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 460px;
}

.brand-section {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  width: 80px;
  height: 80px;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
}

.logo-icon {
  width: 80px;
  height: 80px;
  object-fit: contain;
  border-radius: 20px;
}

.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: #6654F1;
  margin: 0 0 8px;
}

.brand-slogan {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.auth-card {
  width: 100%;
  border-radius: 20px;
  padding: 32px;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-title {
  font-size: 24px;
  color: #1a1a2e;
  font-weight: 700;
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: #888;
}

.auth-form {
  margin-bottom: 0;
}

.custom-input {
  border-radius: 12px;
}

.custom-input :deep(.ant-input) {
  border-radius: 12px;
  height: 48px;
  font-size: 15px;
}

.input-icon {
  color: #667eea;
  font-size: 18px;
}

.submit-btn {
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  margin-top: 8px;
  border-radius: 12px;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  border: none;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.submit-btn:active {
  transform: translateY(0);
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  margin-top: 24px;
  color: #666;
}

.link-btn {
  color: #667eea;
  font-weight: 600;
  margin-left: 6px;
  text-decoration: none;
  transition: all 0.3s ease;
}

.link-btn:hover {
  color: #764ba2;
  text-decoration: none;
}

.disclaimer {
  margin-top: 24px;
}

.disclaimer-content {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.warning-icon {
  color: #faad14;
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 2px;
}

.disclaimer-content p {
  margin: 0;
  font-size: 12px;
  color: #666;
  line-height: 1.6;
}

@keyframes float {
  0% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-20px);
  }
  100% {
    transform: translateY(0px);
  }
}

.float-animation {
  animation: float 6s ease-in-out infinite;
}

@media (max-width: 576px) {
  .auth-wrapper {
    padding: 16px;
  }
  
  .auth-card {
    padding: 24px;
  }
  
  .brand-title {
    font-size: 28px;
  }
  
  .blob {
    display: none;
  }
}
</style>
