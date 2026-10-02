<template>
    <div class="auth-layout">
        <header class="auth-header">
            <img
                src="../assets/images/vectofit-tm.png"
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
.auth-layout {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 24px;
}

.auth-header {
    text-align: center;
    margin-bottom: 10px;
}

.auth-header img {
    width: auto;
    height: 130px;
    object-fit: contain;
}

.auth-content {
    width: 100%;
    max-width: 600px;
    display: flex;
    justify-content: center;
}

.auth-footer {
    margin-top: 24px;
    text-align: center;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.auth-footer p {
    margin: 0;
    font-size: 0.875rem;
}
</style>