import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BasicLayout from '@/layouts/BasicLayout.vue'
import UserLayout from '@/layouts/UserLayout.vue'

const HomeView = () => import('@/views/HomeView.vue')
const LoginView = () => import('@/views/LoginView.vue')
const RegisterView = () => import('@/views/RegisterView.vue')
const PersonaView = () => import('@/views/PersonaView.vue')
const ForumDetailView = () => import('@/views/ForumDetailView.vue')
const AssistantView = () => import('@/views/AssistantView.vue')
const SkillRepositoryView = () => import('@/views/SkillRepositoryView.vue')
const TimeGateView = () => import('@/views/TimeGateView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/auth',
      component: UserLayout,
      redirect: '/auth/login',
      children: [
        {
          path: 'login',
          name: 'login',
          component: LoginView
        },
        {
          path: 'register',
          name: 'register',
          component: RegisterView
        }
      ]
    },
    {
      path: '/',
      component: BasicLayout,
      redirect: '/dashboard',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: HomeView
        },
        {
          path: 'personas',
          name: 'personas',
          component: PersonaView
        },
        {
          path: 'forums/:id',
          name: 'forum-detail',
          component: ForumDetailView
        },
        {
          path: 'assistants',
          name: 'assistants',
          component: AssistantView
        },
        {
          path: 'assistants/skills',
          name: 'assistant-skills',
          component: SkillRepositoryView
        },
        {
          path: 'time-gate',
          name: 'time-gate',
          component: TimeGateView
        },
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard'
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  
  if (to.path.startsWith('/auth') && authStore.token) {
    next('/dashboard')
    return
  }
  
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.token) {
      next('/auth/login')
      return
    }
  }
  
  next()
})

export default router
