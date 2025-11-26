// src/router/index.ts - 添加新路由
import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import AdminLayout from '../layouts/AdminLayout.vue' 
import Dashboard from '../views/Dashboard.vue'
import DomainList from '../views/Domain/List.vue'
import Settings from '../views/Setting/Index.vue'
import ProjectList from '../views/Project/List.vue'
import NameserverCheck from '../views/Setting/NameserverCheck.vue' // 新增导入

const routes = [
  { path: '/login', component: Login },
  {
    path: '/',
    component: AdminLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
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
        path: 'account/settings', // 路径
        name: 'AccountSettings',
        component: () => import('../views/Setting/Account.vue'),
        // 关键点：加上 hidden: true，防止侧边栏自动渲染它 (如果你的侧边栏是动态生成的)
        // 如果你的侧边栏是手写的，那只要你不写 menu-item，它自然就不会出现
        meta: { title: '账户安全', hidden: true } 
      },
      // 新增路由
      {
        path: 'settings/nameserver-check',
        name: 'NameserverCheck',
        component: NameserverCheck,
        meta: { title: 'NS状态检查', subtitle: '监控域名 NS 记录生效状态' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫保持不变
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('app_token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router