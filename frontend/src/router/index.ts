// src/router/index.ts - 最终修复版本
import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import AdminLayout from '../layouts/AdminLayout.vue' 
import Dashboard from '../views/Dashboard.vue'
import DomainList from '../views/Domain/List.vue'
import Settings from '../views/Setting/Index.vue'
import ProjectList from '../views/Project/List.vue'
// import NameserverCheck from '../views/Setting/NameserverCheck.vue' // 移除导入

// 假设您已经定义或导入了 NotFoundComponent
import NotFoundComponent from '../views/NotFound.vue' // 假设 NotFound.vue 放在 views 目录下

const routes = [
  { path: '/login', component: Login },
  {
    path: '/',
    component: AdminLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '', // 根路径 '/' 对应的子路由（默认显示 Dashboard）
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: '指挥中心', subtitle: '实时监控全网流量调度状态' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: ProjectList,
        meta: { title: '项目分组管理', subtitle: '管理您的 A/B 域名池与分流策略' }
      },
      {
        path: 'domains',
        name: 'Domains',
        component: DomainList,
        meta: { title: '域名资产仓库', subtitle: '所有从 Cloudflare 导入的域名总览' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings,
        meta: { title: '系统设置', subtitle: '配置 API 密钥与第三方服务接入' }
      },
      {
        path: 'account/settings', 
        name: 'AccountSettings',
        component: () => import('../views/Setting/Account.vue'),
        meta: { title: '账户安全', hidden: true } 
      },
      // 【注意】：此处移除所有冲突路由
    ] 
  }, 
  
  // 【修复】：将 404 路由移至顶层 routes 数组的末尾
  {
    path: '/:catchAll(.*)', 
    name: 'NotFound',
    component: NotFoundComponent,
    meta: { title: '404' }
  }
] 

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 (依赖 permission.ts 文件)
// 注意：如果您的守卫逻辑在 permission.ts 中，这里保持不变
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('app_token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router