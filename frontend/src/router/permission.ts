// src/router/permission.ts

import router from './index'

// 全局前置守卫：用于权限校验
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('app_token')
  
  // requiresAuth 在 router/index.ts 的路由配置中定义
  if (to.meta.requiresAuth && !token) {
    // 如果需要登录但没有 Token，强制跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 如果已登录但尝试访问登录页，重定向到首页
    next('/')
  } else {
    // 其他情况放行
    next()
  }
})