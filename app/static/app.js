const state = {
  token: localStorage.getItem("devplane_token"),
  user: null,
  serviceId: null,
  envId: null,
};

const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function toast(message, isError = false) {
  const node = $("toast");
  node.textContent = message;
  node.className = isError ? "toast error" : "toast";
  node.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    node.hidden = true;
  }, 4500);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status text */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function showApp(user) {
  state.user = user;
  $("login-panel").hidden = true;
  $("app-panel").hidden = false;
  $("logout").hidden = false;
  $("whoami").textContent = `${user.email} (${user.role})`;
  refreshServices();
}

function resetSelect(select, items, label) {
  select.innerHTML = items
    .map((item) => `<option value="${esc(item.id)}">#${esc(item.id)} ${esc(label(item))}</option>`)
    .join("");
}

async function refreshServices() {
  try {
    const services = await api("/api/v1/services");
    $("services").innerHTML = services.length
      ? services
          .map(
            (s) => `<div class="card">
              <div class="card-head"><strong>#${esc(s.id)} ${esc(s.name)}</strong>
                <span class="badge">${esc(s.status)}</span></div>
              <div class="muted">${esc(s.tech_stack || "unclassified")} &middot; owner #${esc(s.owner_id)}</div>
              <a href="${esc(s.repo_url)}" target="_blank" rel="noreferrer">${esc(s.repo_url)}</a>
              <p>${esc(s.description || "")}</p>
            </div>`
          )
          .join("")
      : `<p class="muted">No services yet. Create one above.</p>`;

    for (const select of [$("service-select"), $("config-service-select")]) {
      resetSelect(select, services, (s) => s.name);
      if (services.length && !select.value) select.value = services[0].id;
    }
    state.serviceId = Number($("service-select").value) || null;
    if (state.serviceId) {
      await refreshEnvironments(state.serviceId);
      await refreshFlags(state.serviceId);
    }
  } catch (err) {
    toast(err.message, true);
  }
}

async function refreshEnvironments(serviceId) {
  try {
    const envs = await api(`/api/v1/services/${serviceId}/environments`);
    $("envs").innerHTML = envs.length
      ? envs
          .map(
            (e) => `<div class="card">
              <div class="card-head"><strong>#${esc(e.id)} ${esc(e.name)}</strong>
                <span class="badge ${esc(e.status)}">${esc(e.status)}</span></div>
              <div class="muted">${esc(e.env_type)} &middot; ns ${esc(e.cluster_namespace)}
                ${e.ttl_minutes ? `&middot; TTL ${esc(e.ttl_minutes)}m` : ""}</div>
              ${e.status !== "terminated" ? `<button class="danger" data-action="terminate-env" data-id="${esc(e.id)}">Terminate</button>` : ""}
            </div>`
          )
          .join("")
      : `<p class="muted">No environments for this service.</p>`;

    const select = $("env-select");
    resetSelect(select, envs.filter((e) => e.status !== "terminated"), (e) => `${e.name} (${e.env_type})`);
    state.envId = Number(select.value) || null;
    if (state.envId) await refreshDeployments(state.envId);
    else $("deps").innerHTML = `<p class="muted">No deployable environments.</p>`;
  } catch (err) {
    toast(err.message, true);
  }
}

async function refreshDeployments(envId) {
  try {
    const deployments = await api(`/api/v1/environments/${envId}/deployments`);
    $("deps").innerHTML = deployments.length
      ? deployments
          .map(
            (d) => `<div class="card">
              <div class="card-head"><strong>#${esc(d.id)} ${esc(d.version)}</strong>
                <span class="badge ${esc(d.status)}">${esc(d.status)}</span></div>
              <div class="muted">${esc(d.strategy)} &middot; ${esc(d.triggered_by)}
                ${d.is_rollback ? "&middot; rollback" : ""} &middot; ${esc(d.execution_mode || "simulated")}</div>
              <pre class="snippet">${esc(d.logs_snippet)}</pre>
              ${d.status === "succeeded" ? `<button data-action="rollback" data-id="${esc(d.id)}">Roll back to previous</button>` : ""}
            </div>`
          )
          .join("")
      : `<p class="muted">No deployments yet.</p>`;
  } catch (err) {
    toast(err.message, true);
  }
}

