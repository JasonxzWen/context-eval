/* Use case: bridge pinned Marked, DOMPurify, Mermaid, and highlight.js runtimes for self-contained work reports. The generator inlines this only for runtime mode. */
(function () {
  var pins = {
    marked: "18.0.3",
    dompurify: "3.4.2",
    mermaid: "11.15.0",
    highlightjs: "11.11.1"
  };

  function setStatus(id, state, text) {
    var node = document.querySelector("[data-rich-status='" + id + "']");
    if (!node) return;
    node.dataset.state = state;
    node.textContent = text;
  }

  function renderMarkdown() {
    var parser = window.marked;
    var purifier = window.DOMPurify;
    var count = 0;

    document.querySelectorAll("[data-rich-markdown]").forEach(function (node, index) {
      var statusId = node.getAttribute("data-rich-status-id") || "markdown";
      var trusted = node.getAttribute("data-trusted") === "true";
      var source = node.textContent.trim();

      if (node.dataset.rendered === "true") {
        count += 1;
        return;
      }

      if (!parser || typeof parser.parse !== "function") {
        setStatus(statusId, "fallback", "Markdown 运行时缺失，显示源内容");
        return;
      }

      if (!purifier && !trusted) {
        setStatus(statusId, "error", "Markdown 未渲染：缺少 sanitizer");
        return;
      }

      var html = parser.parse(source);
      node.innerHTML = purifier ? purifier.sanitize(html) : html;
      node.classList.add("rendered-markdown");
      node.dataset.rendered = "true";
      setStatus(statusId, "ready", "Markdown 已渲染");
      count += 1;
    });

    return count;
  }

  async function renderMermaid() {
    if (!window.mermaid) {
      setStatus("mermaid", "fallback", "Mermaid 运行时缺失，显示源内容");
      return 0;
    }

    document.querySelectorAll("[data-rich-mermaid]").forEach(function (node) {
      node.classList.add("mermaid");
    });

    try {
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "base"
      });
      await window.mermaid.run({
        querySelector: "[data-rich-mermaid]",
        suppressErrors: false
      });
      setStatus("mermaid", "ready", "Mermaid 已渲染");
      return document.querySelectorAll("[data-rich-mermaid] svg").length;
    } catch (error) {
      setStatus("mermaid", "error", "Mermaid 渲染失败");
      return 0;
    }
  }

  function highlightCode() {
    if (!window.hljs || typeof window.hljs.highlightElement !== "function") {
      setStatus("code", "fallback", "高亮器缺失，显示纯代码");
      return 0;
    }

    var count = 0;
    document.querySelectorAll("pre code[class*='language-']").forEach(function (node) {
      if (node.dataset.highlighted === "true") {
        count += 1;
        return;
      }
      window.hljs.highlightElement(node);
      node.dataset.highlighted = "true";
      count += 1;
    });
    setStatus("code", "ready", "代码已高亮");
    return count;
  }

  async function renderAll() {
    renderMarkdown();
    await renderMermaid();
    highlightCode();
  }

  window.HTMLWorkReportsRichRender = {
    pins: pins,
    renderAll: renderAll,
    renderMarkdown: renderMarkdown,
    renderMermaid: renderMermaid,
    highlightCode: highlightCode
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAll);
  } else {
    renderAll();
  }

  window.addEventListener("rich-render-libs-ready", renderAll);
})();
