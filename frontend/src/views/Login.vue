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
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 【核心修复 2】: 使用 import 语句获取 assets 目录下的视频文件，Vite/Webpack 会处理路径
import videoFile from '../assets/bg_video.mp4'; 

const store = useUserStore()
const form = reactive({
  username: '',
  password: ''
})
const loading = ref(false)

// 【核心修复 3】: 将 import 得到的正确路径赋值给 videoSource
const videoSource = ref(videoFile) 

// 处理登录逻辑
const handleLogin = async () => {
  if(!form.username || !form.password) {
    ElMessage.warning('请输入完整的账号和密码')
    return
  }
  loading.value = true
  
  // 增加一点人为延迟，让 loading 效果更明显
  await new Promise(r => setTimeout(r, 800)) 
  
  try {
    // 【核心修复 4】: 传递整个 form 对象作为单个参数
    await store.login(form) 
    
  } catch(e) {
    // 假设错误处理在 store/user.ts 的 login 方法中
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
/* 容器样式 */
.login-container { 
  position: relative; 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  min-height: 100vh; 
  overflow: hidden; 
  background-color: #0d1117; /* 深色背景作为视频加载时的备用 */
}

/* 视频背景样式 */
.bg-video {
  position: absolute;
  top: 50%;
  left: 50%;
  min-width: 100%;
  min-height: 100%;
  width: auto;
  height: auto;
  z-index: 1; /* 确保视频在底层 */
  transform: translate(-50%, -50%);
  object-fit: cover; /* 确保视频覆盖整个区域 */
}

/* 登录框样式 - 玻璃效果 */
.login-box {
  z-index: 2; /* 确保登录框在视频之上 */
  position: relative;
  padding: 40px;
  width: 400px; 
  max-width: 90%;
  
  /* 玻璃效果核心 CSS */
  background: rgba(255, 255, 255, 0.05); /* 半透明背景 */
  backdrop-filter: blur(20px) saturate(180%); /* 景深模糊 */
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.125); /* 边框光泽 */
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); /* 更深的阴影 */
  text-align: center;
}

/* 标题样式 - 渐变光泽 */
.title { 
  font-size: 28px; 
  font-weight: 800; 
  letter-spacing: 3px; 
  margin-bottom: 10px; 
  background: linear-gradient(to right, #fff, #a5f3fc); /* 文字渐变光泽 */
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 副标题样式 */
.subtitle { 
  color: #94a3b8; 
  font-size: 15px; 
  margin-bottom: 35px; 
  font-weight: 300; 
  letter-spacing: 1px;
}

/* 登录按钮样式 */
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

/* Element Plus 内部样式穿透调整 */
/* 修正 el-input 的透明度，确保输入框清晰可见 */
:deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.1); 
  border: 1px solid rgba(255, 255, 255, 0.1); 
  box-shadow: none !important; /* 移除默认阴影 */
}

/* 修正输入文字颜色为白色 */
:deep(.el-input__inner) {
  color: #fff; 
}

/* 底部提示信息样式 */
.footer-tips {
  margin-top: 25px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.5px;
}
</style>