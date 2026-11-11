import { createApiClient } from "./api.js";
import { escapeHtml } from "./format.js";
import { readLanguage, saveLanguage, translate, translations } from "./i18n.js";
import {
  filterMovements,
  filterProducts,
  guide,
  movementsPage,
  overview,
  productsPage,
  rankingsPage,
  setViewContext,
} from "./views.js";

const $ = (selector) => document.querySelector(selector);
const pages = ["overview", "products", "movements", "rankings", "guide"];

let lang = readLanguage();
let state;
let page = "overview";
let mode;
let editingId;
let requestKey;
let toastTimer;

const t = (key) => translate(lang, key);
const errorText = (error) =>
  t(error.message in translations[lang] ? error.message : "unexpected");
const api = createApiClient(() => state?.csrf_token || "");

function notify(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 5000);
}

function query() {
  return new URLSearchParams({
    start: $("#start").value,
    end: $("#end").value,
  }).toString();
}

async function refresh() {
  state = await api(`/api/state?${query()}`);
  render();
}

function setLanguage() {
  document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
  document.title = `Estoque Local · ${t(page)}`;
  $("#language").value = lang;
  document
    .querySelector("nav")
    .setAttribute("aria-label", lang === "pt" ? "Principal" : "Main");

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
}

function render() {
  const hashPage = location.hash.slice(1);
  page = pages.includes(hashPage) ? hashPage : "overview";

  setLanguage();
  setViewContext({
    state,
    language: lang,
    translate: t,
    query,
  });

  document.querySelectorAll("[data-page]").forEach((link) => {
    const isCurrent = link.dataset.page === page;
    link.classList.toggle("active", isCurrent);
    if (isCurrent) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });

  $("#page-title").textContent = t(page);
  $("#page-kicker").textContent = t(`${page}_k`);
  $("#page-description").textContent = t(`${page}_d`);
  $("#demo-banner").hidden = !state.demo;
  $("#demo-banner").textContent = t("demo_banner");
  $("#period").hidden = page === "guide";

  if (page === "guide") {
    $("#content").innerHTML = guide();
    return;
  }

  if (!state.products.length) {
    $("#content").innerHTML = `
      <div class="empty">
        <p class="eyebrow">00 / ESTOQUE LOCAL</p>
        <h2>${t("empty_title")}</h2>
        <p>${t("empty_body")}</p>
        <button class="primary" data-action="new-product">
          ${t("new_product")}
        </button>
        <button class="secondary" data-action="demo">${t("demo")}</button>
      </div>
    `;
    return;
  }

  const pageViews = {
    overview,
    products: productsPage,
    movements: movementsPage,
    rankings: rankingsPage,
  };
  $("#content").innerHTML = pageViews[page]();

  if (page === "products") filterProducts();
  if (page === "movements") filterMovements();
}

function input(label, name, value = "", attributes = "", wide = false) {
  return `
    <label class="${wide ? "wide" : ""}">
      ${t(label)}
      <input
        name="${name}"
        value="${escapeHtml(value)}"
        ${attributes}
      >
    </label>
  `;
}

function showDialog(title, kicker) {
  $("#dialog-title").textContent = title;
  $("#dialog-kicker").textContent = kicker;
  $("#form-error").textContent = "";
  $("#save").disabled = false;
  $("#editor").showModal();
}
function productDialog(id) {
  mode = "product";
  editingId = id;
  const product = state.products.find((item) => item.id === id);
  const price = product ? (product.price_cents / 100).toFixed(2) : "";
  const activeField = product
    ? `
      <label class="checkbox wide">
        <input
          name="active"
          type="checkbox"
          ${product.active ? "checked" : ""}
        >
        ${t("active")}
      </label>
    `
    : "";

  $("#editor-fields").innerHTML = `
    <div class="form-grid">
      ${input(
        "name",
        "name",
        product?.name || "",
        'maxlength="120" required',
        true,
      )}
      ${input("sku", "sku", product?.sku || "", 'maxlength="40" required')}
      ${input("category", "category", product?.category || "", 'maxlength="60"')}
      ${input(
        "supplier",
        "supplier",
        product?.supplier || "",
        'maxlength="120"',
        true,
      )}
      ${input(
        "sale_price",
        "price",
        price,
        'type="number" min="0" max="10000000" step="0.01" required',
      )}
      ${input(
        "minimum",
        "minimum",
        product?.minimum ?? 0,
        'type="number" min="0" max="1000000" step="1" required',
      )}
      <small class="wide">${t("price_hint")}</small>
      ${activeField}
    </div>
  `;
  showDialog(
    t(product ? "edit_product" : "new_product"),
    t("product_form"),
  );
}

