(function () {
  var ALLOWED_HOSTS = {
    "127.0.0.1": true,
    localhost: true,
  };

  function toUrl(value) {
    try {
      return new URL(String(value), window.location.href);
    } catch (_error) {
      return null;
    }
  }

  function isAllowedUrl(urlObj) {
    if (!urlObj) {
      return false;
    }

    var protocol = (urlObj.protocol || "").toLowerCase();
    if (protocol === "data:" || protocol === "blob:" || protocol === "about:") {
      return true;
    }

    if (protocol === "http:" || protocol === "https:" || protocol === "ws:" || protocol === "wss:") {
      var host = (urlObj.hostname || "").toLowerCase();
      return !!ALLOWED_HOSTS[host];
    }

    return false;
  }

  function blockAndWarn(kind, target) {
    try {
      console.warn("[offline-guard] blocked external " + kind + ":", target);
    } catch (_error) {
      // Ignore console failures.
    }
  }

  if (window.fetch) {
    var nativeFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      var target = typeof input === "string" ? input : input && input.url ? input.url : String(input);
      var parsed = toUrl(target);
      if (!isAllowedUrl(parsed)) {
        blockAndWarn("fetch", target);
        return Promise.reject(new Error("Blocked external fetch request in offline mode."));
      }
      return nativeFetch(input, init);
    };
  }

  if (window.XMLHttpRequest && window.XMLHttpRequest.prototype) {
    var xhrOpen = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function (method, url) {
      var parsed = toUrl(url);
      if (!isAllowedUrl(parsed)) {
        blockAndWarn("xhr", url);
        throw new Error("Blocked external XHR request in offline mode.");
      }
      return xhrOpen.apply(this, arguments);
    };
  }

  if (window.WebSocket) {
    var NativeWebSocket = window.WebSocket;
    var GuardedWebSocket = function (url, protocols) {
      var parsed = toUrl(url);
      if (!isAllowedUrl(parsed)) {
        blockAndWarn("websocket", url);
        throw new Error("Blocked external WebSocket in offline mode.");
      }
      if (protocols === undefined) {
        return new NativeWebSocket(url);
      }
      return new NativeWebSocket(url, protocols);
    };
    GuardedWebSocket.prototype = NativeWebSocket.prototype;
    GuardedWebSocket.CONNECTING = NativeWebSocket.CONNECTING;
    GuardedWebSocket.OPEN = NativeWebSocket.OPEN;
    GuardedWebSocket.CLOSING = NativeWebSocket.CLOSING;
    GuardedWebSocket.CLOSED = NativeWebSocket.CLOSED;
    window.WebSocket = GuardedWebSocket;
  }

  if (window.EventSource) {
    var NativeEventSource = window.EventSource;
    var GuardedEventSource = function (url, config) {
      var parsed = toUrl(url);
      if (!isAllowedUrl(parsed)) {
        blockAndWarn("eventsource", url);
        throw new Error("Blocked external EventSource in offline mode.");
      }
      if (config === undefined) {
        return new NativeEventSource(url);
      }
      return new NativeEventSource(url, config);
    };
    GuardedEventSource.prototype = NativeEventSource.prototype;
    window.EventSource = GuardedEventSource;
  }

  if (navigator.sendBeacon) {
    var nativeSendBeacon = navigator.sendBeacon.bind(navigator);
    navigator.sendBeacon = function (url, data) {
      var parsed = toUrl(url);
      if (!isAllowedUrl(parsed)) {
        blockAndWarn("beacon", url);
        return false;
      }
      return nativeSendBeacon(url, data);
    };
  }

  var nativeOpen = window.open;
  window.open = function (url) {
    if (url !== undefined && url !== null) {
      var parsed = toUrl(url);
      if (!isAllowedUrl(parsed)) {
        blockAndWarn("window.open", url);
        return null;
      }
    }
    return nativeOpen.apply(window, arguments);
  };

  document.addEventListener(
    "click",
    function (event) {
      var node = event.target;
      while (node && node !== document) {
        if (node.tagName === "A") {
          var href = node.getAttribute("href");
          if (!href) {
            return;
          }

          var parsed = toUrl(href);
          if (!isAllowedUrl(parsed)) {
            blockAndWarn("anchor", href);
            event.preventDefault();
            event.stopPropagation();
          }
          return;
        }
        node = node.parentNode;
      }
    },
    true
  );
})();
