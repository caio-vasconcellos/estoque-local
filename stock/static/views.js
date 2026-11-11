import { createFormatters, escapeHtml } from "./format.js";
import { guideArticles } from "./guide.js";

const $ = (selector) => document.querySelector(selector);

let state;
let language;
let t;
let query;
let money;
let number;
let percent;
let formattedDate;

export function setViewContext(context) {
  state = context.state;
  language = context.language;
  t = context.translate;
  query = context.query;

  const formatters = createFormatters(language);
  money = formatters.money;
  number = formatters.number;
  percent = formatters.percent;
  formattedDate = formatters.date;
}

function metric(label, value, hint, positive = false) {
  return `
    <div class="metric ${positive ? "positive" : ""}">
      <p class="metric-label">${t(label)}</p>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(hint)}</small>
    </div>
  `;
}

function rankedRows(rows, field, formatValue) {
  if (!rows.length) {
    return `<p class="definition">${t("no_eligible")}</p>`;
  }

  return rows
    .slice(0, 5)
    .map(
      (product, index) => `
        <div class="rank-row">
          <span class="rank-number">
            ${String(index + 1).padStart(2, "0")}
          </span>
          <div>
            <b>${escapeHtml(product.name)}</b>
            <small>
              ${escapeHtml(product.sku)} /
              ${number(product.sold)} ${t("units")} ·
              ${t("margin")} ${percent(product.margin)}
            </small>
          </div>
          <div class="rank-value ${product[field] < 0 ? "negative" : ""}">
            ${escapeHtml(formatValue(product[field]))}
          </div>
        </div>
      `,
    )
    .join("");
}

function sortedProducts(field, ascending = false, filter = () => true) {
  return state.products
    .filter(
      (product) =>
        (product.active ||
          product.sold !== 0 ||
          product.revenue !== 0 ||
          product.purchases !== 0) &&
        filter(product),
    )
    .sort((left, right) => {
      const difference = ascending
        ? left[field] - right[field]
        : right[field] - left[field];
      return difference || left.name.localeCompare(right.name);
    });
}

function ranking(
  title,
  field,
  formatValue,
  description,
  ascending = false,
  filter = () => true,
) {
  const currentValue = ["rank_cost", "rank_capital"].includes(description);
  const products = sortedProducts(field, ascending, filter);

  return `
    <section class="panel">
      <p class="panel-caption">
        ${t(currentValue ? "current_balance" : "period")}
      </p>
      <h2>${t(title)}</h2>
      ${rankedRows(products, field, formatValue)}
      <p class="definition">${t(description)}</p>
    </section>
  `;
}

function revenueChart(rows) {
  if (!rows.length) {
    return `<p class="definition">${t("no_data")}</p>`;
  }

  const largestRevenue = Math.max(
    1,
    ...rows.map((row) => Math.abs(row.revenue)),
  );
  const columnWidth = 580 / rows.length;
  const bars = rows
    .map((row, index) => {
      const height = Math.max(1, (Math.abs(row.revenue) / largestRevenue) * 85);
      const y = row.revenue >= 0 ? 105 - height : 105;
      const visibleHeight = row.revenue >= 0 ? height : height * 0.3;

      return `
        <rect
          x="${10 + index * columnWidth}"
          y="${y}"
          width="${Math.max(1, columnWidth - 6)}"
          height="${visibleHeight}"
        >
          <title>
            ${escapeHtml(formattedDate(row.day))}: ${escapeHtml(money(row.revenue))}
          </title>
        </rect>
      `;
    })
    .join("");

  return `
    <svg
      viewBox="0 0 600 140"
      class="chart"
      role="img"
      aria-label="${t("revenue_chart")}"
    >
      <line x1="0" x2="600" y1="105" y2="105" stroke="#b4c2ab"></line>
      ${bars}
    </svg>
    <div class="chart-axis">
      <span>${formattedDate(rows[0].day)}</span>
      <span>${formattedDate(rows.at(-1).day)}</span>
    </div>
  `;
}

