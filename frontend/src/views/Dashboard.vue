<template>
  <div class="dashboard-content-wrapper">
    
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="(item, index) in statCards" :key="index">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" :style="{ background: item.color }">
            <component :is="item.icon" />
          </div>
          <div class="stat-info">
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-value">{{ item.value }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>🛡️ 24小时流量与拦截趋势</span>
              <el-tag size="small">实时 Live</el-tag>
            </div>
          </template>
          <div ref="chartRef" class="echarts-box"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card quick-actions">
          <template #header>
            <div class="card-header"><span>⚡ 快捷操作</span></div>
          </template>
          <div class="action-grid">
            <div class="action-item" @click="openSyncModal">
              <div class="ac-icon" style="background: #e6f7ff; color: #1890ff"><Refresh /></div>
              <span>同步 CF</span>
            </div>
            <div class="action-item" @click="ElMessage.warning('紧急熔断功能已触发！')">
              <div class="ac-icon" style="background: #fff7e6; color: #fa8c16"><WarnTriangleFilled /></div>
              <span>紧急熔断</span>
            </div>
            <div class="action-item" @click="$router.push('/projects')">
              <div class="ac-icon" style="background: #f6ffed; color: #52c41a"><CirclePlusFilled /></div>
              <span>添加域名</span>
            </div>
          </div>
          <div class="system-log">
            <h4>系统日志</h4>
            <ul class="log-list">
              <li><span class="time">10:23</span> 系统自动备份完成</li>
              <li><span class="time">10:15</span> 数据库连接池初始化成功</li>
            </ul>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" class="table-card">
      <template #header>
        <div class="card-header">
          <span>🌐 活跃域名池监控 (摘要)</span>
          <el-button text type="primary" @click="fetchData">刷新列表</el-button>
        </div>
      </template>
      <el-table :data="tableData.slice(0, 5)" style="width: 100%" :header-cell-style="{background:'#f5f7fa'}">
        <el-table-column prop="domain" label="域名" width="240">
          <template #default="scope">
            <div class="domain-cell">
              <div class="dot green"></div>
              <strong>{{ scope.row.domain }}</strong>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="线路商">
          <template #default="scope">
            <el-tag class="provider-tag cf">Cloudflare</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="zone_id" label="Zone ID" show-overflow-tooltip />
        <el-table-column prop="custom_path" label="路径" show-overflow-tooltip>
          <template #default="scope">
            <span v-if="scope.row.custom_path">/{{ scope.row.custom_path }}</span>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
      <div style="text-align: right; padding-top: 10px;">
        <el-button link type="primary" @click="$router.push('/domains')">查看全部域名资产 »</el-button>
      </div>
    </el-card>
    
    <el-dialog v-model="syncVisible" title="☁️ 同步 Cloudflare 资产" width="500px">
      <div v-if="step === 1">
        <p style="margin-bottom: 10px; color: #666;">
          您可以直接扫描（使用系统设置中的 Token），或手动输入临时 Token：
        </p>
        <el-input v-model="cfToken" placeholder="不填则使用系统设置保存的 Token" clearable type="password" show-password></el-input>
      </div>

      <div v-if="step === 2">
        <p>扫描成功！发现 <b>{{ scannedZones.length }}</b> 个域名：</p>
        <el-table :data="scannedZones" style="margin-top: 10px; max-height: 300px; overflow-y: auto;" border @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="域名" />
          <el-table-column prop="status" label="状态" />
        </el-table>
      </div>

      <template #footer>
        <div v-if="step === 1">
          <el-button @click="syncVisible = false">取消</el-button>
          <el-button type="primary" @click="startScan" :loading="scanning">开始扫描</el-button>
        </div>
        <div v-if="step === 2">
          <el-button @click="step = 1">返回</el-button>
          <el-button type="success" @click="confirmImport" :loading="importing" :disabled="selectedZones.length === 0">
            导入选中的 {{ selectedZones.length }} 个域名
          </el-button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useUserStore } from '../store/user' 
import request from '../utils/request'
import * as echarts from 'echarts' 
import { ElMessage, ElNotification } from 'element-plus'
import { 
  Monitor, Warning, TrendCharts, Lock,
  Refresh, WarnTriangleFilled, CirclePlusFilled
} from '@element-plus/icons-vue'

// 【核心修复】：实例化 store 对象
const store = useUserStore() 

