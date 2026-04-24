<template>
  <div class="shell">
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="brand">
        <div class="logo" aria-hidden="true">
          <span class="cross">✚</span>
          <small>AI</small>
        </div>
        <div>
          <h1>智能医疗助手</h1>
          <p>企业级智能问诊与预约协同工作台</p>
        </div>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <label>意图识别</label>
          <strong class="mono">{{ intent || "待分析" }}</strong>
        </div>
        <div class="stat-card risk-card" :class="`risk-${(riskLevel || 'SAFE').toLowerCase()}`">
          <label>风险等级</label>
          <strong>{{ riskText }}</strong>
        </div>
      </div>

      <div class="session-card glass">
        <label>会话 ID</label>
        <p :title="sessionId">{{ shortSessionId }}</p>
      </div>

      <div class="action-group">
        <button class="primary" :disabled="loading" @click="openAppointmentModal">预约挂号</button>
        <button class="secondary" :disabled="loading" @click="loadAppointments">我的预约</button>
        <button class="danger-soft" :disabled="loading" @click="clearSession">清空会话</button>
      </div>

      <div class="source-panel">
        <h3>知识来源</h3>
        <div v-if="!sources.length" class="empty-source">
          <div class="empty-icon">🩺</div>
          <p class="muted">本轮暂无知识来源</p>
        </div>
        <ul v-else>
          <li v-for="(item, i) in sources" :key="i">{{ item }}</li>
        </ul>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="title-wrap">
          <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">☰</button>
          <div>
            <h2>医疗对话</h2>
            <p>输入症状、健康咨询或预约需求</p>
          </div>
        </div>
        <div class="status-pill" :class="{ busy: loading, offline: !isOnline }">
          <span class="dot"></span>
          {{ isOnline ? (loading ? "处理中" : "已连接") : "未连接" }}
        </div>
      </header>

      <section ref="chatRef" class="chat">
        <div v-if="!messages.length" class="welcome">
          <h3>欢迎使用智能医疗助手</h3>
          <p>你可以试试：最近发烧怎么办、帮我预约内科、高血压日常注意事项。</p>
        </div>

        <article
          v-for="(m, idx) in messages"
          :key="idx"
          class="message"
          :class="[m.role, { streaming: m.role === 'assistant' && !m.content }]"
        >
          <div v-if="m.role !== 'system'" class="avatar">{{ m.role === "user" ? "您" : "医" }}</div>
          <div class="bubble-wrap">
            <div v-if="m.content" class="bubble">
              <div class="msg-main">{{ splitMessage(m.content).main }}</div>
              <div v-if="splitMessage(m.content).disclaimer" class="medical-alert">
                ⚠️ {{ splitMessage(m.content).disclaimer }}
              </div>
            </div>
            <div v-else class="bubble typing"><span></span><span></span><span></span></div>
            <time v-if="m.content && m.ts">{{ formatTime(m.ts) }}</time>
          </div>
        </article>
      </section>

      <section class="composer">
        <div class="quick-actions">
          <button class="quick-chip" :disabled="loading" @click="fillQuick('继续预约')">继续预约</button>
          <button class="quick-chip" :disabled="loading" @click="fillQuick('我想预约内科')">我想预约内科</button>
          <button class="quick-chip" :disabled="loading" @click="fillQuick('最近头痛怎么办')">最近头痛怎么办</button>
          <button class="quick-chip" :disabled="loading" @click="fillQuick('查看我的预约')">查看我的预约</button>
          <button class="quick-chip" :disabled="loading" @click="fillQuick('取消预约')">取消预约</button>
        </div>
        <textarea
          ref="composerRef"
          v-model="input"
          :disabled="loading"
          placeholder="请输入症状、健康问题或预约需求，Enter 发送，Shift + Enter 换行"
          @keydown="handleComposerKeydown"
        ></textarea>
        <button class="send" :disabled="loading || !input.trim()" @click="sendMessage">
          {{ loading ? "发送中..." : "➤ 发送" }}
        </button>
      </section>

      <section v-if="showAppointmentsPanel" class="appointments">
        <div class="section-head">
          <div class="section-title">
            <h3>我的预约</h3>
            <span>{{ appointments.length }} 条</span>
          </div>
          <button class="section-close" :disabled="loading" @click="showAppointmentsPanel = false">×</button>
        </div>
        <div v-if="appointmentsLoading" class="appointments-loading">正在加载预约信息...</div>
        <div v-else-if="appointmentsError" class="appointments-error">{{ appointmentsError }}</div>
        <div v-else-if="!appointments.length" class="appointments-empty">
          <p>暂无预约记录</p>
        </div>
        <div v-else class="card-list">
          <div class="card" v-for="apt in appointments" :key="apt.id">
            <div class="card-top">
              <strong>{{ apt.id }}</strong>
              <span class="tag" :class="appointmentStatusClass(apt.status)">
                {{ appointmentStatusText(apt.status) }}
              </span>
            </div>
            <p><span>姓名</span><strong>{{ apt.patient_name || "-" }}</strong></p>
            <p><span>手机号</span><strong>{{ apt.phone || "-" }}</strong></p>
            <p><span>科室</span><strong>{{ apt.department || "-" }}</strong></p>
            <p><span>医生</span><strong>{{ doctorName(apt.doctor) }}</strong></p>
            <p><span>时间</span><strong>{{ apt.date || "-" }} {{ apt.time || "" }}</strong></p>
            <button
              v-if="apt.status === 'confirmed'"
              class="danger"
              :disabled="loading"
              @click="cancelAppointment(apt.id)"
            >
              取消预约
            </button>
          </div>
        </div>
      </section>
    </main>

    <div v-if="showAppointmentModal" class="modal-mask" @click.self="closeAppointmentModal">
      <div class="modal">
        <div class="modal-head">
          <h3>预约挂号</h3>
          <button class="close-x" @click="closeAppointmentModal">×</button>
        </div>

        <div class="progress"><div class="bar" :style="{ width: `${((appointmentStep - 1) / 5) * 100}%` }"></div></div>

        <div class="steps">
          <div
            v-for="(label, idx) in stepLabels"
            :key="label"
            class="step"
            :class="{ active: appointmentStep >= idx + 1, now: appointmentStep === idx + 1 }"
          >
            <div class="dot">{{ idx + 1 }}</div>
            <span>{{ label }}</span>
          </div>
        </div>

        <div class="step-body">
          <template v-if="appointmentStep === 1">
            <label>姓名</label>
            <input v-model.trim="appointmentForm.name" placeholder="请输入真实姓名" />
            <div class="foot">
              <button class="primary" @click="nextStep1">下一步</button>
            </div>
          </template>

          <template v-else-if="appointmentStep === 2">
            <label>手机号</label>
            <input v-model.trim="appointmentForm.phone" placeholder="请输入11位手机号" />
            <p v-if="phoneError" class="err">请输入有效的 11 位手机号</p>
            <div class="foot">
              <button @click="prevStep">上一步</button>
              <button class="primary" @click="nextStep2">下一步</button>
            </div>
          </template>

          <template v-else-if="appointmentStep === 3">
            <label>科室</label>
            <div class="grid2">
              <button
                v-for="dept in departments"
                :key="dept.id"
                class="chip"
                :class="{ selected: appointmentForm.departmentId === dept.id }"
                @click="selectDepartment(dept)"
              >
                <strong>{{ dept.name }}</strong>
                <small>{{ dept.description }}</small>
              </button>
            </div>
            <div class="foot">
              <button @click="prevStep">上一步</button>
              <button class="primary" :disabled="!appointmentForm.departmentId" @click="nextStep3">下一步</button>
            </div>
          </template>

          <template v-else-if="appointmentStep === 4">
            <label>日期</label>
            <div class="grid3">
              <button
                v-for="date in availableDates"
                :key="date"
                class="chip center"
                :class="{ selected: appointmentForm.date === date }"
                @click="appointmentForm.date = date"
              >
                {{ date }}
              </button>
            </div>
            <div class="foot">
              <button @click="prevStep">上一步</button>
              <button class="primary" :disabled="!appointmentForm.date" @click="nextStep4">下一步</button>
            </div>
          </template>

          <template v-else-if="appointmentStep === 5">
            <label>时间段</label>
            <div class="grid2">
              <button
                v-for="time in timeSlots"
                :key="time"
                class="chip center"
                :class="{ selected: appointmentForm.time === time }"
                @click="appointmentForm.time = time"
              >
                {{ time }}
              </button>
            </div>
            <div class="foot">
              <button @click="prevStep">上一步</button>
              <button class="primary" :disabled="!appointmentForm.time" @click="nextStep5">下一步</button>
            </div>
          </template>

          <template v-else>
            <label>确认信息</label>
            <div class="confirm">
              <p><strong>姓名：</strong>{{ appointmentForm.name }}</p>
              <p><strong>手机号：</strong>{{ appointmentForm.phone }}</p>
              <p><strong>科室：</strong>{{ appointmentForm.department }}</p>
              <p><strong>日期：</strong>{{ appointmentForm.date }}</p>
              <p><strong>时间：</strong>{{ appointmentForm.time }}</p>
              <p><strong>医生：</strong>{{ appointmentForm.doctor }}</p>
            </div>
            <div class="foot">
              <button @click="prevStep">上一步</button>
              <button class="primary" :disabled="loading" @click="submitAppointment">确认预约</button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";

