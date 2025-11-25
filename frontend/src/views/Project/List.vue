<template>
  <div class="project-content-wrapper">
    <!-- 恢复顶部操作栏，但只保留按钮，不包含重复标题 -->
    <div class="top-bar" style="display: flex; justify-content: flex-end; margin-bottom: 24px;">
      <el-button type="primary" size="large" @click="createDialogVisible = true">
        <el-icon style="margin-right:5px"><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <el-row :gutter="24" class="project-grid">
      <el-col :span="6" v-for="proj in projects" :key="proj.id">
        <el-card shadow="hover" class="project-card">
          <div class="card-header">
            <span class="proj-name" @click="openProject(proj)">{{ proj.name }}</span>
            <div style="display: flex; gap: 8px; align-items: center;">
              <el-button link type="danger" size="small" @click="confirmDeleteProject(proj)">移除项目</el-button>
              <el-tag type="success" size="small" effect="dark">运行中</el-tag>
            </div>
          </div>
          <div class="card-body" @click="openProject(proj)">
            <div class="stat-item">
              <span>A池 (入口)</span>
              <strong>{{ proj.entry_count || 0 }} 个</strong>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span>B池 (落地)</span>
              <strong>{{ proj.landing_count || 0 }} 条</strong>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="24" v-if="projects.length === 0">
        <el-empty description="暂无项目，请点击右上角新建" />
      </el-col>
    </el-row>

    <el-dialog v-model="createDialogVisible" title="新建项目" width="400px">
      <el-input v-model="newProjectName" placeholder="请输入项目名称 (如: 兼职粉引流-01)" />
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createProject">确定创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="drawerVisible" :title="currentProject.name" size="65%">
      <template #header>
        <div style="font-size: 18px; font-weight: bold;">
          📂 {{ currentProject.name }}
          <el-tag size="small" type="info" style="margin-left: 10px">ID: {{ currentProject.id }}</el-tag>
        </div>
      </template>
      
      <el-tabs v-model="activeTab" type="border-card">
        
        <el-tab-pane label="🅰️ A池 (入口域名)" name="entry">
          <div class="tab-action">
             <el-button 
               type="danger" 
               size="default" 
               :disabled="selectedEntryDelete.length === 0" 
               @click="bulkDeleteEntry"
             >
               批量解绑 ({{ selectedEntryDelete.length }} 个域名)
             </el-button>
             
             <div style="margin-top: 15px; display: flex; gap: 10px; align-items: center;">
                <p class="tab-tip" style="margin:0;">将闲置域名绑定到此项目：</p>
                <el-select 
                  v-model="selectedEntryIds" 
                  placeholder="选择闲置域名..." 
                  style="width: 300px" 
                  multiple 
                  filterable 
                  collapse-tags
                >
                  <el-option v-for="d in unusedDomains" :key="d.id" :label="d.domain" :value="d.id" />
                </el-select>
                <el-button type="primary" @click="bindEntryDomain" :disabled="selectedEntryIds.length === 0">
                  批量绑定
                </el-button>
             </div>
          </div>
          
          <el-table 
            :data="currentProject.entry_domains" 
            stripe 
            border 
            @selection-change="handleEntrySelection" 
            style="margin-top: 15px"
            max-height="450"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="domain" label="入口域名" min-width="150"/>
            
            <el-table-column label="路径" width="120">
                <template #default="{ row }">
                    <span :class="{'path-set': row.custom_path}">/{{ row.custom_path || '—' }}</span>
                </template>
            </el-table-column>
            
            <el-table-column prop="provider" label="线路" width="80" />
            
            <el-table-column label="状态" width="120" align="center">
              <template #default="scope">
                <div class="status-badge" :class="scope.row.status==='ok'?'ok':'banned'">
                  {{ scope.row.status }}
                </div>
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="120">
                <template #default="{ row }">
                    <el-button link type="primary" size="small" @click="openPathEditModal(row, currentProject.id)">
                        编辑路径
                    </el-button>
                </template>
            </el-table-column>
          </el-table>
          <div v-if="currentProject.entry_domains && currentProject.entry_domains.length === 0" style="text-align: center; color: #999; padding: 20px;">
              A池暂无入口域名，请从上方闲置池中选择绑定。
          </div>
        </el-tab-pane>

        <el-tab-pane label="🅱️ B池 (落地页)" name="landing">
          <div class="tab-action">
            <el-button 
                type="warning" 
                size="default" 
                :loading="isChecking"
                style="margin-right: 15px;"
                @click="manualCheck(currentProject.id)"
            >
                <el-icon style="margin-right: 5px;"><RefreshRight /></el-icon> 
                手动检测状态 (同步)
            </el-button>
            
            <el-button 
              type="danger" 
              size="default" 
              :disabled="selectedLandingDelete.length === 0" 
              @click="bulkDeleteLanding"
            >
              批量删除 ({{ selectedLandingDelete.length }} 个链接)
            </el-button>

            <p class="tab-tip" style="margin-top: 15px; margin-bottom: 10px;">批量添加真实的业务落地页 URL (一行一个)：</p>
            <div style="display: flex; gap: 10px; flex-direction: column; width: 100%;">
              <el-input 
                v-model="newLandingUrl" 
                type="textarea" 
                :rows="5" 
                placeholder="输入落地页 URL (一行一个)&#10;例: https://page1.com&#10;例: https://page2.com" 
              />
              <el-button type="success" @click="addLandingUrl" :disabled="!newLandingUrl">
                批量添加链接
              </el-button>
            </div>
          </div>
          
          <el-table 
            :data="currentProject.landing_domains" 
            stripe 
            border 
            @selection-change="handleLandingSelection" 
            style="margin-top: 15px"
            max-height="450"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="url" label="跳转目标 URL" />
            <el-table-column label="状态" width="120" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'ok' ? 'success' : 'danger'" size="small" effect="plain">
                  {{ scope.row.status === 'ok' ? '✅ 正常' : '❌ 失效' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="currentProject.landing_domains && currentProject.landing_domains.length === 0" style="text-align: center; color: #999; padding: 20px;">
              B池暂无落地页 URL，请在上方区域批量添加。
          </div>
        </el-tab-pane>
        
      </el-tabs>
    </el-drawer>
    
    <el-dialog 
        v-model="pathEditModalVisible" 
        title="编辑域名访问路径" 
        width="400px"
    >
        <p>为域名 <strong>{{ currentDomainToEdit.domain }}</strong> 设置自定义路径。</p>
        <el-form label-position="top">
            <el-form-item label="自定义路径 (例如: go, 6位数字字母组合)">
                <el-input v-model="currentDomainToEdit.custom_path" placeholder="留空则直接通过域名访问" />
                <div class="tips">用户必须访问 <code>{{ currentDomainToEdit.domain }}/{{ currentDomainToEdit.custom_path || '[路径]' }}</code> 才能跳转。</div>
            </el-form-item>
        </el-form>

        <template #footer>
            <el-button @click="currentDomainToEdit.custom_path = generateRandomPath()">随机生成 6 位路径</el-button>
            <el-button @click="pathEditModalVisible = false">取消</el-button>
            <el-button type="primary" @click="executePathUpdate">保存路径</el-button>
        </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus' 
import { 
  Odometer, List, Setting, SwitchButton, FolderOpened, Plus,
  RefreshRight 
} from '@element-plus/icons-vue'

interface EntryDomain {
    id: number
    domain: string
    provider: string
    status: string
    custom_path: string 
}

// --- 变量定义 ---
const projects = ref<any[]>([])
const createDialogVisible = ref(false)
const newProjectName = ref('')
const currentProject = ref<any>({})
const activeTab = ref('entry')
const unusedDomains = ref<any[]>([])
const selectedEntryIds = ref<number[]>([])
const newLandingUrl = ref('') 
const selectedEntryDelete = ref<any[]>([])
const selectedLandingDelete = ref<any[]>([])
const isChecking = ref(false)
const drawerVisible = ref(false)
const pathEditModalVisible = ref(false)
const currentDomainToEdit = ref<Partial<EntryDomain> & { project_id?: number }>({})

// 随机路径生成器
const generateRandomPath = (length = 6): string => {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
};

// 1. 获取项目列表
const fetchProjects = async () => {
  try {
    const res: any = await request.get('/projects') 
    if(res.code === 200) {
        projects.value = res.data
    }
  } catch(e) {
       ElMessage.error('获取项目列表失败');
  }
}

// 2. 创建项目
const createProject = async () => {
  if(!newProjectName.value) return ElMessage.warning("请输入项目名称")
  try {
    const res: any = await request.post('/projects', { name: newProjectName.value })
    
    if (res.code === 200) {
        ElMessage.success('项目创建成功')
        createDialogVisible.value = false
        newProjectName.value = ''
        fetchProjects()
    }
  } catch(e) {
       ElMessage.error('创建项目失败');
  }
}

// 3. 打开详情抽屉
const openProject = async (proj: any) => {
  try {
    const res: any = await request.get(`/projects/${proj.id}`)
    if(res.code === 200) {
      currentProject.value = res.data
      drawerVisible.value = true
      selectedEntryIds.value = []
      selectedEntryDelete.value = []
      selectedLandingDelete.value = []
      loadUnusedDomains() 
    }
  } catch(e) {}
}

// 4. 加载闲置域名
const loadUnusedDomains = async () => {
  const res: any = await request.get('/domains/unused')
  if(res.code === 200) unusedDomains.value = res.data
}

// 5. 核心：批量绑定 A 池
const bindEntryDomain = async () => {
  if(selectedEntryIds.value.length === 0) return ElMessage.warning("请选择至少一个域名")
  try {
    const res: any = await request.post(`/projects/${currentProject.value.id}/bind_entry`, {
      domain_ids: selectedEntryIds.value 
    })
    
    ElNotification.success(res.message)
    selectedEntryIds.value = []
    openProject(currentProject.value) 
    fetchProjects(); 
  } catch(e) {}
}

// 6. 核心：批量添加 B 池
const addLandingUrl = async () => {
  if(!newLandingUrl.value) return ElMessage.warning("请输入 URL")
  try {
    const res: any = await request.post(`/projects/${currentProject.value.id}/landing`, {
      urls: newLandingUrl.value 
    })
    
    ElNotification.success(res.message)
    newLandingUrl.value = ''
    openProject(currentProject.value)
  } catch(e) {}
}

// --- 批量删除操作 ---

// 7. A池表格选择事件处理
const handleEntrySelection = (val: any[]) => {
    selectedEntryDelete.value = val
}

// 8. B池表格选择事件处理
const handleLandingSelection = (val: any[]) => {
    selectedLandingDelete.value = val
}

// 9. 核心：批量解绑 A 池域名
const bulkDeleteEntry = () => {
    const ids = selectedEntryDelete.value.map(d => d.id)
    if (ids.length === 0) return

    ElMessageBox.confirm(`确定要从项目中批量解绑选中的 ${ids.length} 个域名吗？`, '确认批量解绑', {
        type: 'warning'
    }).then(async () => {
        const res: any = await request.delete(`/projects/${currentProject.value.id}/entry/bulk`, { 
            data: { entry_ids: ids } 
        });
        if (res.code === 200) {
            ElMessage.success(res.message);
            openProject(currentProject.value); 
            fetchProjects(); 
        }
    }).catch(() => {});
}

// 10. 核心：批量删除 B 池落地页 (修复 422 错误的关键)
const bulkDeleteLanding = () => {
    const landingIds = selectedLandingDelete.value.map(l => l.id)
    if (landingIds.length === 0) return

    ElMessageBox.confirm(`确定要批量删除选中的 ${landingIds.length} 个落地页 URL 吗？`, '确认批量删除', {
        type: 'warning'
    }).then(async () => {
        // 核心修复：使用 POST 请求绕过 DELETE 请求体的 Bug
        const res: any = await request.post(`/projects/${currentProject.value.id}/landing/bulk_delete`, { 
            landing_ids: landingIds 
        });
        
        if (res.code === 200) {
            ElMessage.success(res.message);
            openProject(currentProject.value); 
        }
    }).catch(() => {});
}


// 11. 核心新增：手动检查 B 池健康状态
const manualCheck = async (projectId: number) => {
    // ... (函数体省略)
    isChecking.value = true
    try {
        const res: any = await request.post(`/projects/${projectId}/manual_check`)
        ElNotification.success(res.message)
        await openProject(currentProject.value)
    } catch(e) {
        ElMessage.error('手动检查失败，请检查后端网络和URL是否为HTTPS')
    } finally {
        isChecking.value = false
    }
}


// 12. 确认删除整个项目 (移除项目)
const confirmDeleteProject = (proj: any) => {
    // ... (函数体省略)
    ElMessageBox.confirm(`⚠️ 警告：确定移除项目【${proj.name}】吗？该操作不可撤销，且会解绑所有域名。`, '移除项目', {
        type: 'error',
        confirmButtonText: '永久移除'
    }).then(async () => {
        const res: any = await request.delete(`/projects/${proj.id}`);
        if (res.code === 200) {
            ElMessage.success(res.message);
            drawerVisible.value = false;
            fetchProjects();
        }
    }).catch(() => {});
}

// 13. 核心新增：路径编辑操作
const openPathEditModal = (domain: EntryDomain, projectId: number) => {
    currentDomainToEdit.value = { ...domain, project_id: projectId }
    pathEditModalVisible.value = true
}

const executePathUpdate = async () => {
    const domain = currentDomainToEdit.value
    if (!domain.id) return

    if (domain.custom_path && !/^[a-zA-Z0-9]{1,30}$/.test(domain.custom_path)) {
        return ElMessage.error('路径只允许使用字母和数字，且长度小于30')
    }
    
    try {
        const res: any = await request.post('/entry_domains/update_path', {
            domain_id: domain.id,
            custom_path: domain.custom_path || '' 
        })

        if (res.code === 200) {
            ElMessage.success(res.message)
            pathEditModalVisible.value = false
            await fetchProjects() 
            await openProject(currentProject.value) 
        }
    } catch (e) {
        ElMessage.error((e as any).message || '路径更新失败')
    }
}


onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
/* 样式保持一致 */
.project-content-wrapper { padding-top: 5px; }

.project-grid {
    display: flex; 
    flex-wrap: wrap;
    align-items: stretch; 
    margin-bottom: 20px;
    /* 增加行间距 */
    row-gap: 24px;
}

/* 顶部与卡片 */
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }

.project-grid {
    display: flex; 
    flex-wrap: wrap;
    align-items: stretch; 
    margin-bottom: 20px;
}

.project-card { 
    height: 100%; 
    cursor: pointer; 
    transition: all 0.2s; 
    border-radius: 8px; 
    border: none; 
    margin-bottom: 20px;
}

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #f0f0f0; padding-bottom: 10px; }
.proj-name { font-weight: bold; font-size: 16px; color: #333; cursor: pointer; }
.card-body { display: flex; justify-content: space-around; align-items: center; cursor: pointer; }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-item span { font-size: 12px; color: #999; margin-bottom: 4px; }
.stat-item strong { font-size: 18px; color: #409EFF; }
.stat-divider { width: 1px; height: 30px; background: #eee; }

.tab-action { background: #f9f9f9; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #eee; }
.tab-tip { margin: 0 0 10px 0; font-size: 13px; color: #666; }

/* 状态徽章颜色修正 */
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
.status-badge.ok { color: #52c41a; background: #f6ffed; border: 1px solid #b7eb8f; }
.status-badge.banned { color: #f5222d; background: #fff1f0; border: 1px solid #ffa39e; }

.path-set { font-weight: bold; color: #409eff; }
</style>