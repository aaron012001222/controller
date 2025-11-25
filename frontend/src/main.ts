import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// 引入 Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 引入 Element Plus Icons (我们修复了大小写问题)
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// 引入 Pinia 和 Router (这是核心，必须正确初始化)
import { createPinia } from 'pinia'
import router from './router'
// 确保路由守卫被引入
import './router/permission' 


const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 确保 Pinia 和 Router 在 mount 之前使用
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')