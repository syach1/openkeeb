(function () {
  var TOKEN_REPLACEMENTS = [
    [/#3e3e3e/gi, "var(--color-key-background-default)"],
    [/rgb\(\s*62\s*,\s*62\s*,\s*62\s*\)/gi, "var(--color-key-background-default)"],

    [/#74ebd5/gi, "var(--color-highlight-2)"],
    [/rgb\(\s*116\s*,\s*235\s*,\s*213\s*\)/gi, "var(--color-highlight-2)"],

    [/#71a4f1/gi, "var(--color-highlight-3)"],
    [/rgb\(\s*113\s*,\s*164\s*,\s*241\s*\)/gi, "var(--color-highlight-3)"],

    [/#58baa8/gi, "var(--color-key-background-changed)"],
    [/rgb\(\s*88\s*,\s*186\s*,\s*168\s*\)/gi, "var(--color-key-background-changed)"],

    [/#989898/gi, "var(--color-cell-border-default)"],
    [/rgb\(\s*152\s*,\s*152\s*,\s*152\s*\)/gi, "var(--color-cell-border-default)"],

    [/#d5d5d5/gi, "var(--color-text-disabled)"],
    [/rgb\(\s*213\s*,\s*213\s*,\s*213\s*\)/gi, "var(--color-text-disabled)"],

    [/#f9f9f9/gi, "var(--color-background-white)"],
    [/rgb\(\s*249\s*,\s*249\s*,\s*249\s*\)/gi, "var(--color-background-white)"],

    [/#e5e5e5/gi, "var(--border-color)"],
    [/rgb\(\s*229\s*,\s*229\s*,\s*229\s*\)/gi, "var(--border-color)"],

    [/#e0e0e0/gi, "var(--border-color)"],
    [/rgb\(\s*224\s*,\s*224\s*,\s*224\s*\)/gi, "var(--border-color)"],

    [/#606060/gi, "var(--color-background-dark)"],
    [/rgb\(\s*96\s*,\s*96\s*,\s*96\s*\)/gi, "var(--color-background-dark)"],

    [/#d8d8d8/gi, "var(--color-background-default)"],
    [/rgb\(\s*216\s*,\s*216\s*,\s*216\s*\)/gi, "var(--color-background-default)"],

    [/#fe4545/gi, "var(--color-key-system)"],
    [/rgb\(\s*254\s*,\s*69\s*,\s*69\s*\)/gi, "var(--color-key-system)"],

    [/#faff00/gi, "var(--color-key-background-forbidden)"],
    [/rgb\(\s*250\s*,\s*255\s*,\s*0\s*\)/gi, "var(--color-key-background-forbidden)"],
  ];

  var isMutating = false;
  var seenStyle = new WeakMap();

  function remapInlineStyle(styleText) {
    var mapped = styleText;
    for (var i = 0; i < TOKEN_REPLACEMENTS.length; i += 1) {
      var pair = TOKEN_REPLACEMENTS[i];
      mapped = mapped.replace(pair[0], pair[1]);
    }
    return mapped;
  }

  function patchElementStyle(el) {
    var styleText = el.getAttribute("style");
    if (!styleText) {
      return;
    }

    var previous = seenStyle.get(el);
    if (previous === styleText) {
      return;
    }

    var mapped = remapInlineStyle(styleText);
    seenStyle.set(el, styleText);
    if (mapped === styleText) {
      return;
    }

    isMutating = true;
    el.setAttribute("style", mapped);
    isMutating = false;
    seenStyle.set(el, mapped);
  }

  function patchNodeTree(node) {
    if (!(node instanceof Element)) {
      return;
    }

    patchElementStyle(node);
    var descendants = node.querySelectorAll("[style]");
    for (var i = 0; i < descendants.length; i += 1) {
      patchElementStyle(descendants[i]);
    }
  }

  function patchDocumentStyles() {
    patchNodeTree(document.documentElement);
  }

  function scheduleInitialPasses() {
    patchDocumentStyles();
    setTimeout(patchDocumentStyles, 300);
    setTimeout(patchDocumentStyles, 1200);
    setTimeout(patchDocumentStyles, 2500);
  }

  function startObserver() {
    var observer = new MutationObserver(function (mutations) {
      if (isMutating) {
        return;
      }

      for (var i = 0; i < mutations.length; i += 1) {
        var mutation = mutations[i];
        if (mutation.type === "attributes") {
          if (mutation.target instanceof Element) {
            patchElementStyle(mutation.target);
          }
          continue;
        }

        for (var j = 0; j < mutation.addedNodes.length; j += 1) {
          patchNodeTree(mutation.addedNodes[j]);
        }
      }
    });

    observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["style"],
    });
  }

  function init() {
    scheduleInitialPasses();
    startObserver();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
