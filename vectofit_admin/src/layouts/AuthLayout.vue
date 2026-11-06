<template>
    <div class="auth-layout">
        <header class="auth-header">
            <img
                src="../assets/images/vectofit-tm2.png"
                alt="VectoFit"
            />
        </header>

        <main class="auth-content">
            <RouterView />
        </main>

        <footer class="auth-footer">
            <p>&copy; 2026 VectoFit</p>
        </footer>
    </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.auth-layout { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; background: var(--vf-background); }
.auth-header { margin-bottom: 28px; }
.auth-header img { display: block; width: 144px; height: auto; }
.auth-content { width: 100%; max-width: 440px; }
.auth-footer { margin-top: 24px; color: var(--vf-muted); font-size: 12px; }
.auth-footer p { margin: 0; }
@media (max-width: 600px) { .auth-layout { padding: 32px 16px; } }
</style>
