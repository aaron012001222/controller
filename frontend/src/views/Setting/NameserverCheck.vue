<!-- src/views/Setting/NameserverCheck.vue -->
<template>
  <div class="nameserver-check-wrapper">
    <div class="top-bar">
      <h2><el-icon><Monitor /></el-icon> Nameserver 状态检查</h2>
      <p class="subtitle">监控域名从阿里云接入 Cloudflare 的 NS 记录生效状态</p>
    </div>

    <el-card shadow="hover" class="control-card">
      <template #header>
        <div class="card-header">
          <span>批量操作</span>
        </div>
      </template>
      
      <div class="bulk-actions">
        <el-button type="primary" @click="loadDomainStatus" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新状态列表
        </el-button>
        
        <el-button type="success" @click="manualCheckSelected" :disabled="selectedDomains.length === 0" :loading="checking">
          <el-icon><Check /></el-icon> 手动检查选中域名 ({{ selectedDomains.length }})
        </el-button>

        <el-button type="info" @click="initNsStatus">
          <el-icon><Setting /></el-icon> 初始化 NS 状态
        </el-button>

        <div class="filter-section">
          <el-select v-model="filterStatus" placeholder="筛选状态" style="width: 150px;" @change="loadDomainStatus">
            <el-option label="全部状态" value=""></el-option>
            <el-option label="等待生效" value="pending"></el-option>
            <el-option label="已生效" value="active"></el-option>
            <el-option label="检查失败" value="failed"></el-option>
            <el-option label="未知状态" value="unknown"></el-option>
          </el-select>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover" class="table-card">
      <template #header>
        <div class="card-header">
          <span>域名状态列表 ({{ domainList.length }})</span>
        </div>
      </template>

      <el-table 
        :data="domainList" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
        stripe
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="domain" label="域名" min-width="200">
          <template #default="scope">
            <div class="domain-name">
              <span>{{ scope.row.domain }}</span>
              <el-tag v-if="scope.row.project_id" size="small" effect="plain">已分配</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="ns_status" label="NS状态" width="120">
          <template #default="scope">
            <el-tag 
              :type="getStatusType(scope.row.ns_status)"
              effect="light"
            >
              {{ getStatusText(scope.row.ns_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="ns_servers" label="预期NS" min-width="200">
          <template #default="scope">
            <div class="ns-servers">
              <div v-for="ns in (scope.row.ns_servers || '').split(',')" :key="ns" class="ns-item">
                {{ ns }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="last_ns_check" label="最后检查" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.last_ns_check) }}
          </template>
        </el-table-column>

        <el-table-column prop="ns_check_count" label="检查次数" width="100">
          <template #default="scope">
            {{ scope.row.ns_check_count || 0 }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button 
              size="small" 
              @click="showDomainLogs(scope.row)"
              :loading="scope.row.loadingLogs"
            >
              日志
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 域名日志对话框 -->
    <el-dialog v-model="logDialogVisible" :title="'域名日志 - ' + currentDomain?.domain" width="800px">
      <el-table :data="domainLogs" v-loading="loadingLogs" style="width: 100%">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="check_type" label="检查类型" width="120">
          <template #default="scope">
            <el-tag size="small">{{ scope.row.check_type }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="message" label="详细信息" show-overflow-tooltip />
      </el-table>

      <template #footer>
        <el-button @click="logDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Monitor, Refresh, Check, Setting } from '@element-plus/icons-vue'
import request from '../../utils/request'

const loading = ref(false)
const checking = ref(false)
const loadingLogs = ref(false)
const filterStatus = ref('')

const domainList = ref<any[]>([])
const selectedDomains = ref<any[]>([])
const domainLogs = ref<any[]>([])
const logDialogVisible = ref(false)
const currentDomain = ref<any>(null)

// 加载域名状态列表
const loadDomainStatus = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    
    const res: any = await request.get('/domain_status', { params })
    if (res.code === 200) {
      domainList.value = res.data
      ElMessage.success(`已加载 ${res.data.length} 个域名`)
    }
  } catch (error: any) {
    ElMessage.error('加载域名状态失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 手动检查选中的域名
const manualCheckSelected = async () => {
  if (selectedDomains.value.length === 0) {
    ElMessage.warning('请先选择要检查的域名')
    return
  }

  checking.value = true
  try {
    const domainIds = selectedDomains.value.map(d => d.id)
    const res: any = await request.post('/domain_status/check', {
      domain_ids: domainIds
    })
    
    if (res.code === 200) {
      ElMessage.success(res.message)
      // 刷新列表
      await loadDomainStatus()
    }
  } catch (error: any) {
    ElMessage.error('检查失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    checking.value = false
  }
}

// 初始化NS状态
const initNsStatus = async () => {
  try {
    await ElMessageBox.confirm(
      '此操作将初始化所有域名的NS状态，主要用于系统升级后的状态修复。确定要继续吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res: any = await request.post('/domain_status/init_ns_status')
    if (res.code === 200) {
      ElMessage.success(res.message)
      await loadDomainStatus()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('初始化失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 显示域名日志
const showDomainLogs = async (domain: any) => {
  currentDomain.value = domain
  logDialogVisible.value = true
  loadingLogs.value = true
  
  try {
    const res: any = await request.get(`/domain_status/${domain.id}/logs`)
    if (res.code === 200) {
      domainLogs.value = res.data
    }
  } catch (error: any) {
    ElMessage.error('加载日志失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingLogs.value = false
  }
}

// 表格选择处理
const handleSelectionChange = (selection: any[]) => {
  selectedDomains.value = selection
}

// 状态类型映射
const getStatusType = (status: string) => {
  const typeMap: any = {
    'active': 'success',
    'pending': 'warning',
    'failed': 'danger',
    'unknown': 'info'
  }
  return typeMap[status] || 'info'
}

// 状态文本映射
const getStatusText = (status: string) => {
  const textMap: any = {
    'active': '已生效',
    'pending': '等待生效',
    'failed': '检查失败',
    'unknown': '未知'
  }
  return textMap[status] || status
}

// 日期格式化
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDomainStatus()
})
</script>

<style scoped>
.nameserver-check-wrapper {
  padding: 20px;
}

.top-bar {
  margin-bottom: 24px;
}

.top-bar h2 {
  margin: 0;
  font-size: 24px;
  color: #1f1f1f;
  display: flex;
  align-items: center;
  gap: 8px;
}

.subtitle {
  margin: 5px 0 0;
  color: #8c8c8c;
  font-size: 13px;
}

.control-card {
  margin-bottom: 20px;
}

.bulk-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-section {
  margin-left: auto;
}

.table-card {
  margin-bottom: 20px;
}

.card-header {
  font-weight: bold;
  font-size: 16px;
}

.domain-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ns-servers {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ns-item {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #666;
}
</style>