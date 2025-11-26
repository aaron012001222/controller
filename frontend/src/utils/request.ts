import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router' // 引入路由实例，用于 401 跳转

// 创建 axios 实例
const service = axios.create({
  baseURL: '/api', // 指向你的 Python 后端
  timeout: 5000 // 请求超时
})

// request 拦截器：每次请求自动带上 Token
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('app_token')
    if (token) {
      // 设置 Authorization 头部
      config.headers.Authorization = `Bearer ${token}`
    }
    // 核心：DELETE 请求体通过 config.data 传递，Axios 会自动处理
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// response 拦截器：统一处理错误
service.interceptors.response.use(
  (response) => {
    // 检查自定义状态码 (例如 code: 200, code: 400)
    if (response.data && response.data.code && response.data.code !== 200) {
        ElMessage.error(response.data.message || '请求失败')
        return Promise.reject(new Error(response.data.message || '请求失败'))
    }
    return response.data
  },
  (error) => {
    // 检查 HTTP 状态码 (例如 401, 500)
    if (error.response) {
        // 如果后端返回 401 (未授权)，强制踢回登录页
        if (error.response.status === 401) {
            ElMessage.error('登录已过期，请重新登录')
            localStorage.removeItem('app_token')
            router.push('/login')
        } else {
            // 显示后端返回的错误信息
            ElMessage.error(error.response.data?.detail || error.response.data?.message || '网络请求错误')
        }
    } else {
        ElMessage.error('网络连接失败或超时')
    }
    return Promise.reject(error)
  }
)

export default service