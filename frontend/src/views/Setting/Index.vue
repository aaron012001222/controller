<template>
  <div class="settings-content-wrapper">
    
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover" class="setting-card">
          <template #header>
            <div class="card-header">
              <span><span class="icon-cf">☁️</span> Cloudflare API 配置</span>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="API Token (令牌)">
              <div style="display: flex; gap: 10px; align-items: flex-start;">
                <el-input v-model="form.cf_token" type="password" show-password placeholder="请输入 Edit Zone DNS 权限的 Token" style="flex: 1;" />
                <el-button type="info" @click="verifyCloudflareToken" :disabled="!form.cf_token">
                  <el-icon style="margin-right: 5px;"><Check /></el-icon> 验证 Token
                </el-button>
              </div>
              <div class="tips">
                获取 Token 后，**一定要先点击下方的“保存配置”按钮**，然后才能在域名页使用扫描功能。
                <br>推荐使用 API Token 而非 Global API Key，更安全。
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover" class="setting-card">
          <template #header>
            <div class="card-header">
              <span><span class="icon-ali">🟠</span> 阿里云配置 </span>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="AccessKey ID">
              <el-input v-model="form.aliyun_key" placeholder="LTAI..." />
            </el-form-item>
            <el-form-item label="AccessKey Secret">
              <el-input v-model="form.aliyun_secret" type="password" show-password placeholder="请输入 Secret" />
              <div class="tips">用于自动购买域名、修改 NS 记录以接入 CF。</div>
            </el-form-item>
          </el-form>

          <div style="margin-top: 20px; text-align: center;">
            <el-button 
                type="success" 
                size="default" 
                @click="openAliyunSyncModal" 
                :disabled="!form.aliyun_key"
            >
                <el-icon style="margin-right: 5px;"><Refresh /></el-icon> 
                扫描阿里云域名并接入 Cloudflare
            </el-button>
          </div>

        </el-card>
      </el-col>
    </el-row>
    
    <el-card shadow="hover" class="control-card" style="margin-top: 20px;">
        <template #header>
            <div class="card-header">
              <span><el-icon><Monitor /></el-icon> Nameserver 状态检查</span>
            </div>
        </template>
        
        <div class="bulk-actions">
            <el-button type="primary" @click="loadDomainStatus" :loading="loadingNs">
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

        <el-table 
            :data="domainList" 
            v-loading="loadingNs"
            @selection-change="handleSelectionChange"
            style="width: 100%; margin-top: 15px;"
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


    <div class="footer-actions">
      <el-button type="primary" size="large" @click="saveSettings" :loading="loading">保存所有配置</el-button>
    </div>

    <el-dialog v-model="aliyunSyncModalVisible" title="阿里云域名自动化接入" width="600px">
        <el-alert
          title="警告：该操作将修改您的阿里云域名 Nameserver (NS) 记录"
          type="warning"
          description="系统将尝试自动修改 NS 记录为 Cloudflare NS。请确保您已备份原始 NS，并理解修改后域名将由 Cloudflare 接管解析。"
          show-icon
          :closable="false"
          style="margin-bottom: 20px;"
        />
        
        <div v-if="isScanning">
            <el-skeleton animated />
            <p style="text-align: center; margin-top: 10px;">正在连接阿里云扫描您的域名资产...</p>
        </div>
        <div v-else-if="aliyunDomains.length > 0">
            <el-alert 
                title="重要提示：选择的域名将被自动配置到 Cloudflare" 
                type="warning" 
                description="系统将自动创建 Cloudflare Zone，并将阿里云的 NS 记录修改为 Cloudflare 指定的 NS。此操作不可逆，请谨慎选择。" 
                show-icon 
                :closable="false"
                style="margin-bottom: 15px;"
            />
            <el-table 
                :data="aliyunDomains" 
                style="width: 100%" 
                max-height="400"
                @selection-change="handleAliyunSelection"
            >
                <el-table-column type="selection" width="55" />
                <el-table-column prop="name" label="域名名称" min-width="200" />
                <el-table-column prop="status" label="状态" width="100" />
                <el-table-column prop="region" label="区域" width="120" />
            </el-table>
            <p style="margin-top: 15px; font-size: 13px; color: #666;">
                已选择 {{ selectedAliyunDomains.length }} 个域名。
            </p>
        </div>
        <div v-else>
            <el-empty description="未发现域名或连接失败，请检查您的密钥配置。" />
        </div>

        <template #footer>
            <el-button @click="aliyunSyncModalVisible = false">取消</el-button>
            <el-button 
                type="success" 
                :disabled="selectedAliyunDomains.length === 0" 
                :loading="isSettingUp"
                @click="startAliyunSetup"
            >
                确认同步 {{ selectedAliyunDomains.length }} 个域名到 Cloudflare
            </el-button>
        </template>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" :title="'域名日志 - ' + currentDomainNs?.domain" width="800px">
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
import request from '../../utils/request'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'
import { 
  Odometer, List, Setting, SwitchButton, FolderOpened, Refresh, RefreshRight, Check, Monitor
} from '@element-plus/icons-vue'

