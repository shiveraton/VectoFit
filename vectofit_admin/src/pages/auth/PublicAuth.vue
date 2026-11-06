<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { initializeCsrf, publicClient } from "../../config/publicAuth";

const route = useRoute();
const router = useRouter();
const registering = computed(() => route.path.endsWith("/register"));
const username = ref("");
const email = ref("");
const password = ref("");
const confirmation = ref("");
const invitation = ref("");
const error = ref("");
const busy = ref(false);
const next = computed(() => {
  const value = route.query.next;
  return typeof value === "string" && /^\/annotator(?:\/\d+)?(?:[?#].*)?$/.test(value)
    ? value : "/annotator";
});
async function submit() {
  busy.value = true;
  error.value = "";
  try {
    await initializeCsrf();
    if (registering.value) {
      await publicClient.post("register/", {
        username: username.value, email: email.value, password: password.value,
        confirm_password: confirmation.value, invitation_code: invitation.value,
      });
    }
    const { data } = await publicClient.post("login/", { username: username.value, password: password.value });
    publicClient.defaults.headers.common["X-CSRFToken"] = data.csrfToken;
    password.value = "";
    confirmation.value = "";
    invitation.value = "";
    await router.replace(next.value);
  } catch (err: unknown) {
    const response = (err as { response?: { data?: unknown } }).response;
    error.value = response?.data ? JSON.stringify(response.data) : "Unable to connect. Please try again.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="public-auth">
    <form @submit.prevent="submit">
      <h1>{{ registering ? "Create annotator account" : "Annotator sign in" }}</h1>
      <label>Username<input v-model="username" autocomplete="username" maxlength="150" required /></label>
      <label v-if="registering">Email<input v-model="email" type="email" autocomplete="email" required /></label>
      <label>Password<input v-model="password" type="password" :autocomplete="registering ? 'new-password' : 'current-password'" required /></label>
      <label v-if="registering">Confirm password<input v-model="confirmation" type="password" autocomplete="new-password" required /></label>
      <label v-if="registering">Invitation code<input v-model="invitation" type="password" autocomplete="off" required /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <button class="primary-button" :disabled="busy">{{ busy ? "Please wait..." : registering ? "Register and sign in" : "Sign in" }}</button>
      <RouterLink :to="{ path: registering ? '/annotator/login' : '/annotator/register', query: { next } }">
        {{ registering ? "Already registered? Sign in" : "Register with an invitation" }}
      </RouterLink>
    </form>
  </main>
</template>

<style scoped>
.public-auth { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
form { display: grid; gap: 18px; width: min(100%, 420px); }
label { display: grid; gap: 6px; }
input { padding: 12px; border: 1px solid #d4d4d8; border-radius: 6px; font: inherit; }
[role="alert"] { color: #b42318; overflow-wrap: anywhere; }
</style>
