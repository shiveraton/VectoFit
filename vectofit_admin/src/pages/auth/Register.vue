<template>
    <section class="register-card">
        <div class="register-header">
            <h1>Create an account</h1>
            <p>Join the VectoFit research workspace.</p>
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
                <label for="confirmPassword">
                    Confirm Password
                </label>

                <input
                    id="confirmPassword"
                    v-model="form.confirmPassword"
                    type="password"
                    placeholder="Re-enter password"
                    autocomplete="new-password"
                    required
                />
            </div>

            <label class="annotator-option">
                <input v-model="form.isAnnotator" type="checkbox" />
                Sign up as an annotator
            </label>

            <p v-if="error" class="error" role="alert">{{ error }}</p>

            <button
                type="submit"
                class="primary-button auth-submit"
                :disabled="isSubmitting"
            >
                {{ isSubmitting ? "Creating account..." : "Create account" }}
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
import { reactive, ref } from "vue";
import router from "../../router";
import { accountService } from "../../services/accountService";

const form = reactive({
    username: '',
    email: '',
    password: '',
    confirmPassword: "",
    isAnnotator: true,
})

const error = ref<string | null>(null);
const isSubmitting = ref(false);

const handleRegister = async () => {
    if (isSubmitting.value) return;
    isSubmitting.value = true;
    error.value = null;
    try {
        await accountService.register({
            username: form.username,
            email: form.email,
            password: form.password,
            confirm_password: form.confirmPassword,
            is_annotator: form.isAnnotator,
        });
        await router.push("/login");
    } catch {
        error.value = "Registration failed. Check the form and try again.";
    } finally {
        isSubmitting.value = false;
    }
}
</script>
