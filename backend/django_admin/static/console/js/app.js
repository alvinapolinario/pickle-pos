document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-nav-toggle]");
  if (toggle) {
    toggle.addEventListener("click", () => document.body.classList.toggle("nav-open"));
  }
  setupConsoleModals();
});

function setupConsoleModals() {
  const formOverlay = document.querySelector("[data-form-modal]");
  const viewOverlay = document.querySelector("[data-view-modal]");
  if (!formOverlay && !viewOverlay) return;

  const formBody = formOverlay ? formOverlay.querySelector("[data-form-modal-body]") : null;
  const formTitle = formOverlay ? formOverlay.querySelector("#form-modal-title") : null;
  const viewBody = viewOverlay ? viewOverlay.querySelector("[data-view-modal-body]") : null;
  const viewTitle = viewOverlay ? viewOverlay.querySelector("#view-modal-title") : null;

  const openOverlay = (overlay) => {
    if (!overlay) return;
    overlay.hidden = false;
    document.body.classList.add("modal-open");
  };

  const closeOverlays = () => {
    if (formOverlay) formOverlay.hidden = true;
    if (viewOverlay) viewOverlay.hidden = true;
    document.body.classList.remove("modal-open");
  };

  const setupLineForm = (form) => {
    form.querySelectorAll("[data-add-line]").forEach((addBtn) => {
      const key = addBtn.dataset.addLine || "";
      const rows = key ? form.querySelector(`[data-line-rows="${key}"]`) : form.querySelector("[data-line-rows]");
      const template = key ? form.querySelector(`[data-line-template="${key}"]`) : form.querySelector("[data-line-template]");
      const total = key
        ? form.querySelector(`[name="${key}-TOTAL_FORMS"]`)
        : form.querySelector("[name$='-TOTAL_FORMS']");
      if (!rows || !template || !total) return;
      addBtn.addEventListener("click", () => {
        const html = template.innerHTML.replaceAll("__prefix__", String(total.value));
        rows.insertAdjacentHTML("beforeend", html);
        total.value = String(Number(total.value) + 1);
      });
    });
    form.addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove-line]");
      if (!button) return;
      const row = button.closest("tr");
      const del = row.querySelector("input[name$='-DELETE']");
      if (del) {
        del.checked = true;
        row.hidden = true;
      }
    });
    form.addEventListener("change", (event) => {
      const select = event.target.closest("[data-reload-form]");
      if (!select || !select.value) return;
      const url = new URL(form.action, window.location.origin);
      url.searchParams.set(select.dataset.reloadForm, select.value);
      openForm(`${url.pathname}${url.search}`, formTitle ? formTitle.textContent : "");
    });
  };

  const bindForm = () => {
    if (!formBody) return;
    const form = formBody.querySelector("[data-modal-form]");
    if (!form) return;
    setupLineForm(form);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = new FormData(form);
      if (event.submitter && event.submitter.name) {
        body.append(event.submitter.name, event.submitter.value);
      }
      const response = await fetch(form.action, {
        method: "POST",
        body,
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (response.status === 204) {
        window.location.reload();
        return;
      }
      formBody.innerHTML = await response.text();
      bindForm();
    });
  };

  const openForm = async (url, title) => {
    if (!formOverlay || !formBody || !formTitle) return;
    formTitle.textContent = title || "Edit";
    formBody.innerHTML = "<p class='row-sub'>Loading…</p>";
    openOverlay(formOverlay);
    const separator = url.includes("?") ? "&" : "?";
    const response = await fetch(`${url}${separator}partial=1`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    formBody.innerHTML = await response.text();
    bindForm();
  };

  const openView = (row) => {
    if (!viewOverlay || !viewBody || !viewTitle || !row) return;
    const entries = [...row.attributes]
      .filter((attr) => attr.name.startsWith("data-view-") && attr.name !== "data-view-title")
      .map((attr) => {
        const label = attr.name.replace("data-view-", "").replace(/-/g, " ");
        return `<div class="detail-row"><span>${label}</span><strong>${attr.value}</strong></div>`;
      })
      .join("");
    viewTitle.textContent = row.dataset.viewTitle || "Details";
    viewBody.innerHTML = `<div class="detail-list">${entries}</div>`;
    openOverlay(viewOverlay);
  };

  const openViewFromUrl = async (url, title) => {
    if (!viewOverlay || !viewBody || !viewTitle) return;
    viewTitle.textContent = title || "Details";
    viewBody.innerHTML = "<p class='row-sub'>Loading…</p>";
    openOverlay(viewOverlay);
    const separator = url.includes("?") ? "&" : "?";
    const response = await fetch(`${url}${separator}partial=1`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    viewBody.innerHTML = await response.text();
  };

  document.addEventListener("click", (event) => {
    const closer = event.target.closest("[data-modal-close]");
    if (closer) {
      event.preventDefault();
      closeOverlays();
    }
  });

  document.querySelectorAll("[data-open-form]").forEach((button) => {
    button.addEventListener("click", () => openForm(button.dataset.openForm, button.dataset.modalTitle));
  });

  document.querySelectorAll("[data-open-view]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.openView) {
        openViewFromUrl(button.dataset.openView, button.dataset.modalTitle);
      } else {
        openView(button.closest("tr"));
      }
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  [formOverlay, viewOverlay].filter(Boolean).forEach((overlay) => {
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) closeOverlays();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("modal-open")) {
      closeOverlays();
    }
  });

  const params = new URLSearchParams(window.location.search);
  const modal = params.get("modal");
  const id = params.get("id");
  if (modal === "create") {
    const createButton = document.querySelector("[data-modal-key='create'], [data-open-form]");
    if (createButton) openForm(createButton.dataset.openForm, createButton.dataset.modalTitle);
  } else if (modal && id) {
    const suffix = modal === "edit" ? "/edit/" : `/${modal}/`;
    const button = document.querySelector(`[data-open-form*="/${id}${suffix}"]`);
    if (button) openForm(button.dataset.openForm, button.dataset.modalTitle);
  } else if (modal) {
    const keyed = document.querySelector(`[data-modal-key="${modal}"]`);
    if (keyed) {
      let url = keyed.dataset.openForm;
      const productId = params.get("product");
      const poId = params.get("po");
      if (productId && !url.includes("product=")) {
        url += `${url.includes("?") ? "&" : "?"}product=${productId}`;
      }
      if (poId && !url.includes("po=")) {
        url += `${url.includes("?") ? "&" : "?"}po=${poId}`;
      }
      openForm(url, keyed.dataset.modalTitle);
    }
  }
}
