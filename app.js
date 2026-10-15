(function () {
  "use strict";
  const CASES = window.CASES || [];
  const IDEAS = window.IDEAS || [];
  const LS_KEY = "lehe_ideas_v1";

  /* ---------- 视图切换 ---------- */
  const tabs = document.querySelectorAll(".tab");
  const views = {
    paper: document.getElementById("view-paper"),
    idea: document.getElementById("view-idea"),
  };
  tabs.forEach((t) =>
    t.addEventListener("click", () => {
      tabs.forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      Object.values(views).forEach((v) => v.classList.remove("active"));
      views[t.dataset.view].classList.add("active");
    })
  );

  /* ---------- 小报：动态类型下拉 ---------- */
  const typeSel = document.getElementById("filter-type");
  [...new Set(CASES.map((c) => c.campaignType).filter(Boolean))]
    .sort()
    .forEach((t) => {
      const o = document.createElement("option");
      o.value = t;
      o.textContent = t;
      typeSel.appendChild(o);
    });

  const grid = document.getElementById("case-grid");
  const emptyP = document.getElementById("case-empty");
  const searchEl = document.getElementById("search");
  const sortSel = document.getElementById("filter-sort");

  const gradients = [
    "linear-gradient(135deg,#FF6B5B,#FFD23F)",
    "linear-gradient(135deg,#4D8AF0,#3EC6A0)",
    "linear-gradient(135deg,#C8102E,#FF6B5B)",
    "linear-gradient(135deg,#8a6df0,#4D8AF0)",
    "linear-gradient(135deg,#3EC6A0,#FFD23F)",
  ];
  const mediaStyle = (i) => gradients[i % gradients.length];

  function renderCases() {
    const kw = searchEl.value.trim().toLowerCase();
    const type = typeSel.value;
    const sort = sortSel.value;
    let list = CASES.filter((c) => {
      const hay = [c.advertiser, c.agency, c.title, c.summary, c.campaignType]
        .join(" ")
        .toLowerCase();
      const hitKw = !kw || hay.includes(kw);
      const hitType = !type || c.campaignType === type;
      return hitKw && hitType;
    });
    list.sort((a, b) =>
      sort === "date-asc"
        ? a.date.localeCompare(b.date)
        : b.date.localeCompare(a.date)
    );

    grid.innerHTML = "";
    emptyP.classList.toggle("hidden", list.length > 0);
    list.forEach((c, i) => {
      const el = document.createElement("article");
      el.className = "card";
      const img =
        c.images && c.images[0]
          ? `<img src="${c.images[0]}" alt="" style="width:100%;height:160px;object-fit:cover">`
          : `<div class="card-media" style="background:${mediaStyle(i)}"><span class="ph">🖼️</span></div>`;
      el.innerHTML = `
        ${img}
        <div class="card-body">
          <div class="card-meta">
            <span class="badge src">${c.source || "来源"}</span>
            <span class="badge type">${c.campaignType || "类型"}</span>
          </div>
          <div class="card-title">${c.title || "(无标题)"}</div>
          <div class="card-line"><b>广告主</b> ${c.advertiser || "—"}</div>
          <div class="card-line"><b>代理商</b> ${c.agency || "—"}</div>
          <div class="card-sum">${c.summary || ""}</div>
          <div class="card-date">${c.date || ""}</div>
        </div>`;
      grid.appendChild(el);
    });
  }
  searchEl.addEventListener("input", renderCases);
  typeSel.addEventListener("change", renderCases);
  sortSel.addEventListener("change", renderCases);

  /* ---------- idea ---------- */
  function loadIdeas() {
    try {
      return JSON.parse(localStorage.getItem(LS_KEY)) || [];
    } catch (e) {
      return [];
    }
  }
  function saveIdeas(arr) {
    localStorage.setItem(LS_KEY, JSON.stringify(arr));
  }

  const ideaGrid = document.getElementById("idea-grid");
  const ideaEmpty = document.getElementById("idea-empty");
  const ideaCats = document.getElementById("idea-cats");
  const catColors = { 文案: "#FF6B5B", 洞察: "#4D8AF0", 胡思乱想: "#8a6df0" };

  function escapeHtml(s) {
    return (s || "").replace(
      /[&<>"]/g,
      (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m])
    );
  }

  function renderIdeas() {
    const cat = ideaCats.querySelector(".chip.active").dataset.cat;
    const local = loadIdeas();
    const all = [...IDEAS, ...local].sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt)
    );
    const list = cat === "all" ? all : all.filter((x) => x.category === cat);
    ideaGrid.innerHTML = "";
    ideaEmpty.classList.toggle("hidden", list.length > 0);
    list.forEach((x) => {
      const el = document.createElement("article");
      el.className = "idea-card";
      el.style.borderLeftColor = catColors[x.category] || "#FF6B5B";
      const tags = (x.tags || [])
        .map((t) => `<span class="idea-tag">#${t}</span>`)
        .join("");
      el.innerHTML = `
        <span class="idea-cat" style="background:${
          catColors[x.category] || "#FF6B5B"
        }">${x.category}</span>
        <div class="idea-content">${escapeHtml(x.content)}</div>
        ${tags ? `<div class="idea-tags">${tags}</div>` : ""}
        <div class="idea-date">${x.createdAt || ""}${
          x.local ? " · 本地新增" : ""
        }</div>`;
      ideaGrid.appendChild(el);
    });
  }

  ideaCats.querySelectorAll(".chip").forEach((ch) =>
    ch.addEventListener("click", () => {
      ideaCats
        .querySelectorAll(".chip")
        .forEach((x) => x.classList.remove("active"));
      ch.classList.add("active");
      renderIdeas();
    })
  );

  /* ---------- 新建弹窗 ---------- */
  const modal = document.getElementById("modal");
  const openBtn = document.getElementById("new-idea");
  const cancelBtn = document.getElementById("idea-cancel");
  const saveBtn = document.getElementById("idea-save");
  openBtn.addEventListener("click", () => modal.classList.remove("hidden"));
  cancelBtn.addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
  saveBtn.addEventListener("click", () => {
    const category = document.getElementById("idea-cat").value;
    const content = document.getElementById("idea-content").value.trim();
    const tags = document.getElementById("idea-tags")
      .value.split(/[,，]/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!content) {
      alert("内容不能为空哦");
      return;
    }
    const local = loadIdeas();
    local.push({
      id: "local_" + Date.now(),
      category,
      content,
      tags,
      createdAt: new Date().toISOString().slice(0, 10),
      local: true,
    });
    saveIdeas(local);
    document.getElementById("idea-content").value = "";
    document.getElementById("idea-tags").value = "";
    modal.classList.add("hidden");
    renderIdeas();
  });

  /* ---------- 初始渲染 ---------- */
  renderCases();
  renderIdeas();
})();
