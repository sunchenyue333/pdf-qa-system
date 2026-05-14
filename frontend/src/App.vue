<template>
  <div style="padding: 40px; max-width: 800px; margin: 0 auto;">
    <h2>PDF Q&A System</h2>

    <!-- Upload -->
    <el-card style="margin-top: 20px;">
      <template #header>Upload PDF</template>
      <el-upload
        drag
        accept=".pdf"
        :before-upload="uploadPDF"
        :show-file-list="false"
      >
        <el-icon style="font-size: 40px;"><upload-filled /></el-icon>
        <div>Drag&drop PDF here, or click to upload</div>
      </el-upload>
      <div v-if="uploadStatus" style="margin-top: 10px; color: green;">
        {{ uploadStatus }}
      </div>
    </el-card>

    <!-- 聊天历史记录 -->
    <el-card v-if="history.length > 0" style="margin-top: 20px;">
      <template #header>Conversation</template>
      <div v-for="(item, index) in history" :key="index" style="margin-bottom: 20px;">

        <!-- 用户问题 -->
        <div style="text-align: right; margin-bottom: 8px;">
          <el-tag type="info">You：{{ item.question }}</el-tag>
        </div>

        <!-- AI 回答 -->
        <div style="background: #f5f7fa; padding: 12px; border-radius: 8px;">
          <p style="line-height: 1.8; margin: 0;">{{ item.answer }}</p>
          <!-- 来源页码标签 -->
          <div style="margin-top: 8px;">
            <el-tag
              v-for="page in item.sources"
              :key="page"
              size="small"
              style="margin-right: 6px;"
            >
              Page {{ page }} 
            </el-tag>
          </div>
        </div>

      </div>
    </el-card>

    <!-- 提问区域 -->
    <el-card style="margin-top: 20px;">
      <template #header>Ask</template>
      <el-input
        v-model="question"
        placeholder="Type your question..."
        :disabled="!uploadDone"
      />
      <el-button
        type="primary"
        style="margin-top: 10px;"
        :loading="loading"
        :disabled="!uploadDone"
        @click="askQuestion"
      >
        Ask
      </el-button>
    </el-card>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { UploadFilled } from '@element-plus/icons-vue'

const API = 'http://127.0.0.1:8000'
const uploadStatus = ref('')
const uploadDone = ref(false)
const question = ref('')
const loading = ref(false)

// 聊天历史，每条是 { question, answer, sources }
const history = ref([])

// 上传 PDF
async function uploadPDF(file) {
  uploadStatus.value = 'Uploading...'
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${API}/upload`, formData)
  uploadStatus.value = res.data.message
  uploadDone.value = true
  return false // 阻止 el-upload 默认的自动上传行为
}

// 提问
async function askQuestion() {
  if (!question.value.trim()) return
  loading.value = true

  const res = await axios.post(`${API}/ask`, { question: question.value })

  // 把这次问答追加进历史记录
  history.value.push({
    question: question.value,
    answer: res.data.answer,
    sources: res.data.sources
  })

  // 清空输入框
  question.value = ''
  loading.value = false
}
</script>