const API_PREFIX = "/api";

const input = ref("");
const loading = ref(false);
const messages = ref([]);
const sources = ref([]);
const intent = ref("");
const riskLevel = ref("SAFE");
const appointments = ref([]);
const chatRef = ref(null);
const composerRef = ref(null);
const toast = ref({ show: false, message: "", type: "ok" });
const sidebarOpen = ref(false);
const isOnline = ref(typeof navigator !== "undefined" ? navigator.onLine : true);
const appointmentsLoading = ref(false);
const appointmentsError = ref("");
const showAppointmentsPanel = ref(true);

const showAppointmentModal = ref(false);
const appointmentStep = ref(1);
const phoneError = ref(false);
const appointmentForm = ref({
  name: "",
  phone: "",
  departmentId: "",
  department: "",
  doctor: "张医生",
  date: "",
  time: "",
});

const stepLabels = ["姓名", "手机号", "科室", "日期", "时间", "确认"];

const departments = [
  { id: "D001", name: "内科", description: "常见内科疾病咨询与诊疗" },
  { id: "D002", name: "外科", description: "外科相关问题处理" },
  { id: "D003", name: "儿科", description: "儿童健康与常见疾病咨询" },
  { id: "D004", name: "妇产科", description: "女性与孕产相关诊疗" },
  { id: "D005", name: "眼科", description: "视力与眼部健康问题" },
  { id: "D006", name: "耳鼻喉科", description: "耳鼻喉疾病咨询与诊疗" },
  { id: "D007", name: "口腔科", description: "口腔和牙齿问题处理" },
  { id: "D008", name: "皮肤科", description: "皮肤相关疾病咨询与诊疗" },
];

