<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const rows = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const ok = ref('')

// 配置表单（考室为单一登记对象，应用始终操作 hall_id=1）
const HALL_ID = 1
const form = ref({ rows: 0, cols: 0, front_rows: 0, desk_rows: 0, desk_cols: 0, desk_col: 0 })

const deskRow = computed(() =>
  form.value.desk_rows > 0 ? form.value.rows - form.value.desk_rows : null)

async function refresh() {
  rows.value = await api('/halls')
  const h = rows.value.find((x: any) => x.id === HALL_ID) || rows.value[0]
  if (h) {
    form.value = {
      rows: h.rows, cols: h.cols, front_rows: h.front_rows ?? 0,
      desk_rows: h.desk_rows ?? 0, desk_cols: h.desk_cols ?? 0, desk_col: h.desk_col ?? 0,
    }
  }
}

onMounted(refresh)

async function save() {
  loading.value = true; error.value = ''; ok.value = ''
  try {
    const payload: any = {
      rows: Number(form.value.rows),
      cols: Number(form.value.cols),
      front_rows: Number(form.value.front_rows || 0),
      desk_rows: Number(form.value.desk_rows || 0),
      desk_cols: Number(form.value.desk_cols || 0),
      desk_col: Number(form.value.desk_col || 0),
    }
    // 桌行由贴后墙派生（只读），回传以让后端拒绝任何“任意放置”
    if (payload.desk_rows > 0) payload.desk_row = 0
    const res = await api(`/halls/${HALL_ID}/config`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    ok.value = res.rewritten_plan_id
      ? `配置已保存，现有方案 #${res.rewritten_plan_id} 已按新配置同成同败重写（历史方案不回刷）`
      : '配置已保存'
    await refresh()
  } catch (e: any) {
    error.value = e?.message || '保存失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <h1>考室</h1>
  <p class="sub">考室网格、前排行数与监考桌（监考桌整块贴后墙，占格不坐人）</p>
  <div class="card">
    <table>
      <thead>
        <tr><th>编码</th><th>名称</th><th>行</th><th>列</th><th>最小间距</th><th>前排行数</th><th>监考桌</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.code }}</td><td>{{ r.name }}</td>
          <td>{{ r.rows }}</td><td>{{ r.cols }}</td><td>{{ r.min_manhattan }}</td>
          <td>{{ r.front_rows ?? 0 }}</td>
          <td v-if="r.desk?.configured">
            {{ r.desk.rows }}×{{ r.desk.cols }} · 第 {{ r.desk.row }} 行 · 列 {{ r.desk.col }}–{{ r.desk.col + r.desk.cols - 1 }}
          </td>
          <td v-else class="muted">未配桌</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3 style="margin-top:0">配置考室 #{{ HALL_ID }}</h3>
    <div class="cfg-grid">
      <label>总行数<input type="number" min="1" v-model.number="form.rows"></label>
      <label>总列数<input type="number" min="1" v-model.number="form.cols"></label>
      <label>前排行数<input type="number" min="0" v-model.number="form.front_rows"></label>
      <label>监考桌高（行）<input type="number" min="0" v-model.number="form.desk_rows"></label>
      <label>监考桌宽（列）<input type="number" min="0" v-model.number="form.desk_cols"></label>
      <label>监考桌起始列<input type="number" min="0" v-model.number="form.desk_col"></label>
    </div>
    <p class="muted" style="font-size:0.78rem">
      监考桌只能整块贴在后墙（最大行号一侧），不接受任意行号放置；高/宽填 0 表示未配桌（与现网一致）。
      桌区行区间与前排区间重叠、越界或宽高非正都会保存失败。
    </p>
    <p v-if="deskRow !== null" class="muted" style="font-size:0.8rem">
      派生桌行（只读）：第 <b>{{ deskRow }}</b> 行 ～ 第 <b>{{ form.rows - 1 }}</b> 行
      <template v-if="deskRow < (form.front_rows || 0)">
        · <span style="color:var(--hs-bad)">与前排区间 0–{{ (form.front_rows || 0) - 1 }} 抢行，保存将失败</span>
      </template>
    </p>
    <button class="btn" :disabled="loading" @click="save">{{ loading ? '保存中…' : '保存配置' }}</button>
    <p v-if="error" class="badge badge-bad" style="margin-top:0.6rem;display:inline-block">保存失败：{{ error }}</p>
    <p v-if="ok" class="badge badge-ok" style="margin-top:0.6rem;display:inline-block">{{ ok }}</p>
  </div>
</template>

<style scoped>
.cfg-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.6rem 0.85rem; margin-bottom: 0.5rem;
}
.cfg-grid label {
  display: flex; flex-direction: column; gap: 0.25rem;
  font-size: 0.78rem; color: var(--hs-muted);
  font-family: "Segoe UI", "PingFang SC", sans-serif;
}
.cfg-grid input {
  padding: 0.35rem 0.45rem; border: 1px solid #b0a890; border-radius: 2px; font-size: 0.9rem;
}
</style>
