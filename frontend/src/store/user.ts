import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '../utils/request'
import router from '../router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('app_token') || '')

  const login = async (form: any) => {
    try {
      const res: any = await request.post('/login', form)
      token.value = res.access_token
      localStorage.setItem('app_token', res.access_token)
      router.push('/') // 登录成功跳到后台
      return true
    } catch (e) {
      return false
    }
  }

  const logout = () => {
    token.value = ''
    localStorage.removeItem('app_token')
    router.push('/login')
  }

  return { token, login, logout }
})