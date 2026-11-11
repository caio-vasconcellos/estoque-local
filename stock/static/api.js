export function createApiClient(getCsrfToken) {
  return async function api(path, method = "GET", payload) {
    const options = { method };

    if (payload !== undefined) {
      options.headers = {
        "Content-Type": "application/json",
        "X-CSRF-Token": getCsrfToken(),
      };
      options.body = JSON.stringify(payload);
    }

    let response;
    try {
      response = await fetch(path, options);
    } catch {
      throw new Error("connection");
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "unexpected");
    }

    return response.json();
  };
}
