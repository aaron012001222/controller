<template>
  <div class="login-container">
    <video autoplay muted loop playsinline class="bg-video">
      <source :src="videoSource" type="video/mp4" />
      您的浏览器不支持视频背景。
    </video>

    <div class="login-box">
      <h2 class="title">TRAFFIC CONTROL</h2>
      <p class="subtitle">混合云流量中控系统</p>
      
      <el-form :model="form" size="large" @keyup.enter="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="管理员账号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" class="btn-login" @click="handleLogin" :loading="loading">
          {{ loading ? '正在接入...' : '立即接入' }}
        </el-button>
      </el-form>

      <div class="footer-tips">
        <span>Enterprise Grade Security | 256-bit Encrypted</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useUserStore } from '../store/user'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 核心修改：引入你的视频文件
// Vite 会自动处理这个路径，请确保文件 src/assets/bg_video.mp4 存在！
import videoSource from '../assets/bg_video.mp4'

const store = useUserStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: '' }) // 方便测试先填好账号

const handleLogin = async () => {
  if(!form.username || !form.password) {
    ElMessage.warning('请输入完整的账号和密码')
    return
  }
  loading.value = true
  // 增加一点人为延迟，让loading效果更明显，显得系统很专业
  await new Promise(r => setTimeout(r, 800)) 
  await store.login(form)
  loading.value = false
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  /* 给一个深色底色，防止视频加载慢时闪白屏 */
  background-color: #000; 
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  overflow: hidden;
  position: relative;
}

/* 核心修改：视频标签的样式 */
.bg-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  /* 关键属性：让视频像背景图一样覆盖全屏，不拉伸变形 */
  object-fit: cover;
  z-index: 0; /* 放在最底层 */
  opacity: 0.8; /* 可以稍微降低点透明度，让前景文字更清晰 */
}

.login-box {
  position: relative;
  z-index: 10; /* 确保在视频上面 */
  width: 420px;
  padding: 45px 40px;
  /* 核心修改：更高级的玻璃拟态效果 */
  background: rgba(17, 25, 40, 0.75); /* 深蓝灰色半透明 */
  backdrop-filter: blur(16px) saturate(180%); /* 毛玻璃模糊 + 饱和度提升 */
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.125);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); /* 更深的阴影 */
  text-align: center;
}

.title { 
  font-size: 28px; 
  font-weight: 800; 
  letter-spacing: 3px; 
  margin-bottom: 10px; 
  background: linear-gradient(to right, #fff, #a5f3fc); /* 文字渐变光泽 */
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle { color: #94a3b8; font-size: 15px; margin-bottom: 35px; font-weight: 300; letter-spacing: 1px;}

.btn-login { 
  width: 100%; 
  font-weight: bold; 
  margin-top: 15px; 
  height: 45px; 
  font-size: 16px;
  letter-spacing: 2px;
  background: linear-gradient(to right, #2563eb, #06b6d4); /* 按钮渐变色 */
  border: none;
}
.btn-login:hover {
  background: linear-gradient(to right, #1d4ed8, #0891b2);
  box-shadow: 0 0 15px rgba(6, 182, 212, 0.5); /* 悬停光晕 */
}

.footer-tips { margin-top: 25px; font-size: 12px; color: rgba(255, 255, 255, 0.3); letter-spacing: 1px; }

/* 深度定制 Element Plus 输入框样式 */
:deep(.el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}
/* 输入框聚焦时发光 */
:deep(.el-input__wrapper.is-focus) {
  border-color: #06b6d4;
  box-shadow: 0 0 0 1px #06b6d4 !important;
}
:deep(.el-input__inner) { color: #fff; height: 45px; }
:deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.5); }
</style>