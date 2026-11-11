import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/tables' },
    { path: '/login', name: 'login', component: () => import('../pages/LoginPage.vue'), meta: { public: true } },
    { path: '/tables', name: 'tables', component: () => import('../pages/TablesPage.vue'), meta: { title: '湖表总览' } },
    {
      path: '/tables/:id',
      name: 'table-detail',
      component: () => import('../pages/TableDetailPage.vue'),
      meta: { title: '文件与分区明细' },
    },
    {
      path: '/tables/:id/plan',
      name: 'table-plan',
      component: () => import('../pages/PlanPage.vue'),
      meta: { title: '合并计划预览' },
    },
    { path: '/jobs', name: 'jobs', component: () => import('../pages/JobsPage.vue'), meta: { title: '任务执行监控' } },
    {
      path: '/snapshots',
      name: 'snapshots',
      component: () => import('../pages/SnapshotsPage.vue'),
      meta: { title: '快照 diff 与校验' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/tables' },
  ],
})

setupGuards(router)

export default router