function movementDialog(kind = "purchase", productId, originalId) {
  if (!state.products.some((product) => product.active)) {
    notify(t("no_products"));
    return;
  }

  mode = "movement";
  requestKey = crypto.randomUUID();
  const kindOptions = ["purchase", "sale", "return", "loss", "gain"]
    .map(
      (option) => `
        <option value="${option}" ${option === kind ? "selected" : ""}>
          ${t(option)}
        </option>
      `,
    )
    .join("");

  $("#editor-fields").innerHTML = `
    <div class="form-grid">
      <label class="wide">
        ${t("type")}
        <select name="kind" id="move-kind">${kindOptions}</select>
      </label>
      <div id="move-details" class="wide"></div>
    </div>
  `;
  moveDetails(kind, productId, originalId);
  showDialog(t("new_movement").replace(" ↗", ""), t("movement_form"));
}

function returnFields(activeProducts, originalId) {
  const activeIds = new Set(activeProducts.map((product) => product.id));
  const sales = state.returnable.filter((sale) =>
    activeIds.has(sale.product_id),
  );
  const saleOptions = sales
    .map(
      (sale) => `
        <option
          value="${sale.id}"
          ${sale.id === originalId ? "selected" : ""}
        >
          #${sale.id} · ${escapeHtml(sale.name)} ·
          ${sale.returnable} ${t("refund_left")}
        </option>
      `,
    )
    .join("");

  return `
    <label class="wide">
      ${t("sale_reference")}
      <select name="original_id" required>
        <option value="">${t("choose")}</option>
        ${saleOptions}
      </select>
    </label>
    ${input(
      "quantity",
      "quantity",
      1,
      'type="number" min="1" max="1000000" step="1" required',
    )}
    ${input("reason", "note", "", 'maxlength="300"', true)}
    <small class="wide">
      ${t(sales.length ? "return_hint" : "no_returns")}
    </small>
  `;
}

function standardMovementFields(kind, activeProducts, productId) {
  const selectedProduct =
    activeProducts.find((product) => product.id === Number(productId)) ||
    activeProducts[0];
  const productOptions = activeProducts
    .map(
      (product) => `
        <option
          value="${product.id}"
          ${product.id === selectedProduct.id ? "selected" : ""}
        >
          ${escapeHtml(product.name)} ·
          ${product.quantity} ${t("available")}
        </option>
      `,
    )
    .join("");
  const priceField =
    kind === "loss"
      ? ""
      : input(
          kind === "sale" ? "unit_price" : "unit_cost",
          "unit_price",
          kind === "sale"
            ? (selectedProduct.price_cents / 100).toFixed(2)
            : "",
          'type="number" min="0" max="10000000" step="0.01" required',
        );
  const isAdjustment = ["loss", "gain"].includes(kind);
  const noteAttributes = `maxlength="300" ${isAdjustment ? "required" : ""}`;

  return `
    <label class="wide">
      ${t("product")}
      <select name="product_id" id="move-product" required>
        ${productOptions}
      </select>
    </label>
    ${input(
      "quantity",
      "quantity",
      1,
      'type="number" min="1" max="1000000" step="1" required',
    )}
    ${priceField}
    ${input("reason", "note", "", noteAttributes, true)}
    <small class="wide">
      ${t(isAdjustment ? "adjustment_hint" : "move_hint")}
    </small>
  `;
}

