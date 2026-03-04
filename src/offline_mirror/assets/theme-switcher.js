(function () {
  var THEME_KEY = "offline_ui_theme";
  var DEFAULT_THEME = "classic";
  var THEMES = [{ value: "classic", label: "Classic" }];

  function isValidTheme(theme) {
    return THEMES.some(function (entry) {
      return entry.value === theme;
    });
  }

  function getStoredTheme() {
    var value = "";
    try {
      value = window.localStorage.getItem(THEME_KEY) || "";
    } catch (_error) {
      value = "";
    }
    return value;
  }

  function setStoredTheme(value) {
    try {
      window.localStorage.setItem(THEME_KEY, value);
    } catch (_error) {
      // Ignore storage failures in restricted contexts.
    }
  }

  function applyTheme(theme) {
    var resolved = isValidTheme(theme) ? theme : DEFAULT_THEME;
    document.documentElement.setAttribute("data-ui-theme", resolved);
    setStoredTheme(resolved);
    return resolved;
  }

  function createSwitcher(initialTheme) {
    var existing = document.getElementById("ui-theme-switcher");
    if (THEMES.length < 2) {
      if (existing && existing.parentNode) {
        existing.parentNode.removeChild(existing);
      }
      return;
    }

    if (existing) {
      return;
    }

    var wrapper = document.createElement("div");
    wrapper.id = "ui-theme-switcher";
    wrapper.className = "ui-theme-switcher";

    var label = document.createElement("label");
    label.className = "ui-theme-switcher__label";
    label.setAttribute("for", "ui-theme-switcher-select");
    label.textContent = "Theme";

    var select = document.createElement("select");
    select.id = "ui-theme-switcher-select";
    select.className = "ui-theme-switcher__select";

    THEMES.forEach(function (theme) {
      var option = document.createElement("option");
      option.value = theme.value;
      option.textContent = theme.label;
      select.appendChild(option);
    });

    select.value = initialTheme;
    select.addEventListener("change", function () {
      applyTheme(select.value);
    });

    wrapper.appendChild(label);
    wrapper.appendChild(select);
    document.body.appendChild(wrapper);
  }

  function init() {
    var theme = getStoredTheme();
    if (theme === "matte-dark") {
      theme = DEFAULT_THEME;
      setStoredTheme(theme);
    }

    var resolved = applyTheme(theme);
    createSwitcher(resolved);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
