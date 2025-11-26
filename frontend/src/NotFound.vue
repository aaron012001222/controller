<template>
  <div class="not-found-container">
    <el-card class="error-card">
      <div class="error-content">
        <div class="error-code">404</div>
        <h1 class="error-title">页面不存在或访问受限</h1>
        <p class="error-message">
          您请求的资源可能已被移除、名称已更改或您没有权限访问该路径。
          <br>
          如果多次尝试失败，请检查您的入口路径或联系管理员。
        </p>

        <div class="action-buttons">
          <el-button 
            type="primary" 
            size="large" 
            @click="goBack" 
            :icon="ArrowLeft"
          >
            返回上一页
          </el-button>
          <el-button 
            type="info" 
            size="large" 
            @click="goToHome" 
            :icon="HomeFilled"
            plain
          >
            系统首页
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft, HomeFilled } from '@element-plus/icons-vue'

const router = useRouter()

const goBack = () => {
  // 返回历史记录的上一页
  router.go(-1)
}

const goToHome = () => {
  // 跳转到仪表盘或登录页 (如果未登录)
  router.push('/')
}
</script>

<style scoped>
.not-found-container {
  /* 确保页面填满父容器 */
  height: 100%; 
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 50px 20px;
  background-color: #f0f2f5;
}

.error-card {
  max-width: 600px;
  width: 100%;
  padding: 40px;
  text-align: center;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
}

.error-code {
  font-size: 100px;
  font-weight: 800;
  color: #409EFF; /* Element Plus Primary Color */
  margin-bottom: 5px;
  /* 渐变效果，突出科技感 */
  background: linear-gradient(to right, #409EFF, #66b1ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
}

.error-title {
  font-size: 28px;
  color: #303133;
  margin-bottom: 15px;
  font-weight: 600;
}

.error-message {
  font-size: 16px;
  color: #909399;
  margin-bottom: 30px;
  line-height: 1.6;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 20px;
}
</style>