const timeSlots = [
  "08:00-09:00",
  "09:00-10:00",
  "10:00-11:00",
  "11:00-12:00",
  "14:00-15:00",
  "15:00-16:00",
  "16:00-17:00",
  "17:00-18:00",
];

const availableDates = computed(() =>
  Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  })
);

const sessionId = (() => {
  const key = "medical_ai_session_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    localStorage.setItem(key, id);
  }
  return id;
})();

const shortSessionId = computed(() => (sessionId.length > 24 ? `${sessionId.slice(0, 24)}...` : sessionId));

const riskText = computed(() => {
  const map = { HIGH: "高风险", MEDIUM: "中风险", LOW: "低风险", SAFE: "安全" };
  return map[riskLevel.value] || "未知";
});

const doctorName = (doctor) => {
  if (typeof doctor === "object" && doctor !== null) {
    return doctor.name || doctor.doctor_name || doctor.title || "张医生";
  }
  if (typeof doctor === "string" && doctor.trim()) return doctor;
  return "张医生";
};

const formatTime = (ts) => {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return "";
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
};

const splitMessage = (content = "") => {
  const text = String(content || "");
  const disclaimerMarkers = ["⚠️", "本系统提供的医疗信息仅供参考", "以上内容仅供参考"];
  const marker = disclaimerMarkers.find((m) => text.includes(m));
  if (!marker) return { main: text, disclaimer: "" };
  if (marker === "⚠️") {
    const [main, ...rest] = text.split("⚠️");
    return { main: (main || "").trim(), disclaimer: rest.join("⚠️").trim() };
  }
  const idx = text.indexOf(marker);
  return { main: text.slice(0, idx).trim(), disclaimer: text.slice(idx).trim() };
};

