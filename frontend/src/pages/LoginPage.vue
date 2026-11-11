<template>
  <div class="min-h-screen grid lg:grid-cols-[1.15fr_1fr]">
    <section class="relative border-r border-[var(--rule-soft)] bg-[var(--paper-2)] px-10 lg:px-16 py-10 flex flex-col justify-between overflow-hidden">
      <div>
        <div class="flex items-center justify-between">
          <div class="eyebrow">拾光内容平台 · offline warehouse squad</div>
          <div class="label">FIG.00 / sheet 01</div>
        </div>
        <h1 class="display mt-3 !text-[clamp(30px,3.4vw,44px)]">lakePack</h1>
        <div class="mt-1 text-[13px] text-[var(--ink-soft)]">数据湖小文件合并与分区整理工坊</div>
        <div class="mt-2 max-w-[420px] text-[11.5px] leading-relaxed text-[var(--ink-soft)]">
          Flink 每小时落小文件，凌晨人工跑 Spark 合并脚本。这里把「分区健康度 → 装箱计划 →
          执行重写 → 快照守恒」画在同一张图纸上，每一步都有据可查。
        </div>
      </div>

      <div class="relative my-6 flex-1 min-h-[260px]">
        <svg viewBox="0 0 560 420" class="h-full w-full" fill="none" stroke="var(--rule)" stroke-width="1">
          <defs>
            <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--rule-soft)" stroke-width="1" />
            </pattern>
          </defs>
          <!-- isometric table slabs: three partitions, diminishing fragments -->
          <g>
            <polygon points="120,150 300,90 430,150 250,210" fill="url(#hatch)" stroke="var(--ink-soft)" />
            <polygon points="120,150 120,168 250,228 250,210" fill="var(--paper)" stroke="var(--ink-soft)" />
            <polygon points="250,210 250,228 430,168 430,150" fill="var(--paper)" stroke="var(--ink-soft)" />

            <polygon points="120,232 300,172 430,232 250,292" fill="url(#hatch)" stroke="var(--ink-soft)" />
            <polygon points="120,232 120,250 250,310 250,292" fill="var(--paper)" stroke="var(--ink-soft)" />
            <polygon points="250,292 250,310 430,250 430,232" fill="var(--paper)" stroke="var(--ink-soft)" />

            <polygon points="120,314 300,254 430,314 250,374" fill="url(#hatch)" stroke="var(--ink-soft)" />
            <polygon points="120,314 120,332 250,392 250,374" fill="var(--paper)" stroke="var(--ink-soft)" />
            <polygon points="250,374 250,392 430,332 430,314" fill="var(--paper)" stroke="var(--ink-soft)" />
          </g>

          <!-- fragment ticks on the top slab: many small files -->
          <g stroke="var(--blue)" stroke-width="1">
            <line x1="152" y1="152" x2="168" y2="146" />
            <line x1="182" y1="162" x2="198" y2="156" />
            <line x1="212" y1="172" x2="228" y2="166" />
            <line x1="242" y1="182" x2="258" y2="176" />
            <line x1="272" y1="192" x2="288" y2="186" />
            <line x1="302" y1="202" x2="318" y2="196" />
          </g>
          <!-- merged output slabs on the lower two -->
          <g stroke="var(--sea)" stroke-width="1">
            <rect x="300" y="238" width="54" height="14" transform="skewX(-27)" />
            <rect x="300" y="320" width="54" height="14" transform="skewX(-27)" />
          </g>

          <!-- dimension / leader lines -->
          <g stroke="var(--ink-faint)" stroke-width="0.8">
            <line x1="430" y1="150" x2="505" y2="122" />
            <line x1="430" y1="232" x2="505" y2="204" />
            <line x1="430" y1="314" x2="505" y2="286" />
            <line x1="120" y1="150" x2="76" y2="122" />
            <line x1="120" y1="374" x2="76" y2="398" />
          </g>
          <g class="fill-[var(--ink-soft)]" font-size="9.5" font-family="Barlow, sans-serif" letter-spacing="1.2">
            <text x="430" y="116">dt=20261108</text>
            <text x="430" y="198">dt=20261109</text>
            <text x="430" y="280">dt=20261110</text>
            <text x="20" y="116">target 256 MB</text>
            <text x="14" y="404">manifest v2</text>
          </g>
          <g class="fill-[var(--ink-faint)]" font-size="8.5" font-family="Barlow, sans-serif" letter-spacing="1">
            <text x="152" y="140">1 8 0 · small files</text>
            <text x="300" y="232">compacted</text>
          </g>
        </svg>

        <div class="absolute bottom-0 left-0 flex items-end gap-6">
          <div class="leader-note">
            小文件 266 → 合并候选<br />
            目标 256 MB / 阈值 64 MB
          </div>
          <div class="leader-note">
            快照 v1 → v2：Σrows 守恒<br />
            changed = 0
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between text-[10px] uppercase tracking-label text-[var(--ink-faint)]">
        <span>S3-compatible · 40 TB · 60 parquet tables</span>
        <span>drafting scale 1:1</span>
      </div>
    </section>

    <section class="px-10 lg:px-20 py-10 flex flex-col justify-center">
      <div class="w-full max-w-[360px]">
        <div class="eyebrow">sign in</div>
        <h2 class="display mt-2 !text-[24px]">进入合并工坊</h2>
        <p class="mt-2 text-[12px] leading-relaxed text-[var(--ink-soft)]">
          使用数仓小队账号登录。工程师可生成并执行合并计划，分析师只读。
        </p>

        <form class="mt-8 space-y-5" @submit.prevent="submit">
          <div>
            <label class="label block mb-1">邮箱</label>
            <input
              v-model="email"
              type="email"
              class="bp-input"
              autocomplete="username"
              data-test="login-email"
              placeholder="eng@lake.local"
            />
          </div>
          <div>
            <label class="label block mb-1">密码</label>
            <input
              v-model="password"
              type="password"
              class="bp-input"
              autocomplete="current-password"
              data-test="login-password"
              placeholder="Demo@2026"
            />
          </div>
          <button type="submit" class="bp-btn bp-btn--solid w-full justify-center !py-2" data-test="login-submit" :disabled="auth.loading">
            {{ auth.loading ? '校验中…' : '登录' }}
          </button>
        </form>

        <ErrorNotice :error="error" />

        <div class="mt-8 border-t border-[var(--rule-soft)] pt-4">
          <div class="label mb-2">演示账号 · 密码统一 Demo@2026</div>
          <ul class="space-y-1">
            <li v-for="account in demoAccounts" :key="account.email">
              <button class="text-left text-[11.5px] text-[var(--blue)] hover:underline" @click="fill(account.email)">
                {{ account.label }} · {{ account.email }}
              </button>
            </li>
          </ul>
        </div>
        <div class="mt-6 text-[10px] uppercase tracking-label text-[var(--ink-faint)]">
          拾光内容平台 · 离线数仓小队 / 4 人
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useAuthStore } from '../stores/authStore'
import type { ApiError } from '../types/api'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const email = ref('eng@lake.local')
const password = ref('Demo@2026')
const error = ref<ApiError | null>(null)

const demoAccounts = [
  { label: '管理员', email: 'admin@lake.local' },
  { label: '数据工程师', email: 'eng@lake.local' },
  { label: '分析师（只读）', email: 'analyst@lake.local' },
]

function fill(value: string) {
  email.value = value
  password.value = 'Demo@2026'
}

async function submit() {
  error.value = null
  try {
    await auth.login(email.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/tables'
    router.push(redirect)
  } catch (err) {
    error.value = err as ApiError
  }
}
</script>