// API 配置相关变量
const loading = ref(false)
const form = reactive({
  cf_token: '',
  aliyun_key: '',
  aliyun_secret: ''
})

// 阿里云自动化相关变量
const aliyunSyncModalVisible = ref(false)
const isScanning = ref(false)
const isSettingUp = ref(false)
const aliyunDomains = ref<any[]>([]) 
const selectedAliyunDomains = ref<string[]>([]);

// 【======= 整合自 NameserverCheck.vue 的变量 =======】
const loadingNs = ref(false) 
const checking = ref(false)
const loadingLogs = ref(false)
const filterStatus = ref('')

const domainList = ref<any[]>([])
const selectedDomains = ref<any[]>([])
const domainLogs = ref<any[]>([])
const logDialogVisible = ref(false)
const currentDomainNs = ref<any>(null)


// 加载已保存的设置
const loadSettings = async () => {
  try {
    const res: any = await request.get('/settings')
    if (res.code === 200 && res.data) {
      form.cf_token = res.data.cf_token || ''
      form.aliyun_key = res.data.aliyun_key || ''
      form.aliyun_secret = res.data.aliyun_secret || ''
    }
  } catch (e) {
    // console.error(e)
  }
}

// 保存设置
const saveSettings = async () => {
  loading.value = true
  try {
    const res: any = await request.post('/settings', form)
    if (res.code === 200) {
      ElMessage.success('系统设置已更新')
    }
  } catch (e) {
    // error handled by request.ts
  } finally {
    loading.value = false
  }
}

// 验证 Cloudflare Token
const verifyCloudflareToken = async () => {
    if (!form.cf_token) {
        return ElMessage.warning('请先输入 Cloudflare Token')
    }
    
    try {
        const res: any = await request.get('/cloudflare/verify_token');
        if (res.code === 200 && res.valid) {
            ElNotification.success({
                title: 'Token 验证成功',
                message: `权限: ${res.permissions} | 域名数量: ${res.zone_count}`,
                duration: 5000
            });
        } else {
            let errorMessage = res.message || 'Token 验证失败';
            if (res.error_code) {
                errorMessage += ` (错误码: ${res.error_code})`;
            }
            if (res.suggested_fix) {
                errorMessage += `\n建议: ${res.suggested_fix}`;
            }
            
            ElNotification.error({
                title: 'Token 验证失败',
                message: errorMessage,
                duration: 8000
            });
        }
    } catch (error: any) {
        const errorMsg = error.response?.data?.detail || error.message || '网络错误';
        ElMessage.error('验证失败: ' + errorMsg);
    }
};

// 自动化接入入口 (触发扫描)
const openAliyunSyncModal = async () => {
    if(!form.aliyun_key || !form.aliyun_secret) {
        return ElMessage.warning('请先在设置页保存阿里云 Access Key 和 Secret！')
    }
    aliyunSyncModalVisible.value = true
    await scanAliyunDomains();
}