async function refreshFlags(serviceId) {
  try {
    const [flags, secrets] = await Promise.all([
      api(`/api/v1/services/${serviceId}/flags`),
      api(`/api/v1/services/${serviceId}/secrets`),
    ]);
    $("flags").innerHTML = flags.length
      ? flags
          .map(
            (f) => `<div class="card">
              <div class="card-head"><strong>${esc(f.key)}</strong>
                <span class="badge ${f.enabled ? "running" : "terminated"}">${f.enabled ? "on" : "off"}</span></div>
              <div class="muted">${esc(f.description || "no description")}</div>
              <button data-action="toggle-flag" data-id="${esc(f.id)}" data-enabled="${f.enabled}">
                ${f.enabled ? "Disable" : "Enable"}
              </button>
              <button class="danger" data-action="delete-flag" data-id="${esc(f.id)}">Delete</button>
            </div>`
          )
          .join("")
      : `<p class="muted">No feature flags.</p>`;
    $("secrets").innerHTML = secrets.length
      ? secrets
          .map(
            (s) => `<div class="card">
              <div class="card-head"><strong>${esc(s.name)}</strong>
                <span class="badge">${esc(s.provider)}</span></div>
              <code>${esc(s.ref_path)}</code>
              <button class="danger" data-action="delete-secret" data-id="${esc(s.id)}">Delete</button>
            </div>`
          )
          .join("")
      : `<p class="muted">No secret references.</p>`;
  } catch (err) {
    toast(err.message, true);
  }
}

async function refreshOpsTools() {
  try {
    const data = await api("/api/v1/ops/tools");
    $("tools").innerHTML = data.tools
      .map(
        (t) => `<div class="card">
          <strong>${esc(t.name)}</strong>
          <div class="muted">${esc(t.description)}</div>
          <code>GET ${esc(t.path)}</code>
          <div class="muted">Requires: ${esc(t.requires)}</div>
        </div>`
      )
      .join("");
    $("ops-tool").innerHTML = data.tools
      .map((t) => `<option value="${esc(t.name)}">${esc(t.name)}</option>`)
      .join("");
  } catch (err) {
    toast(err.message, true);
  }
}

async function refreshAdmin() {
  try {
    $("admin-out").textContent = JSON.stringify(await api("/api/v1/admin/metrics"), null, 2);
    await refreshAudit();
  } catch (err) {
    $("admin-out").textContent = err.message;
    $("audit-out").textContent = "";
  }
}

async function refreshAudit() {
  try {
    $("audit-out").textContent = JSON.stringify(await api("/api/v1/admin/audit?limit=50"), null, 2);
  } catch (err) {
    $("audit-out").textContent = err.message;
  }
}

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = new URLSearchParams({ username: fd.get("email"), password: fd.get("password") });
  try {
    const token = await api("/api/v1/auth/login", {
      method: "POST",
      body,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    state.token = token.access_token;
    localStorage.setItem("devplane_token", state.token);
    showApp(await api("/api/v1/auth/me"));
  } catch (err) {
    toast(err.message, true);
  }
});

$("logout").addEventListener("click", () => {
  localStorage.removeItem("devplane_token");
  location.reload();
});

document.querySelectorAll("nav button").forEach((btn) => {
  btn.addEventListener("click", async () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll("article").forEach((el) => {
      el.hidden = true;
    });
    $(btn.dataset.tab).hidden = false;
    if (btn.dataset.tab === "delivery") {
      state.serviceId = Number($("service-select").value) || null;
      if (state.serviceId) await refreshEnvironments(state.serviceId);
    }
    if (btn.dataset.tab === "config") {
      state.serviceId = Number($("config-service-select").value) || null;
      if (state.serviceId) await refreshFlags(state.serviceId);
    }
    if (btn.dataset.tab === "ops") await refreshOpsTools();
    if (btn.dataset.tab === "admin") await refreshAdmin();
  });
});

$("svc-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = Object.fromEntries(new FormData(e.target));
    await api("/api/v1/services", { method: "POST", body: JSON.stringify(payload) });
    e.target.reset();
    await refreshServices();
    toast("Service created");
  } catch (err) {
    toast(err.message, true);
  }
});

$("service-select").addEventListener("change", async (e) => {
  state.serviceId = Number(e.target.value);
  await refreshEnvironments(state.serviceId);
});

$("config-service-select").addEventListener("change", async (e) => {
  state.serviceId = Number(e.target.value);
  await refreshFlags(state.serviceId);
});

$("env-select").addEventListener("change", async (e) => {
  state.envId = Number(e.target.value);
  if (state.envId) await refreshDeployments(state.envId);
});

