<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const menuOpen = ref(false);
const navigation = [
  { to: '/dashboard', label: 'Overview', path: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z' },
  { to: '/dataset', label: 'Datasets', path: 'M3 7v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7 M3 7V5a2 2 0 0 1 2-2h5l2 4h9 M3 7h18 M8 12h8 M8 16h5' },
  { to: '/training', label: 'Training', path: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2' },
  { to: '/models', label: 'Model Registry', path: 'm12 3 9 5-9 5-9-5 9-5z M3 12l9 5 9-5 M3 16l9 5 9-5' },
  { to: '/pilot-results', label: 'Pilot Results', path: 'M9 3h6 M10 3v7L4 20a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1l-6-10V3 M8 15h8' },
];
const pageLabel = computed(() => route.name === 'DatasetAnnotation' ? 'Dataset annotation' : navigation.find(item => route.path.startsWith(item.to))?.label ?? 'Workspace');
watch(() => route.fullPath, () => { menuOpen.value = false; });
const handleSignOut = () => { router.push('/login'); };
</script>

<template>
  <div class="admin-layout">
    <a class="skip-link" href="#admin-content">Skip to content</a>
    <aside class="sidebar">
      <div class="sidebar-brand">
        <RouterLink to="/dashboard" aria-label="VectoFit overview" class="brand-link">
          <img src="../assets/images/vectofit-tm2.png" alt="VectoFit" />
        </RouterLink>
        <button class="menu-toggle" type="button" aria-controls="admin-navigation" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen">
          {{ menuOpen ? 'Close menu' : 'Menu' }}
        </button>
      </div>
      <nav id="admin-navigation" class="sidebar-nav" :class="{ 'is-open': menuOpen }" aria-label="Admin navigation" @keydown.esc="menuOpen = false">
        <div class="nav-section">
          <span class="nav-title">Workspace</span>
          <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" class="nav-link" :class="{ 'is-current': item.to === '/dataset' && route.name === 'DatasetAnnotation' }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="item.path" /></svg>
            {{ item.label }}
          </RouterLink>
        </div>
        <div class="nav-section system-section">
          <span class="nav-title">Administration</span>
          <div class="nav-unavailable"><span>Users</span><small>Unavailable</small></div>
          <div class="nav-unavailable"><span>Activity Logs</span><small>Unavailable</small></div>
          <div class="nav-unavailable"><span>Settings</span><small>Unavailable</small></div>
        </div>
        <div class="sidebar-footer">
          <span class="workspace-caption">VectoFit Admin Portal</span>
          <button type="button" class="sign-out" @click="handleSignOut">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5H4v14h5 M14 8l4 4-4 4 M8 12h10" /></svg>
            Sign out
          </button>
        </div>
      </nav>
    </aside>
    <div class="admin-main">
      <header class="admin-header">
        <div class="workspace-breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>{{ pageLabel }}</strong></div>
        <span class="admin-role">Administrator</span>
      </header>
      <main id="admin-content" class="admin-content" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-layout { min-height: 100vh; background: var(--vf-background); color: var(--vf-text); }
.skip-link { position: fixed; top: -80px; left: 16px; z-index: 100; padding: 12px 20px; background: var(--vf-dark); color: white; border-radius: 8px; }
.skip-link:focus { top: 12px; }
.sidebar { position: fixed; inset: 0 auto 0 0; width: 232px; display: flex; flex-direction: column; background: #fff; border-right: 1px solid var(--vf-border); z-index: 20; }
.sidebar-brand { min-height: 112px; padding: 28px 24px 24px; }
.brand-link { display: inline-flex; flex-direction: column; align-items: flex-start; gap: 10px; text-decoration: none; }
.brand-link img { display: block; width: 136px; height: auto; }
.brand-link span { color: var(--vf-muted); font-size: 11px; letter-spacing: .035em; }
.sidebar-nav { display: flex; flex: 1; min-height: 0; flex-direction: column; overflow-y: auto; padding: 12px; }
.nav-section { margin-bottom: 28px; }
.nav-title { display: block; padding: 0 12px; margin-bottom: 10px; color: var(--vf-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .1em; }
.nav-link { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 10px 12px; margin-bottom: 4px; border: 1px solid transparent; border-radius: 6px; color: var(--vf-muted); font-size: 13px; text-decoration: none; transition: background-color 150ms; }
.nav-link svg, .sign-out svg { width: 18px; height: 18px; flex-shrink: 0; }
.nav-link:hover { background: #f4f4f5; color: var(--vf-dark); }
.nav-link.router-link-active, .nav-link.is-current { background: var(--vf-orange-soft); color: var(--vf-orange-dark); border-color: #ffedd5; font-weight: 600; }
.nav-unavailable { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 10px 12px; color: var(--vf-muted); font-size: 12px; }
.nav-unavailable small { font-size: 10px; color: var(--vf-muted); }
.sidebar-footer { margin-top: auto; padding: 20px 0 0; border-top: 1px solid var(--vf-border); }
.workspace-caption { display: block; padding: 0 12px; margin-bottom: 10px; color: var(--vf-muted); font-size: 11px; }
.sign-out { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 44px; padding: 10px 12px; border: none; border-radius: 6px; background: transparent; color: var(--vf-text); text-align: left; cursor: pointer; }
.sign-out:hover { background: #f4f4f5; }
.admin-main { margin-left: 232px; min-width: 0; }
.admin-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; min-height: 64px; padding: 12px 36px; border-bottom: 1px solid var(--vf-border); background: #fff; }
.workspace-breadcrumb { display: flex; align-items: center; gap: 12px; color: var(--vf-muted); font-size: 12px; }
.workspace-breadcrumb strong { color: var(--vf-text); font-weight: 500; }
.admin-role { font-size: 11px; color: var(--vf-muted); }
.admin-content { width: 100%; max-width: 1600px; margin: 0 auto; padding: 36px; outline: none; }
.menu-toggle { display: none; }
@media (max-width: 900px) {
  .sidebar { position: static; width: 100%; border-right: 0; border-bottom: 1px solid var(--vf-border); }
  .sidebar-brand { display: flex; justify-content: space-between; align-items: center; min-height: 72px; padding: 16px 24px; }
  .brand-link { gap: 4px; }
  .brand-link img { width: 110px; }
  .brand-link span { font-size: 10px; }
  .menu-toggle { display: block; min-height: 40px; padding: 8px 12px; border: 1px solid var(--vf-control-border); border-radius: 6px; background: #fff; color: var(--vf-text); cursor: pointer; }
  .sidebar-nav { display: none; padding: 12px 24px 20px; }
  .sidebar-nav.is-open { display: flex; }
  .nav-section { margin-bottom: 16px; }
  .system-section { display: none; }
  .admin-main { margin-left: 0; }
  .admin-header { min-height: 48px; padding: 12px 24px; }
  .admin-content { padding: 28px 24px; }
}
@media (max-width: 600px) {
  .sidebar-brand, .admin-header { padding-left: 16px; padding-right: 16px; }
  .admin-content { padding: 24px 16px; }
  .admin-role { display: none; }
}
</style>