function moveDetails(kind, productId, originalId) {
  const activeProducts = state.products.filter((product) => product.active);
  const fields =
    kind === "return"
      ? returnFields(activeProducts, originalId)
      : standardMovementFields(kind, activeProducts, productId);

  $("#move-details").innerHTML = `
    <div class="form-grid">${fields}</div>
  `;
}
$("#editor-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#form-error").textContent = "";
  $("#save").disabled = true;
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    if (mode === "product") {
      data.minimum = Number(data.minimum);
      data.active = editingId
        ? $('#editor-form [name="active"]').checked
        : true;
      await api(
        editingId ? `/api/products/${editingId}` : "/api/products",
        editingId ? "PUT" : "POST",
        data,
      );
    } else {
      data.quantity = Number(data.quantity);
      data.request_key = requestKey;
      if (data.kind === "return") {
        const sale = state.returnable.find(
          (m) => m.id === Number(data.original_id),
        );
        data.product_id = sale?.product_id;
        data.original_id = Number(data.original_id);
      } else data.product_id = Number(data.product_id);
      await api("/api/movements", "POST", data);
    }
    $("#editor").close();
    notify(t("saved"));
    await refresh();
  } catch (error) {
    if ($("#editor").open) $("#form-error").textContent = errorText(error);
    else notify(errorText(error));
  } finally {
    $("#save").disabled = false;
  }
});
$("#editor").addEventListener("change", (event) => {
  if (event.target.id === "move-kind") moveDetails(event.target.value);
  if (event.target.id === "move-product" && $("#move-kind").value === "sale") {
    const p = state.products.find((p) => p.id === Number(event.target.value));
    $('#editor-form [name="unit_price"]').value = (p.price_cents / 100).toFixed(
      2,
    );
  }
});
$("#add-product").onclick = () => productDialog();
$("#add-movement").onclick = () => movementDialog();
$("#close-dialog").onclick = $("#cancel-dialog").onclick = () =>
  $("#editor").close();
$("#period").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await refresh();
  } catch (error) {
    notify(errorText(error));
  }
};
$("#last-30").onclick = async () => {
  const end = new Date(`${state.today}T12:00:00`);
  const first = new Date(end);
  first.setDate(first.getDate() - 29);
  $("#start").value =
    `${first.getFullYear()}-${String(first.getMonth() + 1).padStart(2, "0")}-${String(first.getDate()).padStart(2, "0")}`;
  $("#end").value = state.today;
  try {
    await refresh();
  } catch (error) {
    notify(errorText(error));
  }
};
$("#language").onchange = () => {
  lang = $("#language").value;
  saveLanguage(lang);
  if (state) render();
  else setLanguage();
};
window.addEventListener("hashchange", () => {
  if (state) render();
});
$("#content").addEventListener("input", (event) => {
  if (
    [
      "product-search",
      "category-filter",
      "low-filter",
      "archive-filter",
    ].includes(event.target.id)
  )
    filterProducts();
  if (["movement-search", "kind-filter"].includes(event.target.id))
    filterMovements();
});
$("#content").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.hasAttribute("data-edit"))
    productDialog(Number(button.dataset.edit));
  if (button.hasAttribute("data-buy"))
    movementDialog("purchase", Number(button.dataset.buy));
  if (button.hasAttribute("data-return"))
    movementDialog("return", undefined, Number(button.dataset.return));
  if (button.dataset.action === "new-product") productDialog();
  if (button.dataset.action === "print") window.print();
  if (button.dataset.action === "demo" && window.confirm(t("demo_confirm"))) {
    button.disabled = true;
    try {
      await api("/api/demo", "POST", {});
      await refresh();
    } catch (error) {
      notify(errorText(error));
      button.disabled = false;
    }
  }
});
(async () => {
  setLanguage();
  try {
    state = await api("/api/state");
    $("#start").value = state.start;
    $("#end").value = state.end;
    render();
  } catch (error) {
    $("#content").textContent = errorText(error);
  }
})();
