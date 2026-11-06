import { createRouter, createWebHistory } from "vue-router";
import AnnotatorLayout from "../layouts/AnnotatorLayout.vue";
import AnnotatorHome from "../pages/views/AnnotatorHome.vue";
import DatasetAnnotation from "../pages/views/DatasetAnnotation.vue";
import PublicAuth from "../pages/auth/PublicAuth.vue";
import { publicClient } from "../config/publicAuth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/annotator" },
    { path: "/annotator/login", component: PublicAuth, meta: { authPage: true } },
    { path: "/annotator/register", component: PublicAuth, meta: { authPage: true } },
    { path: "/annotator", component: AnnotatorLayout, meta: { requiresAnnotator: true }, children: [
      { path: "", component: AnnotatorHome },
      { path: ":id(\\d+)", component: DatasetAnnotation },
    ] },
    { path: "/:pathMatch(.*)*", component: { template: '<main><h1>404</h1><p>Page not found.</p></main>' } },
  ],
});

router.beforeEach(async (to) => {
  if (!to.meta.requiresAnnotator) return true;
  try {
    await publicClient.get("me/");
    return true;
  } catch {
    return { path: "/annotator/login", query: { next: to.fullPath } };
  }
});

export default router;