$("env-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const serviceId = Number($("service-select").value);
  if (!serviceId) return toast("Create a service first", true);
  const payload = {
    name: fd.get("name"),
    env_type: fd.get("env_type"),
    cluster_namespace: fd.get("cluster_namespace") || "default",
  };
  if (fd.get("ttl_minutes")) payload.ttl_minutes = Number(fd.get("ttl_minutes"));
  try {
    const env = await api(`/api/v1/services/${serviceId}/environments`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    toast(`Environment #${env.id} provisioning`);
    await refreshEnvironments(serviceId);
  } catch (err) {
    toast(err.message, true);
  }
});

$("dep-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const envId = Number(fd.get("env_id"));
  if (!envId) return toast("Provision an environment first", true);
  try {
    const dep = await api(`/api/v1/environments/${envId}/deployments`, {
      method: "POST",
      body: JSON.stringify({
        version: fd.get("version"),
        commit_sha: fd.get("commit_sha") || "",
        strategy: fd.get("strategy"),
      }),
    });
    toast(`Deployment #${dep.id} queued`);
    await refreshDeployments(envId);
  } catch (err) {
    toast(err.message, true);
  }
});

$("flag-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const serviceId = Number($("config-service-select").value);
  if (!serviceId) return toast("Create a service first", true);
  const fd = new FormData(e.target);
  try {
    await api(`/api/v1/services/${serviceId}/flags`, {
      method: "POST",
      body: JSON.stringify({
        key: fd.get("key"),
        description: fd.get("description") || "",
        enabled: fd.get("enabled") === "on",
      }),
    });
    e.target.reset();
    await refreshFlags(serviceId);
    toast("Flag created");
  } catch (err) {
    toast(err.message, true);
  }
});

$("secret-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const serviceId = Number($("config-service-select").value);
  if (!serviceId) return toast("Create a service first", true);
  const fd = new FormData(e.target);
  try {
    await api(`/api/v1/services/${serviceId}/secrets`, {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(fd)),
    });
    e.target.reset();
    await refreshFlags(serviceId);
    toast("Secret reference created");
  } catch (err) {
    toast(err.message, true);
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  try {
    if (button.dataset.action === "terminate-env") {
      await api(`/api/v1/services/environments/${id}/terminate`, { method: "POST" });
      await refreshEnvironments(Number($("service-select").value));
    }
    if (button.dataset.action === "rollback") {
      await api(`/api/v1/deployments/${id}/rollback`, { method: "POST" });
      await refreshDeployments(Number($("env-select").value));
      toast("Rollback deployment queued");
    }
    if (button.dataset.action === "toggle-flag") {
      const serviceId = Number($("config-service-select").value);
      await api(`/api/v1/services/${serviceId}/flags/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: button.dataset.enabled !== "true" }),
      });
      await refreshFlags(serviceId);
    }
    if (button.dataset.action === "delete-flag") {
      const serviceId = Number($("config-service-select").value);
      await api(`/api/v1/services/${serviceId}/flags/${id}`, { method: "DELETE" });
      await refreshFlags(serviceId);
    }
    if (button.dataset.action === "delete-secret") {
      const serviceId = Number($("config-service-select").value);
      await api(`/api/v1/services/${serviceId}/secrets/${id}`, { method: "DELETE" });
      await refreshFlags(serviceId);
    }
  } catch (err) {
    toast(err.message, true);
  }
});

$("ops-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const tool = fd.get("tool");
  const namespace = fd.get("namespace") || "default";
  const pod = fd.get("pod");
  const urls = {
    get_pods: `/api/v1/ops/pods?namespace=${encodeURIComponent(namespace)}`,
    get_logs: `/api/v1/ops/logs?pod=${encodeURIComponent(pod || "devplane-api-0")}&namespace=${encodeURIComponent(namespace)}`,
    deployment_status: `/api/v1/ops/deployment-status?namespace=${encodeURIComponent(namespace)}`,
    terraform_plan_status: "/api/v1/ops/terraform-plan-status",
    jenkins_job_status: "/api/v1/ops/jenkins-job-status",
  };
  try {
    $("ops-out").textContent = JSON.stringify(await api(urls[tool]), null, 2);
  } catch (err) {
    $("ops-out").textContent = err.message;
  }
});

$("audit-refresh").addEventListener("click", refreshAudit);

(async () => {
  if (!state.token) return;
  try {
    showApp(await api("/api/v1/auth/me"));
  } catch {
    localStorage.removeItem("devplane_token");
    state.token = null;
  }
})();
