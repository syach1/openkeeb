(function () {
  var THEME_KEY = "offline_ui_theme";
  var DEFAULT_THEME = "classic";
  var VALID_THEMES = {
    classic: true,
  };

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

  var theme = getStoredTheme();
  if (theme === "matte-dark") {
    theme = DEFAULT_THEME;
    setStoredTheme(theme);
  }

  if (!VALID_THEMES[theme]) {
    theme = DEFAULT_THEME;
    setStoredTheme(theme);
  }

  document.documentElement.setAttribute("data-ui-theme", theme);
})();
