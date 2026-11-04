<template>
  <section class="login-card">
    <div class="login-header">
      <h2>Welcome Back</h2>
      <p>Sign in to the VectoFit Administrator Portal</p>
    </div>

    <form @submit.prevent="handleLogin">
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
          ,
          v-model="form.password"
          type="password"
          placeholder="Enter your password"
          autocomplete="current-password"
          required
        />
      </div>

      <button type="submit" class="login-button">Sign In</button>
    </form>

    <div class="register-link">
      <span>Don't have an account?</span>
      <RouterLink to="Register"> Sign Up </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import router from "../../router";
import client from "../../config/client";
import { accountService } from "../../services/accountService";

const isLoading = ref(false);

const form = reactive({
  identifier: "",
  password: "",
});

const handleLogin = async () => {
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
      console.error("Token is missing in response payload:", response.data);
    }
  } catch (error) {
    console.error("Login failed:", error);
  } finally {
    isLoading.value = false;
    console.log("Login request completed.");
  }
};
</script>

<style>
.login-card {
  width: 100%;
  max-width: 420px;
  padding: 42px;
  background: #ffffff;
  border: 1px solid #f1e5df;
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(42, 27, 22, 0.08);
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

.login-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 28px;
}

.login-logo img {
  display: block;
  width: auto;
  height: 58px;
  object-fit: contain;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  margin: 0 0 8px;
  color: #1f1a18;
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.login-header p {
  margin: 0;
  color: #766d69;
  font-size: 0.9rem;
  line-height: 1.5;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  padding: 13px 15px;
  box-sizing: border-box;
  border: 1px solid #ded7d3;
  border-radius: 10px;
  background: #fffdfc;
  color: #2b2522;
  font-size: 0.92rem;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.form-group input::placeholder {
  color: #aaa19d;
}

.form-group input:hover {
  border-color: #cfc4be;
}

.form-group input:focus {
  outline: none;
  border-color: #ff4d00;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(255, 77, 0, 0.1);
}

.login-button {
  width: 100%;
  margin-top: 40px;
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

.login-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(255, 77, 0, 0.25);
}

.login-button:active {
  transform: translateY(0);
}

.login-button:focus-visible {
  outline: 3px solid rgba(255, 77, 0, 0.2);
  outline-offset: 2px;
}

.register-link {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 24px;
  color: #766d69;
  font-size: 0.88rem;
}

.register-link a {
  margin-left: 5px;
  color: #e94b23;
  font-weight: 700;
  text-decoration: none;
  transition: color 0.2s ease;
}

.register-link a:hover {
  color: #c9362c;
}
</style>
