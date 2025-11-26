<template>
  <div class="p-6">
    <el-card class="box-card max-w-2xl mx-auto">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="text-lg font-bold">管理员账户设置</span>
          <el-tag type="danger" effect="dark">高敏感操作</el-tag>
        </div>
      </template>
      
      <el-alert
        title="修改提示"
        type="warning"
        description="修改用户名或密码后，系统将强制退出登录，您需要使用新凭证重新进入。"
        show-icon
        :closable="false"
        class="mb-6"
      />

      <el-form :model="form" label-width="100px" size="large">
        <el-form-item label="新用户名">
          <el-input v-model="form.username" placeholder="请输入新的登录账号" />
        </el-form-item>
        
        <el-form-item label="新密码">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入新的登录密码" 
            show-password 
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="onSubmit" :loading="loading" class="w-full">
            确认修改并重新登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '', // 留空让用户自己填，或者你可以从 store 获取当前用户名预填
  password: ''
})

const onSubmit = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('用户名和密码都不能为空')
    return
  }

  try {
    await ElMessageBox.confirm(
      '确定要修改登录账号和密码吗？修改后需要重新登录。',
      '安全警告',
      {
        confirmButtonText: '确定修改',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    loading.value = true
    // 调用我们在 main.py 里写的接口
    const res: any = await request.post('/user/update', form)
    
    ElMessage.success(res.message || '修改成功，请重新登录')
    
    // 清除本地 Token
    localStorage.removeItem('app_token')
    
    // 跳转回登录页
    router.push('/login')
    
  } catch (error) {
    // 取消或报错
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>