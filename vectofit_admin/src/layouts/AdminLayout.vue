<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <img src="../assets/images/vectofit-tm2.png" alt="VectoFit" />
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <span class="nav-title">Overview</span>

          <RouterLink to="/dashboard" class="nav-link"> Dashboard </RouterLink>
        </div>

        <div class="nav-section">
          <span class="nav-title">ML Development</span>

          <RouterLink to="/dataset" class="nav-link"> Datasets </RouterLink>

          <RouterLink to="/features" class="nav-link"> Features </RouterLink>

          <RouterLink to="/training" class="nav-link"> Training </RouterLink>

          <RouterLink to="/evaluation" class="nav-link">
            Evaluation
          </RouterLink>

          <RouterLink to="/models" class="nav-link"> Models </RouterLink>
        </div>

        <div class="nav-section">
          <span class="nav-title">System</span>

          <RouterLink to="/administration/users" class="nav-link">
            Users
          </RouterLink>

          <RouterLink to="/administration/logs" class="nav-link">
            Activity Logs
          </RouterLink>

          <RouterLink to="/administration/settings" class="nav-link">
            Settings
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-footer">
        <button class="sign-out" @click="() => handleSignOut()">
          Sign Out
        </button>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-header">
        <div>
          <h1>Administrator</h1>
        </div>
      </header>

      <main class="admin-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const handleSignOut = () => {
  router.push("/login");
};
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
  display: flex;
  background: #f8f6f5;
  color: #25201e;
  overflow: hidden;
}

.sidebar {
  width: 240px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background: #ffffff;
  border-right: 1px solid #eee6e2;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  overflow: hidden;
}

.sidebar-brand {
  padding: 24px 20px;
  border-bottom: 1px solid #eee6e2;
}

.sidebar-brand img {
  display: flex;
  width: 160px;
  max-width: 200px;
  object-fit: contain;
}

.sidebar-brand span {
  display: block;
  margin-top: 8px;
  color: #8a817d;
  font-size: 0.75rem;
}

.sidebar-nav {
  flex: 1;
  padding: 20px 12px;
}

.nav-section {
  margin-bottom: 24px;
}

.nav-title {
  display: block;
  padding: 0 10px;
  margin-bottom: 8px;
  color: #9a918d;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.nav-link {
  display: block;
  padding: 10px 12px;
  margin-bottom: 2px;
  border-radius: 8px;
  color: #5f5753;
  font-size: 0.88rem;
  text-decoration: none;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}

.nav-link:hover {
  background: #fff1eb;
  color: #e94b23;
}

.nav-link.router-link-active {
  background: #fff0eb;
  color: #e94b23;
  font-weight: 600;
}

.sidebar-footer {
  padding: 16px 12px;
  border-top: 1px solid #eee6e2;
}

.sign-out {
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #6f6763;
  text-align: left;
  cursor: pointer;
}

.sign-out:hover {
  background: #fff1eb;
  color: #e94b23;
}

.admin-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.admin-header {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: #ffffff;
  border-bottom: 1px solid #eee6e2;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.admin-header h1 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.admin-user {
  color: #766d69;
  font-size: 0.85rem;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}
</style>
