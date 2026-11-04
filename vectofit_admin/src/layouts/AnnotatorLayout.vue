
<template>
  <div class="annotator-layout">
    <header class="annotator-header">
      <div class="header-brand">
        <img :src="logo" alt="VectoFit" class="brand-logo" />
        <span class="brand-divider"></span>
        <span class="brand-label">Annotation</span>
      </div>

      <button type="button" class="sign-out-button" @click="signOut">
        Sign Out
      </button>
    </header>

    <main class="annotator-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import router from "../router";
import logo from "../assets/images/vectofit-tm2.png";

const signOut = () => {
  localStorage.removeItem("token");
  router.push("/login");
};
</script>

<style scoped>
.annotator-layout {
  min-height: 100vh;
  background: #f8f6f5;
  color: #25201e;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.annotator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 76px;
  padding: 12px 32px;
  background: #fff;
  border-bottom: 1px solid #eee6e2;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-logo {
  display: block;
  width: 145px;
  max-height: 48px;
  object-fit: contain;
  object-position: left center;
}

.brand-divider {
  width: 1px;
  height: 28px;
  background: #e4e4e7;
}

.brand-label {
  color: #71717a;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.sign-out-button {
  padding: 9px 16px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #ea580c;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.sign-out-button:hover {
  background: #ffedd5;
  border-color: #fdba74;
}

.annotator-main {
  padding: 32px;
}

@media (max-width: 640px) {
  .annotator-header {
    padding: 12px 18px;
  }

  .brand-logo {
    width: 115px;
  }

  .header-brand {
    gap: 10px;
  }

  .annotator-main {
    padding: 20px 16px;
  }
}
</style>
