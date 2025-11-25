<template>
  <div class="domain-list-container">

    <el-card shadow="hover" class="table-card">
      <el-table :data="domains" style="width: 100%;" v-loading="loading" border max-height="650">
        <el-table-column prop="domain" label="域名" min-width="200" />
        <el-table-column prop="provider" label="线路商" width="120" />
        
        <el-table-column label="归属项目" width="180">
            <template #default="scope">
                <span v-if="scope.row.project_id">已分配 (ID: {{ scope.row.project_id }})</span>
                <el-tag type="info" size="small" v-else>闲置</el-tag>
            </template>
        </el-table-column>
        
        <el-table-column prop="custom_path" label="路径" width="120">
             <template #default="scope">
                <span v-if="scope.row.custom_path">/{{ scope.row.custom_path }}</span>
                <span v-else>—</span>
            </template>
        </el-table-column>
        
        <el-table-column prop="status" label="全局状态" width="100">
             <template #default="scope">
                <el-tag :type="scope.row.status === 'ok' ? 'success' : 'danger'" size="small">
                  {{ scope.row.status === 'ok' ? '正常' : '异常' }}
                </el-tag>
            </template>
        </el-table-column>
        
        <el-table-column prop="zone_id" label="Cloudflare Zone ID" min-width="250" show-overflow-tooltip />
        
        <el-table-column label="操作" width="120" align="center" fixed="right">
             <template #default="scope">
                <el-button link type="danger" size="small" @click="confirmDelete(scope.row)">彻底删除</el-button>
            </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '../../utils/request'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { 
  Refresh // 引入刷新图标
} from '@element-plus/icons-vue'

const domains = ref<any[]>([])
const loading = ref(false)

// 获取所有域名列表
const fetchDomains = async () => {
    loading.value = true
    try {
        // 注意：我们调用的 API 是 /api/domains (所有域名)
        const res: any = await request.get('/domains')
        if (res.code === 200) {
            domains.value = res.data
        }
    } catch (e) {
        ElMessage.error('加载域名列表失败');
    } finally {
        loading.value = false;
    }
}

// 删除功能
const confirmDelete = (domain: any) => {
    // 如果域名已分配，给出更强烈的警告
    const warningMessage = domain.project_id 
        ? `⚠️ 警告：该域名已分配给项目 ID ${domain.project_id}。彻底删除它将导致该项目路由失效！`
        : `确定要从系统中彻底删除域名【${domain.domain}】吗？`
        
    ElMessageBox.confirm(warningMessage, '彻底删除域名', {
        type: 'error',
        confirmButtonText: '永久删除'
    }).then(async () => {
        // 调用后端 DELETE /api/domains/{domain_id} 接口
        const res: any = await request.delete(`/domains/${domain.id}`);
        if (res.code === 200) {
            ElMessage.success(res.message);
            fetchDomains(); // 刷新列表
        }
    }).catch(() => {});
}


onMounted(() => {
    fetchDomains()
})
</script>

<style scoped>
/* 样式复用 */
.domain-list-container { 
    padding: 0; /* 移除内边距，让内容紧贴父 Layout */
}
.main-content { padding: 24px; }
.top-bar { margin-bottom: 24px; }
.top-bar h2 { margin: 0; font-size: 24px; color: #1f1f1f; }
.subtitle { margin: 5px 0 0; color: #8c8c8c; font-size: 13px; }

.table-card { border: none; border-radius: 8px; }
</style>