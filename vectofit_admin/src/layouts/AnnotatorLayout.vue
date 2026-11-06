
<template>
  <div class="annotator-layout">
    <header class="annotator-header">
      <div class="header-brand">
        <img :src="logo" alt="VectoFit" class="brand-logo" />
        <span class="brand-divider"></span>
        <span class="brand-label">Annotation</span>
      </div>

      <button type="button" class="secondary-button" @click="signOut">
        Sign Out
      </button>
    </header>

    <main class="annotator-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { publicLogout } from "../config/publicAuth";
const router = useRouter();
import logo from "../assets/images/vectofit-tm2.png";

const signOut = async () => {
  if (import.meta.env.MODE === "public") {
    try {
      await publicLogout();
      await router.replace("/annotator/login");
    } catch {
      window.alert("Sign out failed. Please try again.");
    }
    return;
  }
  localStorage.removeItem("token");
  router.push("/login");
};
</script>

<style scoped>
.annotator-layout {
  min-height: 100vh;
  background: var(--vf-background);
  color: var(--vf-text);
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.annotator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 76px;
  padding: 12px 32px;
  background: #fff;
  border-bottom: 1px solid var(--vf-border);
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





.annotator-main {
  max-width: 1600px;
  margin: 0 auto;
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
