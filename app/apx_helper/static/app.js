const state = { kind: null, file: null, result: null };

const $ = (id) => document.getElementById(id);
const panels = { kind: $("panel-kind"), upload: $("panel-upload"), result: $("panel-result") };
const steps = [$("step-1"), $("step-2"), $("step-3")];

function goTo(step) {
  Object.values(panels).forEach((p) => p.classList.add("hidden"));
  panels[step].classList.remove("hidden");
  const index = { kind: 0, upload: 1, result: 2 }[step];
  steps.forEach((el, i) => {
    el.classList.toggle("active", i === index);
    el.classList.toggle("done", i < index);
  });
}

function reset() {
  state.kind = null;
  state.file = null;
  state.result = null;
  $("file-input").value = "";
  $("file-name").textContent = "";
  $("library-id").value = "";
  $("btn-process").disabled = true;
  hideError();
  goTo("kind");
}

function showError(message) {
  const box = $("upload-error");
  box.textContent = message;
  box.classList.remove("hidden");
}

function hideError() {
  $("upload-error").classList.add("hidden");
}

document.querySelectorAll(".card").forEach((card) => {
  card.addEventListener("click", () => {
    state.kind = card.dataset.kind;
    $("kind-label").textContent = state.kind === "transaction" ? "Transacción" : "Librería";
    $("library-id-wrapper").classList.toggle("hidden", state.kind !== "library");
    goTo("upload");
  });
});

document.querySelectorAll("[data-back]").forEach((btn) => btn.addEventListener("click", reset));

const dropzone = $("dropzone");
const fileInput = $("file-input");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("over");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("over"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("over");
  if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) selectFile(fileInput.files[0]);
});

function selectFile(file) {
  if (!file.name.toLowerCase().endsWith(".json")) {
    showError("El archivo debe tener extensión .json");
    return;
  }
  hideError();
  state.file = file;
  $("file-name").textContent = file.name;
  $("btn-process").disabled = false;
}

$("btn-process").addEventListener("click", async () => {
  hideError();
  const body = new FormData();
  body.append("file", state.file);
  body.append("expected_kind", state.kind);
  const libraryId = $("library-id").value.trim();
  if (libraryId) body.append("library_id", libraryId);

  $("loader").classList.remove("hidden");
  try {
    const response = await fetch("/api/contracts/process", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) {
      showError(payload.detail || "No se pudo procesar el contrato.");
      return;
    }
    state.result = payload;
    renderResult(payload);
    goTo("result");
  } catch (error) {
    showError(`No se pudo contactar al servidor: ${error.message}`);
  } finally {
    $("loader").classList.add("hidden");
  }
});

function renderResult(payload) {
  $("result-meta").innerHTML = `
    <div>Contrato de <strong>${payload.kindLabel}</strong></div>
    <div>Archivo: <strong>${escapeHtml(payload.filename)}</strong></div>
    <div>Hojas generadas: <strong>${payload.sheets.map(escapeHtml).join(", ")}</strong></div>`;

  const { missing = 0, review = 0, invalid = 0 } = payload.summary;
  const total = missing + review + invalid;
  $("summary").innerHTML = `
    <div class="chip total"><b>${total}</b>pendientes</div>
    <div class="chip missing"><b>${missing}</b>falta información</div>
    <div class="chip review"><b>${review}</b>a revisar</div>
    <div class="chip invalid"><b>${invalid}</b>valor no permitido</div>`;

  const tbody = document.querySelector("#issues tbody");
  tbody.innerHTML = payload.issues
    .map(
      (issue) => `<tr data-severity="${issue.severity}">
        <td><span class="tag ${issue.severity}">${issue.severityLabel}</span></td>
        <td>${escapeHtml(issue.sheet)}</td>
        <td>${issue.cell ? `<code>${issue.cell}</code>` : "—"}</td>
        <td>${escapeHtml(issue.field)}</td>
        <td>${escapeHtml(issue.message)}</td>
      </tr>`
    )
    .join("");

  $("issues").classList.toggle("hidden", total === 0);
  document.querySelector(".filters").classList.toggle("hidden", total === 0);
  $("no-issues").classList.toggle("hidden", total > 0);
  applyFilters();
}

document.querySelectorAll(".filter").forEach((cb) => cb.addEventListener("change", applyFilters));

function applyFilters() {
  const active = [...document.querySelectorAll(".filter:checked")].map((cb) => cb.value);
  document.querySelectorAll("#issues tbody tr").forEach((row) => {
    row.classList.toggle("hidden", !active.includes(row.dataset.severity));
  });
}

$("btn-download").addEventListener("click", () => {
  const binary = atob(state.result.fileBase64);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = state.result.filename;
  link.click();
  URL.revokeObjectURL(url);
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}

reset();
