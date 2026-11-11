export function escapeHtml(value) {
  const entities = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };

  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) => entities[character],
  );
}

export function createFormatters(language) {
  const locale = language === "pt" ? "pt-BR" : "en-GB";
  const numberFormatter = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  });
  const moneyFormatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "BRL",
  });
  const dateFormatter = new Intl.DateTimeFormat(locale);

  return {
    money(cents) {
      return cents == null ? "—" : moneyFormatter.format(cents / 100);
    },
    number(value) {
      return numberFormatter.format(value);
    },
    percent(value) {
      return value == null ? "—" : `${numberFormatter.format(value)}%`;
    },
    date(value) {
      return dateFormatter.format(new Date(`${value}T12:00:00`));
    },
  };
}