function lowStockTable(products) {
  if (!products.length) {
    return `<p class="definition">${t("all_good")}</p>`;
  }

  const rows = products
    .map(
      (product) => `
        <tr>
          <td>
            <strong>${escapeHtml(product.name)}</strong>
            <small>${escapeHtml(product.sku)}</small>
          </td>
          <td class="num negative">${product.quantity}</td>
          <td class="num">${product.minimum}</td>
          <td class="num">
            <button class="text-link" data-buy="${product.id}">
              ${t("purchase")} ↗
            </button>
          </td>
        </tr>
      `,
    )
    .join("");

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>${t("product")}</th>
            <th class="num">${t("stock")}</th>
            <th class="num">${t("minimum")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

export function overview() {
  const totals = state.totals;
  const lowStock = state.products
    .filter(
      (product) =>
        product.active && product.quantity <= product.minimum,
    )
    .sort((left, right) => left.quantity - right.quantity);
  const excludedExpenses =
    language === "pt"
      ? "Despesas operacionais, impostos sobre vendas e taxas não são descontados. As perdas de estoque aparecem separadamente."
      : "Operating expenses, sales taxes and fees are not deducted. Inventory losses are shown separately.";

  return `
    <div class="metrics">
      ${metric("revenue", money(totals.revenue), t("net_returns"))}
      ${metric(
        "profit",
        money(totals.profit),
        `${t("margin")}: ${percent(totals.margin)}`,
        true,
      )}
      ${metric("stock_value", money(totals.stock_value), t("current_note"))}
      ${metric("low_stock", number(totals.low_stock), t("products_unit"))}
    </div>

    <div class="two-columns">
      <section class="panel">
        <div class="section-head">
          <div>
            <h2>${t("sales_rhythm")}</h2>
            <p>${t("revenue_chart")}</p>
          </div>
        </div>
        ${revenueChart(state.daily)}
      </section>

      <section class="panel green">
        <h2>${t("purchase_title")}</h2>
        <dl class="number-list">
          <div><dt>${t("purchases")}</dt><dd>${money(totals.purchases)}</dd></div>
          <div><dt>${t("cogs")}</dt><dd>${money(totals.cogs)}</dd></div>
          <div><dt>${t("net_units")}</dt><dd>${number(totals.sold)}</dd></div>
          <div><dt>${t("losses")}</dt><dd>${money(totals.losses)}</dd></div>
        </dl>
      </section>
    </div>

    <div class="two-columns">
      ${ranking(
        "top_sellers",
        "sold",
        (value) => `${number(value)} ${t("units")}`,
        "rank_qty",
      )}
      ${ranking(
        "top_profit",
        "profit",
        money,
        "rank_profit",
        false,
        (product) => product.revenue !== 0 || product.cogs !== 0,
      )}
    </div>
    <div class="section-head">
      <a class="quiet" href="#rankings">${t("see_rankings")}</a>
    </div>

    <section class="panel">
      <div class="section-head">
        <div>
          <h2>${t("alerts")}</h2>
          <p>${t("below_min")}</p>
        </div>
        <a href="#products" class="quiet">${t("view_products")}</a>
      </div>
      ${lowStockTable(lowStock)}
    </section>

    <div class="callout">
      <h3>${t("profit")}</h3>
      <p>${t("gross_note")}. ${excludedExpenses}</p>
    </div>
  `;
}

function productStatus(product) {
  if (!product.active) return "archived";
  if (product.quantity <= product.minimum) return "replenish";
  return "regular";
}

function productRow(product) {
  const status = productStatus(product);
  const tagClass = status === "archived" ? "muted" : status === "replenish" ? "warn" : "";
  const supplier = product.supplier
    ? ` / ${escapeHtml(product.supplier)}`
    : "";

  return `
    <tr>
      <td>
        <strong>${escapeHtml(product.name)}</strong>
        <small>${escapeHtml(product.sku)}${supplier}</small>
      </td>
      <td>${escapeHtml(product.category) || "—"}</td>
      <td class="num">
        ${product.quantity}
        <small>${t("minimum")} ${product.minimum}</small>
      </td>
      <td class="num">${money(product.average_cents)}</td>
      <td class="num">${money(product.price_cents)}</td>
      <td class="num">${money(product.value_cents)}</td>
      <td><span class="tag ${tagClass}">${t(status)}</span></td>
      <td>
        <button class="text-link" data-edit="${product.id}">${t("edit")}</button>
      </td>
    </tr>
  `;
}

export function productsPage() {
  const categories = [
    ...new Set(state.products.map((product) => product.category).filter(Boolean)),
  ].sort();
  const categoryOptions = categories
    .map((category) => `<option>${escapeHtml(category)}</option>`)
    .join("");

  return `
    <div class="table-tools">
      <input
        id="product-search"
        placeholder="${t("search")}"
        aria-label="${t("search")}"
      >
      <select id="category-filter" aria-label="${t("category")}">
        <option value="">${t("all_categories")}</option>
        ${categoryOptions}
      </select>
      <label class="pill-check">
        <input type="checkbox" id="low-filter">${t("only_low")}
      </label>
      <label class="pill-check">
        <input type="checkbox" id="archive-filter">${t("show_archived")}
      </label>
      <a class="quiet" href="/api/export/products?${query()}">${t("csv")}</a>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>${t("product")}</th>
            <th>${t("category")}</th>
            <th class="num">${t("stock")}</th>
            <th class="num">${t("avg_cost")}</th>
            <th class="num">${t("sale_price")}</th>
            <th class="num">${t("inventory")}</th>
            <th>${t("status")}</th>
            <th>${t("actions")}</th>
          </tr>
        </thead>
        <tbody id="product-rows"></tbody>
      </table>
    </div>
    <p class="definition">${t("current_note")}. ${t("export_note")}</p>
  `;
}

export function filterProducts() {
  const term = $("#product-search").value.toLocaleLowerCase();
  const category = $("#category-filter").value;
  const onlyLowStock = $("#low-filter").checked;
  const showArchived = $("#archive-filter").checked;

  const products = state.products.filter((product) => {
    const searchable = `${product.name} ${product.sku} ${product.supplier}`;
    const matchesSearch =
      !term || searchable.toLocaleLowerCase().includes(term);
    const matchesCategory = !category || product.category === category;
    const matchesLowStock =
      !onlyLowStock ||
      (product.active && product.quantity <= product.minimum);
    const matchesArchive = showArchived || product.active;

    return (
      matchesSearch &&
      matchesCategory &&
      matchesLowStock &&
      matchesArchive
    );
  });

  $("#product-rows").innerHTML = products.length
    ? products.map(productRow).join("")
    : `<tr><td colspan="8">${t("no_data")}</td></tr>`;
}

function movementRow(movement) {
  const originalSale = movement.original_id
    ? `<small>↳ #${movement.original_id}</small>`
    : "";
  const revenue =
    movement.kind === "sale" || movement.kind === "return"
      ? money(movement.revenue_delta)
      : "—";
  const returnAction =
    movement.kind === "sale" && movement.returnable > 0
      ? `
        <button class="text-link" data-return="${movement.id}">
          ${t("returned")}
        </button>
        <small>${movement.returnable} ${t("refund_left")}</small>
      `
      : "";

  return `
    <tr>
      <td>
        <strong>#${movement.id}</strong>
        <small>${formattedDate(movement.occurred_on)}</small>
      </td>
      <td>
        ${escapeHtml(movement.name)}
        <small>${escapeHtml(movement.sku)}</small>
      </td>
      <td>
        <span class="tag ${movement.kind === "loss" ? "warn" : ""}">
          ${t(movement.kind)}
        </span>
        ${originalSale}
      </td>
      <td class="num">
        ${movement.stock_delta > 0 ? "+" : ""}${movement.stock_delta}
      </td>
      <td class="num">${money(movement.cost_delta)}</td>
      <td class="num ${movement.revenue_delta < 0 ? "negative" : ""}">
        ${revenue}
      </td>
      <td>${escapeHtml(movement.note)}</td>
      <td>${returnAction}</td>
    </tr>
  `;
}

export function movementsPage() {
  const kindOptions = ["purchase", "sale", "return", "loss", "gain"]
    .map((kind) => `<option value="${kind}">${t(kind)}</option>`)
    .join("");

  return `
    <div class="table-tools">
      <input
        id="movement-search"
        placeholder="${t("search")}"
        aria-label="${t("search")}"
      >
      <select id="kind-filter" aria-label="${t("type")}">
        <option value="">${t("all_types")}</option>
        ${kindOptions}
      </select>
      <a class="quiet" href="/api/export/movements?${query()}">${t("csv")}</a>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th># / ${t("date")}</th>
            <th>${t("product")}</th>
            <th>${t("type")}</th>
            <th class="num">${t("quantity")}</th>
            <th class="num">${t("cost")}</th>
            <th class="num">${t("revenue_short")}</th>
            <th>${t("note")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="movement-rows"></tbody>
      </table>
    </div>
    <p class="definition">${t("ledger_note")}</p>
  `;
}

export function filterMovements() {
  const term = $("#movement-search").value.toLocaleLowerCase();
  const kind = $("#kind-filter").value;
  const movements = state.movements.filter((movement) => {
    const searchable = `${movement.name} ${movement.sku} ${movement.note}`;
    const matchesKind = !kind || movement.kind === kind;
    const matchesSearch =
      !term || searchable.toLocaleLowerCase().includes(term);
    return matchesKind && matchesSearch;
  });

  $("#movement-rows").innerHTML = movements.length
    ? movements.map(movementRow).join("")
    : `<tr><td colspan="8">${t("no_data")}</td></tr>`;
}

function productResultRow(product) {
  const profitClass = product.profit < 0 ? "negative" : "positive";

  return `
    <tr>
      <td>${escapeHtml(product.name)}<small>${escapeHtml(product.sku)}</small></td>
      <td class="num">${number(product.sold)}</td>
      <td class="num">${money(product.revenue)}</td>
      <td class="num">${money(product.cogs)}</td>
      <td class="num ${profitClass}">${money(product.profit)}</td>
      <td class="num">${percent(product.margin)}</td>
      <td class="num">${money(product.purchases)}</td>
    </tr>
  `;
}

export function rankingsPage() {
  const units = (value) => `${number(value)} ${t("units")}`;
  const cards = [
    ranking("top_sellers", "sold", units, "rank_qty"),
    ranking(
      "slow_sellers",
      "sold",
      units,
      "rank_qty",
      true,
      (product) => Boolean(product.active),
    ),
    ranking(
      "top_profit",
      "profit",
      money,
      "rank_profit",
      false,
      (product) => product.revenue !== 0 || product.cogs !== 0,
    ),
    ranking(
      "top_margin",
      "margin",
      percent,
      "rank_margin",
      false,
      (product) => product.revenue > 0,
    ),
    ranking(
      "high_cost",
      "average_cents",
      money,
      "rank_cost",
      false,
      (product) => product.quantity > 0,
    ),
    ranking(
      "top_spend",
      "purchases",
      money,
      "rank_spend",
      false,
      (product) => product.purchases > 0,
    ),
    ranking(
      "locked_capital",
      "value_cents",
      money,
      "rank_capital",
      false,
      (product) => product.quantity > 0,
    ),
  ].join("");
  const productRows = sortedProducts("profit").map(productResultRow).join("");
  const resultTitle =
    language === "pt" ? "Resultado por produto" : "Results by product";

  return `
    <div class="table-tools">
      <p class="definition">
        ${formattedDate(state.start)} → ${formattedDate(state.end)}
      </p>
      <button class="quiet" data-action="print">${t("print")} ↗</button>
      <a class="quiet" href="/api/export/products?${query()}">${t("csv")}</a>
    </div>

    <div class="rankings-grid">${cards}</div>

    <section class="panel report-detail">
      <div class="section-head">
        <div>
          <h2>${resultTitle}</h2>
          <p>${t("gross_note")}. ${t("net_returns")}.</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>${t("product")}</th>
              <th class="num">${t("net_units")}</th>
              <th class="num">${t("revenue_short")}</th>
              <th class="num">${t("cogs")}</th>
              <th class="num">${t("profit")}</th>
              <th class="num">${t("margin")}</th>
              <th class="num">${t("purchases")}</th>
            </tr>
          </thead>
          <tbody>${productRows}</tbody>
        </table>
      </div>
    </section>
  `;
}

export function guide() {
  const articles = guideArticles[language]
    .map(
      ([title, body], index) => `
        <article>
          <p class="eyebrow">${String(index + 1).padStart(2, "0")}</p>
          <h2>${title}</h2>
          <p>${body}</p>
        </article>
      `,
    )
    .join("");

  return `<div class="guide">${articles}</div>`;
}

