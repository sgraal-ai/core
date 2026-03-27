/**
 * sgraal.auto.js v1 — Zero-config browser embed for Sgraal preflight API.
 * <script src="https://sgraal.com/sgraal.auto.js" data-api-key="sg_live_..."></script>
 */
(function () {
  "use strict";
  var config = { apiKey: null, baseUrl: "https://api.sgraal.com", domain: "general", actionType: "reversible" };

  function validateKey(key) {
    if (!key) return false;
    if (key.indexOf("sg_live_") === 0 || key === "sg_demo_playground") return true;
    console.error("[sgraal] Invalid API key format — must start with sg_live_ or be sg_demo_playground");
    return false;
  }

  function preflight(memoryState, options) {
    var opts = options || {};
    var key = opts.apiKey || config.apiKey;
    if (!validateKey(key)) return Promise.reject(new Error("Invalid Sgraal API key"));
    return fetch(config.baseUrl + "/v1/preflight", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
      body: JSON.stringify({
        memory_state: memoryState,
        domain: opts.domain || config.domain,
        action_type: opts.actionType || config.actionType,
      }),
    }).then(function (r) { return r.json(); });
  }

  function guard(fn, memoryState, options) {
    return preflight(memoryState, options).then(function (result) {
      if (result.recommended_action === "BLOCK") throw new Error("Sgraal BLOCK: omega=" + result.omega_mem_final);
      return fn(result);
    });
  }

  function configure(opts) {
    if (opts.apiKey) config.apiKey = opts.apiKey;
    if (opts.domain) config.domain = opts.domain;
    if (opts.actionType) config.actionType = opts.actionType;
    if (opts.baseUrl) config.baseUrl = opts.baseUrl;
  }

  // Auto-init from script tag
  var scripts = document.querySelectorAll("script[data-api-key]");
  for (var i = 0; i < scripts.length; i++) {
    var src = scripts[i].getAttribute("src") || "";
    if (src.indexOf("sgraal") !== -1) {
      config.apiKey = scripts[i].getAttribute("data-api-key");
      break;
    }
  }

  window.sgraal = { preflight: preflight, guard: guard, configure: configure, version: "1.0.0" };
})();
