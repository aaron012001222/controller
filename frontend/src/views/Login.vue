<template>
  <div class="login-container" oncontextmenu="return false;"> 
    
    <video autoplay muted loop playsinline preload="auto" class="bg-video" oncontextmenu="return false;">
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
          {{ loading ? '正在接入...' : '立即登入' }}
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
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const store = useUserStore()
const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

// 视频源路径，假设您将 bg_video.mp4 放在 /public/ 目录下
const videoSource = ref('/bg_video.mp4')
// 如果您也创建了 webm 格式，则使用此变量
// const videoSourceWebM = ref('/bg_video.webm') 

const handleLogin = async () => {
  if(!form.username || !form.password) {
    ElMessage.warning('请输入完整的账号和密码')
    return
  }
  loading.value = true
  
  // 增加一点人为延迟，让loading效果更明显，显得系统很专业
  await new Promise(r => setTimeout(r, 800)) 
  
  try {
    // 【核心修复】将 form 对象作为唯一的参数传递给 store.login
    await store.login(form) // <--- 只需要传递 form 对象
    
    // 假设 store.login 成功后会处理路由跳转
    
  } catch(e) {
    // 假设错误处理在 store/user.ts 的 login 方法中
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden; 
}

/* 视频样式优化 */
.bg-video {
  position: absolute;
  top: 50%;
  left: 50%;
  min-width: 100%; 
  min-height: 100%;
  width: auto;
  height: auto;
  z-index: 1; 
  transform: translate(-50%, -50%); 
  object-fit: cover; 
  filter: blur(5px) brightness(0.6); 
  transition: filter 1s ease-out; 
}

.login-box {
  z-index: 10; 
  padding: 40px 50px;
  width: 400px; 
  max-width: 90%;
  
  /* 玻璃效果 */
  background: rgba(255, 255, 255, 0.05); 
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.125);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); 
  text-align: center;
}

.title { 
  font-size: 28px; 
  font-weight: 800; 
  letter-spacing: 3px; 
  margin-bottom: 10px; 
  background: linear-gradient(to right, #fff, #a5f3fc); 
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle { 
  color: #94a3b8; 
  font-size: 15px; 
  margin-bottom: 35px; 
  font-weight: 300; 
  letter-spacing: 1px;
}

/* 修正 Element Plus 内部样式 */
:deep(.el-input__wrapper) {
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: none !important;
}
:deep(.el-input__inner) {
    color: #fff;
}
:deep(.el-input__inner::placeholder) {
    color: #a0a8b3;
}
:deep(.el-input__prefix) {
    color: #fff;
}

.btn-login { 
  width: 100%; 
  font-weight: bold; 
  margin-top: 15px; 
  height: 45px; 
  font-size: 16px;
  letter-spacing: 2px;
  background: linear-gradient(to right, #2563eb, #06b6d4); 
  border: none;
}
.btn-login:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.footer-tips {
  margin-top: 30px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.5px;
}
</style>