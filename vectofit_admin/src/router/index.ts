import { createRouter, createWebHistory } from "vue-router";

import AuthLayout from "../layouts/AuthLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";
import Login from "../pages/auth/Login.vue";
import Register from "../pages/auth/Register.vue";
import Dashboard from "../pages/dashboard/Dashboard.vue";
import Features from "../pages/views/Features.vue";
import Training from "../pages/views/Training.vue";
import Dataset from "../pages/views/Datasets.vue";
import Evaluation from "../pages/views/Evaluation.vue";
import Models from "../pages/views/Models.vue";

const routes = [
  {
    path: "/",
    component: AdminLayout,
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: Dashboard,
      },
      {
        path: "dataset",
        name: "Dataset",
        component: Dataset,
      },
      {
        path: "features",
        name: "Features",
        component: Features,
      },
      {
        path: "training",
        name: "Training",
        component: Training,
      },
      {
        path: "evaluation",
        name: "Evaluation",
        component: Evaluation,
      },
      {
        path: "models",
        name: "Models",
        component: Models,
      },
    ],
  },
  {
    path: "/",
    component: AuthLayout,
    children: [
      {
        path: "register",
        name: "Register",
        component: Register,
      },
      {
        path: "login",
        name: "Login",
        component: Login,
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: routes,
});

export default router;
