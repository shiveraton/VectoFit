import { createRouter, createWebHistory } from "vue-router";

import AuthLayout from "../layouts/AuthLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";
import AnnotatorLayout from "../layouts/AnnotatorLayout.vue";
import Login from "../pages/auth/Login.vue";
import Register from "../pages/auth/Register.vue";
import Dashboard from "../pages/dashboard/Dashboard.vue";
import Training from "../pages/views/Training.vue";
import Dataset from "../pages/views/Datasets.vue";
import DatasetAnnotation from "../pages/views/DatasetAnnotation.vue";
import Models from "../pages/views/Models.vue";
import PilotResults from "../pages/views/PilotResults.vue";
import AnnotatorHome from "../pages/views/AnnotatorHome.vue";

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
        path: "dataset/:id/annotate",
        name: "DatasetAnnotation",
        component: DatasetAnnotation,
      },
      {
        path: "training",
        name: "Training",
        component: Training,
      },
      {
        path: "evaluation",
        redirect: {
          name: "Models",
        },
      },
      {
        path: "models",
        name: "Models",
        component: Models,
      },
      {
        path: "pilot-results",
        name: "PilotResults",
        component: PilotResults,
      },
    ],
  },
  {
    path: "/annotator",
    component: AnnotatorLayout,
    children: [
      { path: "", name: "AnnotatorHome", component: AnnotatorHome },
      {
        path: ":id",
        name: "AnnotatorDataset",
        component: DatasetAnnotation,
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
