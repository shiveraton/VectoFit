<template>
  <div class="page-header">
    <h1>My Profile</h1>
  </div>

  <div class="profile-card">
    <div class="profile-avatar">
      <svg viewBox="0 0 24 24" color="#15803d">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 12c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3S14.66 14 13 14zm0 5c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3S14.66 19 13 19z"/>
      </svg>
    </div>
    <div class="profile-info">
      <div class="profile-name">{{ fullName }}</div>
      <div class="profile-email">{{ email }}</div>
      <div class="profile-role" :class="roleClass">
        {{ roleDisplay }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import client from "../config/client";

onMounted(async () => {
  try {
    const response = await client.get("/accounts/me/");
    const user = response.data;
    fullName = user.username || user.email || "Unknown";
    email = user.email || "";
    const isAnnotator = user.is_annotator === true;
    const isStaff = user.is_staff === true;
    
    if (isAnnotator && !isStaff) {
      roleClass = "role-annotator";
      roleDisplay = "Annotator";
    } else if (isStaff) {
      roleClass = "role-admin";
      roleDisplay = "Admin";
    } else {
      roleClass = "role-user";
      roleDisplay = "User";
    }
  } catch (err) {
    console.error("Failed to load profile:", err);
    fullName = "Error loading profile";
    email = "";
    roleClass = "role-user";
    roleDisplay = "User";
  }
</script>

<style scoped>
.page-header {
  text-align: center;
  padding: 24px 0;
  border-bottom: 1px solid #e8edf3;
}

.profile-card {
  max-width: 400px;
  margin: 0 auto;
  padding: 32px 24px;
  background: #ffffff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  text-align: center;
}

.profile-avatar {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  color: #15803d;
}

.profile-info {
  text-align: center;
}

.profile-name {
  font-size: 20px;
  font-weight: 600;
  color: #172033;
  margin-bottom: 8px;
}

.profile-email {
  font-size: 14px;
  color: #718096;
  margin-bottom: 16px;
}

.profile-role {
  margin-top: 16px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.role-annotator {
  color: #15803d;
  background: #f0fdf4;
}

.role-admin {
  color: #1e40af;
  background: #eff6ff;
}

.role-user {
  color: #6b7280;
  background: #f3f4f6;
}