const appointmentStatusText = (status) => {
  const s = (status || "").toLowerCase();
  if (s === "confirmed") return "待就诊";
  if (s === "completed") return "已完成";
  if (s === "cancelled" || s === "canceled") return "已取消";
  return "已取消";
};

const appointmentStatusClass = (status) => {
  const s = (status || "").toLowerCase();
  if (s === "confirmed") return "pending";
  if (s === "completed") return "done";
  return "cancel";
};

const showToast = (message, type = "ok") => {
  toast.value = { show: true, message, type };
  setTimeout(() => {
    toast.value.show = false;
  }, 1800);
};

const pushMessage = (role, content) => {
  messages.value.push({ role, content, ts: Date.now() });
};

const pushSystemNotice = (content) => {
  const text = String(content || "").trim();
  if (!text) return;
  const last = messages.value[messages.value.length - 1];
  if (last && last.role === "system" && (last.content || "").trim() === text) return;
  messages.value.push({ role: "system", content: text, ts: Date.now() });
};

const forceScrollBottom = (retry = 2) => {
  if (!chatRef.value) return;
  chatRef.value.scrollTop = chatRef.value.scrollHeight;
  if (retry > 0) {
    requestAnimationFrame(() => forceScrollBottom(retry - 1));
  }
};

const scrollBottom = async () => {
  await nextTick();
  forceScrollBottom(3);
};

function handleComposerKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function fillQuick(text) {
  input.value = text;
  nextTick(() => composerRef.value?.focus());
}

function resetAppointmentForm() {
  appointmentStep.value = 1;
  phoneError.value = false;
  appointmentForm.value = {
    name: "",
    phone: "",
    departmentId: "",
    department: "",
    doctor: "张医生",
    date: "",
    time: "",
  };
}

function openAppointmentModal() {
  resetAppointmentForm();
  showAppointmentModal.value = true;
}

function closeAppointmentModal() {
  showAppointmentModal.value = false;
}

function nextStep1() {
  if (!appointmentForm.value.name) return showToast("请输入姓名", "warn");
  appointmentStep.value = 2;
}

function nextStep2() {
  const ok = /^\d{11}$/.test(appointmentForm.value.phone);
  phoneError.value = !ok;
  if (!ok) return;
  appointmentStep.value = 3;
}

function selectDepartment(dept) {
  appointmentForm.value.departmentId = dept.id;
  appointmentForm.value.department = dept.name;
}

function nextStep3() {
  if (!appointmentForm.value.departmentId) return showToast("请选择科室", "warn");
  appointmentStep.value = 4;
}

function nextStep4() {
  if (!appointmentForm.value.date) return showToast("请选择日期", "warn");
  appointmentStep.value = 5;
}

function nextStep5() {
  if (!appointmentForm.value.time) return showToast("请选择时间段", "warn");
  appointmentStep.value = 6;
}

function prevStep() {
  appointmentStep.value = Math.max(1, appointmentStep.value - 1);
}

