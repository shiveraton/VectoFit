<template>
    <section class="register-card">
        <div class="register-header">
            <h2>Create Account</h2>
        </div>

        <form @submit.prevent="handleRegister">
            <div class="form-group">
                <label for="username">
                    Username
                </label>

                <input
                    id="username"
                    v-model="form.username"
                    type="text"
                    placeholder="Enter your username"
                    autocomplete="username"
                    required
                />
            </div>

            <div class="form-group">
                <label for="email">
                    Email
                </label>

                <input
                    id="email"
                    v-model="form.email"
                    type="email"
                    placeholder="Enter your email"
                    autocomplete="email"
                    required
                />
            </div>

            <div class="form-group">
                <label for="password">
                    Password
                </label>

                <input
                    id="password"
                    v-model="form.password"
                    type="password"
                    placeholder="Create a password"
                    autocomplete="new-password"
                    required
                />
            </div>

            <div class="form-group">
                <label form="confirmPassword">
                    Confirm Password
                </label>

                <input
                    id="password",
                    v-model="form.password"
                    type="password"
                    placeholder="Re-enter password"
                    autocomplete="new-password"
                    required
                />
            </div>

            <button
                type="submit"
                class="register-button"
            >
                Create Account
            </button>
        </form>

        <div class="login-link">
            <span>Already have an account?</span>

            <RouterLink to="/login">
                Sign In
            </RouterLink>
        </div>
    </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const form = reactive({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
})

const handleRegister = () => {
    console.log('Registration submitted:', form)
}
</script>

<style scoped>
.register-card {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    width: 100%;
    padding: 32px;
    border: 1px solid #ddd;
    border-radius: 12px;
    background: white;
}

.register-header {
   margin-bottom: 24px;
}

.register-header h2 {
   margin: 0 0 8px;
}

.register-header p {
    margin-bottom: 16px;
    color: #666;
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.form-group label {
    color: #403936;
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 15px;
}

.form-group input {
    width: 100%;
    padding: 11px 12px;
    border: 1px solid #ccc;
    border-radius: 6px;
    outline: none;
}

.form-group input:focus {
    border-color: #333;
}

.register-button {
    width: 100%;
    margin-top: 30px;
    padding: 13px 16px;
    border: none;
    border-radius: 10px;
    background: linear-gradient(90deg, #e63946 0%, #ff4d00 100%);
    color: #ffffff;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    transition:
        transform 0.2s ease,
        box-shadow 0.2s ease,
        opacity 0.2s ease;
}

.login-link {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 24px;
    color: #766d69;
    font-size: 0.88rem;
}

.login-link a {
    margin-left: 5px;
    color: #e94b23;
    font-weight: 700;
    text-decoration: none;
    transition: color 0.2s ease;
}

.login-link a:hover {
    color: #c9362c;
}
</style>