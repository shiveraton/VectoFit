import { createRouter, createWebHistory } from "vue-router";

import AnnotatorLayout from "../layouts/AnnotatorLayout.vue";
import AuthLayout from "../layouts/AuthLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";
import Login from "../pages/auth/Login.vue";
import Register from "../pages/auth/Register.vue";
import Dashboard from "../pages/dashboard/Dashboard.vue";
import Training from "../pages/views/Training.vue";
import Dataset from "../pages/views/Datasets.vue";
import DatasetAnnotation from "../pages/views/DatasetAnnotation.vue";
import Models from "../pages/views/Models.vue";
import AnnotationQueue from "../pages/views/AnnotationQueue.vue";
import AnnotationWorkspace from "../components/annotation/AnnotationWorkspace.vue";
import client from "../config/client";
import Experiments from "../pages/views/Experiments.vue";

const routes = [
  {
    path: "/",
    component: AdminLayout,
    children: [
      {
        path: "annotation-queue",
        name: "AnnotationQueue",
        component: AnnotationQueue,
        meta: { roles: ["admin", "annotator"] },
      },
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
        meta: { roles: ["admin", "annotator"] },
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
        path: "experiments",
        name: "Experiments",
        component: Experiments,
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
  {
    path: "/annotator",
    component: AnnotatorLayout,
    children: [
      {
        path: "",
        name: "AnnotatorDashboard",
        redirect: { name: "AnnotatorDatasets" },
      },
      {
        path: "dashboard",
        name: "AnnotatorDashboard",
        component: () => import("../pages/annotator/AnnotatorDashboard.vue"),
      },
      {
        path: "datasets",
        name: "AnnotatorDatasets",
        component: () => import("../pages/annotator/AnnotatorDatasets.vue"),
      },
      {
        path: "datasets/:id/annotate",
        name: "AnnotatorDatasetAnnotation",
        component: AnnotationWorkspace,
        meta: { roles: ["annotator"] },
      },
      {
        path: "progress",
        name: "AnnotatorProgress",
        component: () => import("../pages/annotator/AnnotatorProgress.vue"),
      },
      {
        path: "profile",
        name: "AnnotatorProfile",
        component: () => import("../pages/annotator/AnnotatorProfile.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: routes,
});

router.beforeEach(async (to) => {
  const token = localStorage.getItem("token");
  if (!token)
    return to.name === "Login" || to.name === "Register"
      ? true
      : { name: "Login" };
  if (!localStorage.getItem("role")) {
    try {
      const response = await client.get("/accounts/me/");
      localStorage.setItem("role", response.data.role);
      localStorage.setItem("is_staff", String(response.data.is_staff));
      localStorage.setItem("is_annotator", String(response.data.is_annotator));
    } catch {
      localStorage.removeItem("token");
      return { name: "Login" };
    }
  }
  if (to.name === "Login" || to.name === "Register") {
    return localStorage.getItem("is_annotator") === "true"
      ? { name: "AnnotatorDashboard" }
      : { name: "Dashboard" };
  }
  const isStaff = localStorage.getItem("is_staff") === "true";
  const isAnnotator = localStorage.getItem("is_annotator") === "true";
  if (
    isAnnotator &&
    !isStaff &&
    !to.matched.some((record) =>
      (record.meta.roles as string[] | undefined)?.includes("annotator"),
    )
  )
    return { name: "AnnotationQueue" };
  return true;
});

export default router;