// 实际调用后端扫描 API
const scanAliyunDomains = async () => {
    isScanning.value = true
    aliyunDomains.value = [];
    selectedAliyunDomains.value = [];
    try {
        const res: any = await request.post('/aliyun/scan_domains');
        if (res.code === 200 && res.data) {
            aliyunDomains.value = res.data;
            ElMessage.success(`成功扫描到 ${res.data.length} 个域名。`);
        } else {
            ElMessage.error(res.detail || '扫描失败，请检查阿里云密钥。');
        }
    } catch (error: any) {
        const errorMsg = error.response?.data?.detail || error.message || '网络错误';
        ElMessage.error(`扫描失败: ${errorMsg}`);
        console.error('阿里云扫描错误:', error);
    } finally {
        isScanning.value = false;
    }
}

// 处理表格选择事件
const handleAliyunSelection = (selection: any[]) => {
    selectedAliyunDomains.value = selection.map(item => item.name);
};

// 启动阿里云接入流程
const startAliyunSetup = async () => {
    isSettingUp.value = true;
    try {
        const res: any = await request.post('/aliyun/setup_domains', {
            domain_names: selectedAliyunDomains.value
        });
        
        if (res.code === 200) {
            ElNotification.success({
                title: '同步启动成功', 
                message: `${res.message} 请等待 DNS 解析生效。`, 
                duration: 8000
            });
            aliyunSyncModalVisible.value = false;
            
            selectedAliyunDomains.value = [];
            aliyunDomains.value = [];

            // 接入成功后刷新 NS 状态列表
            await loadDomainStatus()
        } else {
            ElMessage.error(res.message || '同步失败。');
        }
    } catch (error: any) {
        const errorMsg = error.response?.data?.detail || error.message || '网络或API错误';
        ElMessage.error(`同步失败: ${errorMsg}`);
        console.error('阿里云接入错误:', error);
    } finally {
        isSettingUp.value = false;
    }
};

// 【======= 整合自 NameserverCheck.vue 的函数 (NS 检查逻辑) =======】

const loadDomainStatus = async () => {
  loadingNs.value = true
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
    loadingNs.value = false
  }
}

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
      await loadDomainStatus()
    }
  } catch (error: any) {
    ElMessage.error('检查失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    checking.value = false
  }
}

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

const showDomainLogs = async (domain: any) => {
  currentDomainNs.value = domain
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

const handleSelectionChange = (selection: any[]) => {
  selectedDomains.value = selection
}

const getStatusType = (status: string) => {
  const typeMap: any = {
    'active': 'success',
    'pending': 'warning',
    'failed': 'danger',
    'unknown': 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const textMap: any = {
    'active': '已生效',
    'pending': '等待生效',
    'failed': '检查失败',
    'unknown': '未知'
  }
  return textMap[status] || status
}

const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}
// ===================================================

onMounted(() => {
  loadSettings()
  loadDomainStatus() // 【新增：加载 NS 检查列表】
})
</script>

<style scoped>
/* 样式保持一致 */
.settings-content-wrapper { padding-top: 5px; }

.page-container { height: 100vh; background: #f0f2f5; }
.layout-container { height: 100%; }
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
}
.logo-icon { font-size: 24px; margin-right: 10px; }
.logo-text { font-weight: 900; font-size: 18px; color: #1a1a1a; letter-spacing: 1px; }
.el-menu-vertical { border-right: none; margin-top: 10px; flex: 1; }
.spacer { flex: 1; }
.logout-item { border-top: 1px solid #f0f0f0; color: #ff4d4f; }
.main-content { padding: 24px; }
.top-bar { margin-bottom: 24px; }
.top-bar h2 { margin: 0; font-size: 24px; color: #1f1f1f; }
.subtitle { margin: 5px 0 0; color: #8c8c8c; font-size: 13px; }

.setting-card { height: 100%; }
.card-header { font-weight: bold; font-size: 16px; }
.tips { font-size: 12px; color: #999; margin-top: 5px; line-height: 1.4; }
.footer-actions { margin-top: 30px; display: flex; justify-content: flex-end; }

/* 【新增：NameserverCheck.vue 样式】 */
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