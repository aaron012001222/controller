<template>
  <div class="page-container">
    <el-container class="layout-container">
      <el-aside width="240px" class="sidebar">
        <div class="logo-area">
          <div class="logo-icon">🚀</div>
          <div class="logo-text">中转轮询系统</div>
        </div>
        
        <el-menu
          class="el-menu-vertical"
          :default-active="activeMenu"
          router
          unique-opened
          background-color="#fff"
          text-color="#333"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/" @click="$router.push('/')">
            <el-icon><Odometer /></el-icon>
            <span>控制中心</span>
          </el-menu-item>

          <el-menu-item index="/projects" @click="$router.push('/projects')">
            <el-icon><FolderOpened /></el-icon>
            <span>项目管理</span>
          </el-menu-item>

          <el-menu-item index="/domains" @click="$router.push('/domains')">
            <el-icon><List /></el-icon>
            <span>域名仓库</span>
          </el-menu-item>

          <el-sub-menu index="4">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </template>
            <el-menu-item index="/settings" @click="$router.push('/settings')">
              <el-icon><Key /></el-icon>
              <span>API 配置</span>
            </el-menu-item>
            </el-sub-menu>
        </el-menu>

        <div class="spacer"></div>

        <div class="logout-area">
          <el-menu class="logout-menu">
            <el-menu-item class="logout-item" @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-menu-item>
          </el-menu>
        </div>
      </el-aside>

      <el-container>
        <el-header style="padding: 0; height: auto;">
          <div class="main-header">
            <div class="page-info">
              <h2 class="page-title">{{ currentRouteTitle }}</h2>
              <p class="page-subtitle">{{ currentRouteSubtitle }}</p>
            </div>
            
            <div class="user-info">
              <el-dropdown @command="handleUserCommand">
                <span class="user-dropdown">
                  <el-avatar :size="32" icon="User" />
                  <span class="username">管理员</span>
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                    <el-dropdown-item command="account">账户安全</el-dropdown-item>
                    <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessage } from 'element-plus' //
import { 
  Odometer, 
  FolderOpened, 
  List, 
  Setting, 
  SwitchButton,
  Monitor,
  Key,
  ArrowDown,
  User
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 计算当前激活的菜单
const activeMenu = computed(() => {
  // 修正：如果当前路径是 /settings，则 activeMenu 应该是 /settings
  // 并在 el-menu-item index="4-1" 中使用 /settings
  if (route.path.startsWith('/settings')) {
    return '/settings';
  }
  return route.path
})

// 计算当前路由的标题和副标题
const currentRouteTitle = computed(() => {
  return route.meta.title || '流量调度系统'
})

const currentRouteSubtitle = computed(() => {
  return route.meta.subtitle || '高效管理您的流量分发'
})

// 处理退出登录
const handleLogout = () => {
  userStore.logout()
}

// 处理用户下拉菜单命令
const handleUserCommand = (command: string) => {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'profile') {
    ElMessage.info('功能开发中')
  } else if (command === 'account') {
    router.push('/account/settings')
  }
}

// 页面加载时检查认证状态
onMounted(() => {
  if (!userStore.token) {
    router.push('/login')
  }
})
</script>

<style scoped>
/* 样式保持不变 */
.page-container {
  height: 100vh;
  background: #f0f2f5;
}

.layout-container {
  height: 100%;
}

/* 侧边栏样式 */
.sidebar {
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
}

.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #eee;
  padding: 0 20px;
}

.logo-icon {
  font-size: 24px;
  margin-right: 10px;
}

.logo-text {
  font-weight: 900;
  font-size: 18px;
  color: #1a1a1a;
  letter-spacing: 1px;
}

.el-menu-vertical {
  border-right: none;
  margin-top: 10px;
  flex: 1;
}

.spacer {
  flex: 1;
}

.logout-area {
  border-top: 1px solid #f0f0f0;
}

.logout-menu {
  border: none;
}

.logout-item {
  color: #ff4d4f;
  height: 50px;
  line-height: 50px;
}

.logout-item:hover {
  background-color: #fff2f0;
}

/* 主头部样式 */
.main-header {
  background: #fff;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  min-height: 80px;
}

.page-info {
  flex: 1;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1f1f1f;
  line-height: 1.2;
}

.page-subtitle {
  margin: 8px 0 0;
  color: #8c8c8c;
  font-size: 14px;
  line-height: 1.4;
}

/* 用户信息样式 */
.user-info {
  display: flex;
  align-items: flex-start;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.3s;
}

.user-dropdown:hover {
  background-color: #f5f5f5;
}

.username {
  margin: 0 8px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

/* 主内容区样式 */
.main-content {
  padding: 24px;
  background: #f0f2f5;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 200px !important;
  }
  
  .logo-text {
    font-size: 16px;
  }
  
  .main-header {
    padding: 16px;
    flex-direction: column;
    gap: 16px;
  }
  
  .page-title {
    font-size: 20px;
  }
  
  .page-subtitle {
    font-size: 13px;
  }
  
  .main-content {
    padding: 16px;
  }
  
  .user-info {
    align-self: flex-end;
  }
}

/* 自定义滚动条 */
.main-content::-webkit-scrollbar {
  width: 6px;
}

.main-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.main-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.main-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 菜单项悬停效果 */
.el-menu-item:hover {
  background-color: #f0f7ff !important;
}

.el-menu-item.is-active {
  background-color: #ecf5ff !important;
  border-right: 3px solid #409EFF;
}

/* 子菜单样式 */
.el-sub-menu .el-menu-item {
  padding-left: 50px !important;
}

.el-sub-menu .el-menu-item:hover {
  background-color: #f0f7ff !important;
}

.el-sub-menu .el-menu-item.is-active {
  background-color: #ecf5ff !important;
  color: #409EFF;
}
</style>