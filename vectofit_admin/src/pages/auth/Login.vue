<template>
  <section class="login-card">
    <div class="login-header">
      <h1>Sign in to VectoFit</h1>
      <p>Access your research and annotation workspace.</p>
    </div>

    <form @submit.prevent="handleLogin" :aria-busy="isLoading">
      <div class="form-group">
        <label for="identifier"> Username or Email </label>

        <input
          id="identifier"
          v-model="form.identifier"
          type="text"
          placeholder="Enter your username or email"
          autocomplete="username"
          required
        />
      </div>

      <div class="form-group">
        <label for="password"> Password </label>

        <input
          id="password"
          v-model="form.password"
          type="password"
          placeholder="Enter your password"
          autocomplete="current-password"
          required
        />
      </div>

      <p v-if="loginError" class="auth-error" role="alert">{{ loginError }}</p>
      <button type="submit" class="primary-button auth-submit" :disabled="isLoading">{{ isLoading ? 'Signing in...' : 'Sign in' }}</button>
    </form>

    <div class="register-link">
      <span>Don't have an account?</span>
      <RouterLink to="/register"> Sign Up </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import router from "../../router";
import client from "../../config/client";
import { accountService } from "../../services/accountService";

const isLoading = ref(false);
const loginError = ref("");

const form = reactive({
  identifier: "",
  password: "",
});

const handleLogin = async () => {
  if (isLoading.value) return;
  loginError.value = "";
  isLoading.value = true;

  try {
    const response = await client.post("/accounts/login/", {
      identifier: form.identifier,
      password: form.password,
    });

    const token = response.data.access_token || response.data.token;

    if (token) {
      localStorage.setItem("token", token);
      const user = await accountService.getCurrentUser();
      await router.push(user.is_annotator ? "/annotator" : "/dashboard");
    } else {
      loginError.value = "Sign-in could not be completed. Please try again.";
    }
  } catch {
    loginError.value = "Unable to sign in. Check your credentials and connection, then try again.";
  } finally {
    isLoading.value = false;
  }
};
</script>
