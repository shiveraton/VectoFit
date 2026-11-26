const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function compile(relative, requireMock, dev = false) {
  const filename = path.join(__dirname, "../src", relative);
  const exports = {};
  const output = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  vm.runInNewContext(output, { exports, require: requireMock, __DEV__: dev }, { filename });
  return exports;
}

function hookHarness(data, overrides = {}) {
  const auth = { token: "session-token", user: { id: "owner-1" } };
  const calls = [];
  let queryOptions, mutationOptions;
  const query = { data, isError: false, isFetching: false, refetch: async () => { calls.push("refresh"); }, ...overrides };
  const store = select => select(auth);
  store.getState = () => auth;
  const mutation = { isPending: false, isError: false, reset: () => calls.push("reset"),
    mutateAsync: async () => {
      const result = await mutationOptions.mutationFn();
      await mutationOptions.onSuccess(result);
    },
  };
  const module = compile("features/session-results/hooks/useSessionResult.ts", name => {
    if (name === "@tanstack/react-query") return {
      useQueryClient: () => ({ setQueryData: (key, value) => calls.push({ key, value }) }),
      useQuery: options => { queryOptions = options; return query; },
      useMutation: options => { mutationOptions = options; return mutation; },
    };
    if (name === "axios") return { isAxiosError: value => Boolean(value?.isAxiosError) };
    if (name.endsWith("useAuthStore")) return { default: store, __esModule: true };
    if (name.endsWith("sessionResultService")) return {
      getLiveSession: async (id, signal) => { calls.push({ get: id, signal }); return data; },
      retryLiveSession: async id => { calls.push({ retry: id }); return { id, status: "PENDING" }; },
    };
    throw new Error("Unexpected import " + name);
  });
  return { module, run: id => module.default(id), auth, query, mutation, calls,
    options: () => queryOptions };
}

test("saved sessions use live results; fixtures require an explicit development branch", () => {
  const Live = () => null, Preview = () => null;
  const load = dev => compile("screens/SessionResultScreen.tsx", name => {
    if (name === "react/jsx-runtime") return { jsx: (type, props) => ({ type, props }) };
    if (name.endsWith("SessionResultLive")) return { default: Live, __esModule: true };
    if (name.endsWith("SessionResultPreview")) return { default: Preview, __esModule: true };
    throw new Error(name);
  }, dev).default;
  const props = { route: { params: { sessionId: 12, previewFixture: "main" } } };
  assert.equal(load(false)(props).type, Live);
  assert.equal(load(true)(props).type, Preview);
  assert.equal(load(true)({ route: { params: { sessionId: 12 } } }).type, Live);
});

test("live state mapping does not invent processing stages or successful results", () => {
  const h = hookHarness();
  assert.equal(h.module.sessionState({ status: "PROCESSING" }).status, "loading");
  assert.equal(h.module.sessionState({ status: "PROCESSING" }).stage, undefined);
  assert.equal(h.module.sessionState({ status: "COMPLETED", view_angle: "frontal", session_result: null }).status, "error");
  assert.equal(h.module.sessionState({ status: "FAILED", session_saved: false }).error.sessionSaved, false);
  assert.equal(h.module.sessionState({ status: "FAILED", session_saved: true }).error.sessionSaved, true);
  const result = { sessionId: "12" };
  assert.equal(h.module.sessionState({ status: "COMPLETED", session_result: result }).data, result);
});

test("live queries are scoped to owner and session, consume cancellation and poll only processing states", async () => {
  const h = hookHarness({ id: 12, status: "PENDING" });
  assert.equal(h.run(12).state.status, "loading");
  assert.equal(h.options().queryKey.join(","), "session-result,owner-1,12");
  assert.equal(h.options().refetchInterval({ state: { data: { status: "PENDING" } } }), 3000);
  assert.equal(h.options().refetchInterval({ state: { data: { status: "COMPLETED" } } }), false);
  const signal = {};
  await h.options().queryFn({ signal });
  assert.equal(h.calls[0].signal, signal);
  h.auth.token = null;
  assert.equal(h.run(12).state.status, "error");
  assert.equal(h.options().enabled, false);
});

test("network failures refresh GET while failed processing uses the confirmed retry endpoint", async () => {
  const network = hookHarness(undefined, { isError: true, error: { isAxiosError: true } });
  assert.equal(network.run(12).state.error.kind, "network");
  await network.run(12).retry();
  assert.equal(network.calls.join(","), "refresh");
  const failed = hookHarness({ id: 12, status: "FAILED", session_saved: true });
  await failed.run(12).retry();
  assert.equal(failed.calls[0].retry, 12);
  assert.equal(failed.calls[1].value.status, "PENDING");
  assert.equal(failed.calls[2], "refresh");
});

test("a retry response arriving after sign-out cannot repopulate another session's cache", async () => {
  const h = hookHarness({ id: 12, status: "FAILED" });
  const hook = h.run(12);
  h.auth.token = "different-login";
  await hook.retry();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].retry, 12);
});

test("conflicting retry is refreshed and owner-denied responses never become saved results", async () => {
  const h = hookHarness({ id: 12, status: "FAILED" });
  h.mutation.mutateAsync = async () => { throw { isAxiosError: true, response: { status: 409 } }; };
  await h.run(12).retry();
  assert.equal(h.calls.join(","), "reset,refresh");
  const denied = hookHarness(undefined, { isError: true, error: { isAxiosError: true, response: { status: 404 } } });
  assert.equal(denied.run(12).state.status, "error");
  assert.equal(denied.run(12).state.error.kind, "unknown");
});

test("live service requests only the confirmed JSON endpoint and rejects mismatched identities", async () => {
  const calls = [];
  let result = { id: 12, status: "COMPLETED", session_result: { sessionId: "12" } };
  const service = compile("features/session-results/services/sessionResultService.ts", name => {
    if (name.endsWith("api/client")) return { __esModule: true, default: {
      get: async (url, options) => { calls.push({ url, options }); return { data: result }; },
      post: async url => { calls.push({ url }); return { data: { id: 12, status: "PENDING" } }; },
    } };
    if (name.endsWith("validation")) return { assertSessionResult() {} };
    throw new Error(name);
  });
  const signal = {};
  await service.getLiveSession(12, signal);
  assert.equal(calls[0].url, "/assessments/sessions/12/");
  assert.equal(calls[0].options.params.include, "reps");
  assert.equal(calls[0].options.signal, signal);
  await service.retryLiveSession(12);
  assert.equal(calls[1].url, "/assessments/sessions/12/retry/");
  result.session_result.sessionId = "99";
  await assert.rejects(service.getLiveSession(12), /identity mismatch/);
});