async function submitAppointment() {
  const payload = {
    patient_name: appointmentForm.value.name,
    phone: appointmentForm.value.phone,
    department: appointmentForm.value.department,
    doctor: appointmentForm.value.doctor,
    date: appointmentForm.value.date,
    time: appointmentForm.value.time,
  };

  const res = await fetch(`${API_PREFIX}/save-appointment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, appointment_data: payload }),
  });
  const data = await res.json();

  if (!res.ok || !data.success) {
    showToast(data.message || "预约失败", "warn");
    return;
  }

  closeAppointmentModal();
  await loadAppointments();
  pushMessage(
    "assistant",
    `预约成功，预约号：${data.appointment?.id || "-"}\n姓名：${payload.patient_name}\n科室：${payload.department}\n日期：${payload.date}\n时间：${payload.time}`
  );
  await scrollBottom();
  showToast("预约创建成功", "ok");
}

async function loadHistory() {
  const res = await fetch(`${API_PREFIX}/history/${sessionId}`);
  if (!res.ok) return;
  const data = await res.json();
  messages.value = (data.full_history || []).map((m) => ({
    role: m.role === "user" ? "user" : "assistant",
    content: m.content || "",
    ts: m.timestamp || m.ts || m.created_at || null,
  }));
  await scrollBottom();
}

async function sendMessage() {
  const content = input.value.trim();
  if (!content || loading.value) return;

  pushMessage("user", content);
  input.value = "";
  loading.value = true;
  await scrollBottom();

  const resp = await fetch(`${API_PREFIX}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: content, session_id: sessionId }),
  });

  if (!resp.ok || !resp.body) {
    loading.value = false;
    pushMessage("assistant", "请求失败，请稍后再试。");
    await scrollBottom();
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let assistantIndex = -1;
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: !done });
    if (done) buffer += "\n\n";
    buffer = buffer.replace(/\r\n/g, "\n");

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const data = raw
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");

      if (data) {
        try {
          const event = JSON.parse(data);
          if (event.type === "start") {
            messages.value.push({ role: "assistant", content: "", ts: Date.now() });
            assistantIndex = messages.value.length - 1;
            await scrollBottom();
          } else if (event.type === "message" && assistantIndex >= 0) {
            messages.value[assistantIndex].content += event.content || "";
            await scrollBottom();
          } else if (event.type === "complete") {
            intent.value = event.intent || "";
            riskLevel.value = event.risk_level || "SAFE";
            sources.value = event.sources || [];
            if (Array.isArray(event.appointments) && event.appointments.length) {
              appointments.value = event.appointments;
            }
            if (event.topic_switched && event.topic_switch_notice) {
              pushSystemNotice(event.topic_switch_notice);
            }
            await scrollBottom();
          }
        } catch (_) {
          // ignore malformed event chunk
        }
      }
      boundary = buffer.indexOf("\n\n");
    }

    if (done) break;
  }

  loading.value = false;
  await scrollBottom();
}

async function clearSession() {
  await fetch(`${API_PREFIX}/clear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  messages.value = [];
  intent.value = "";
  riskLevel.value = "SAFE";
  sources.value = [];
  appointments.value = [];
  showToast("会话已清空", "ok");
}

async function loadAppointments() {
  showAppointmentsPanel.value = true;
  appointmentsLoading.value = true;
  appointmentsError.value = "";
  const res = await fetch(`${API_PREFIX}/my-appointments?session_id=${sessionId}`);
  if (!res.ok) {
    appointmentsLoading.value = false;
    appointmentsError.value = "预约数据加载失败，请稍后重试";
    return;
  }
  const data = await res.json();
  appointments.value = data.appointments || [];
  appointmentsLoading.value = false;
  showToast("预约列表已刷新", "ok");
}

async function cancelAppointment(appointmentId) {
  if (!window.confirm("确定要取消这个预约吗？")) return;

  const res = await fetch(`${API_PREFIX}/cancel-appointment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, appointment_id: appointmentId }),
  });
  const data = await res.json();

  if (!res.ok || !data.success) {
    showToast(data.message || "取消预约失败", "warn");
    return;
  }

  await loadAppointments();
  showToast("预约已取消", "ok");
}

const onOnline = () => {
  isOnline.value = true;
};

const onOffline = () => {
  isOnline.value = false;
};

onMounted(() => {
  loadHistory();
  window.addEventListener("online", onOnline);
  window.addEventListener("offline", onOffline);
});

onUnmounted(() => {
  window.removeEventListener("online", onOnline);
  window.removeEventListener("offline", onOffline);
});
</script>