// 统计卡片
const statCards = [
  { label: '活跃域名', value: '1', icon: Monitor, color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { label: '今日请求', value: '0', icon: TrendCharts, color: 'linear-gradient(135deg, #2af598 0%, #009efd 100%)' },
  { label: '拦截威胁', value: '0', icon: Lock, color: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)' },
  { label: '系统健康', value: '100%', icon: Warning, color: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)' }
]

const tableData = ref([])
const fetchData = async () => {
  try {
    const res: any = await request.get('/domains') 
    if(res && res.code === 200) tableData.value = res.data
  } catch(e) { console.error(e) }
}

// 同步逻辑
const syncVisible = ref(false)
const step = ref(1)
const cfToken = ref('')
const scanning = ref(false)
const importing = ref(false)
const scannedZones = ref([])
const selectedZones = ref([])

const openSyncModal = () => {
  syncVisible.value = true
  step.value = 1
  cfToken.value = ''
  scannedZones.value = []
}

const startScan = async () => {
  scanning.value = true
  try {
    const params: any = {}
    if(cfToken.value) params.token = cfToken.value

    const res: any = await request.get('/cloudflare/scan', { params })
    if(res.code === 200) {
      scannedZones.value = res.data
      if(scannedZones.value.length === 0) {
        ElMessage.info("没有发现任何域名")
      } else {
        step.value = 2
      }
    }
  } catch(e) {
    ElMessage.error('扫描 Cloudflare 失败，请检查 Token。')
  } finally {
    scanning.value = false
  }
}

const handleSelectionChange = (val: any) => {
  selectedZones.value = val
}

const confirmImport = async () => {
  importing.value = true
  try {
    const res: any = await request.post('/cloudflare/import', {
      token: cfToken.value || undefined,
      domains: selectedZones.value
    })
    if(res.code === 200) {
      ElNotification({ title: '导入成功', message: res.message, type: 'success' })
      syncVisible.value = false
      fetchData()
    }
  } catch(e) { ElMessage.error('导入失败') } finally {
    importing.value = false
  }
}

// 图表逻辑
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const initChart = async () => {
  await nextTick()
  if (!chartRef.value) return
  if (chartInstance != null) chartInstance.dispose();
  chartInstance = echarts.init(chartRef.value)
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'] },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#eee' } } },
    series: [
      { name: '流量', type: 'line', smooth: true, itemStyle: { color: '#409EFF' }, areaStyle: { color: '#ecf5ff' }, data: [120, 132, 101, 134, 90, 230, 210] }
    ]
  }
  chartInstance.setOption(option)
}

onMounted(() => {
  fetchData()
  initChart()
  window.addEventListener('resize', () => chartInstance?.resize())
})
onUnmounted(() => {
  window.removeEventListener('resize', () => chartInstance?.resize())
  chartInstance?.dispose()
})
</script>

<style scoped>
/* 确保内容区与 AdminLayout 完美配合 */
.dashboard-content-wrapper { padding-top: 5px; }

/* HUD 统计卡片 */
.stat-row { margin-bottom: 24px; }
.stat-card { border: none; border-radius: 12px; transition: transform 0.3s; cursor: pointer; }
.stat-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
.stat-card :deep(.el-card__body) { display: flex; align-items: center; padding: 20px; }
.stat-icon { 
  width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 24px; margin-right: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.stat-info { display: flex; flex-direction: column; }
.stat-label { font-size: 12px; color: #8c8c8c; margin-bottom: 4px; }
.stat-value { font-size: 24px; font-weight: bold; color: #1f1f1f; }

/* 图表区域 */
.chart-row { margin-bottom: 24px; }
.chart-card { border: none; border-radius: 12px; height: 380px; display: flex; flex-direction: column; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.echarts-box { width: 100%; height: 300px; margin-top: 10px; }

/* 快捷操作区 */
.action-grid { display: flex; justify-content: space-between; margin-bottom: 20px; }
.action-item { display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: opacity 0.2s; }
.action-item:hover { opacity: 0.8; }
.ac-icon { width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; margin-bottom: 8px; }
.system-log { border-top: 1px solid #f0f0f0; padding-top: 15px; }

/* 表格区域 */
.table-card { border: none; border-radius: 12px; }
.domain-cell { display: flex; align-items: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.dot.green { background: #52c41a; }
.provider-tag.cf { color: #fa8c16; background: #fff7e6; border-color: #ffd591; }
</style>