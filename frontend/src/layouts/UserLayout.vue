<template>
  <div class="user-layout-container">
    <div class="user-layout-mask"></div>
    <div class="user-layout-content">
      <div class="main-content">
        <router-view />
      </div>

      <div class="user-layout-footer">
        <div class="links">
          <a href="#">帮助</a>
          <a href="#">隐私</a>
          <a href="#">条款</a>
        </div>
        <div class="copyright">
          Copyright &copy; 2026 Trae AI
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-layout-container {
  width: 100%;
  min-height: 100vh;
  background: #f2f7f3;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.user-layout-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(2px);
  z-index: 1;
}

.user-layout-content {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 450px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 顶部header已移除 */

.main-content {
  width: 100%;
  margin-bottom: 40px;
}

.user-layout-footer {
  width: 100%;
  text-align: center;
}

.user-layout-footer .links {
  margin-bottom: 8px;
  font-size: 14px;
}

.user-layout-footer .links a {
  color: #787f84;
  transition: all 0.3s;
  text-decoration: none;
  margin: 0 12px;
}

.user-layout-footer .links a:hover {
  color: #2d3236;
}

.user-layout-footer .copyright {
  color: #787f84;
  font-size: 14px;
}

@media (max-width: 576px) {
  .user-layout-content {
    width: 95%;
    padding: 16px;
  }
  
  /* 移动端标题样式已移除 */
}
</style>
