(function () {
  "use strict";
  const IDEAS = window.IDEAS || [];
  const LS_KEY = "lehe_ideas_v1";
  let CASES = window.CASES || [];

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
  function fillTypeOptions() {
    typeSel.innerHTML = '<option value="">全部类型</option>';
    [...new Set(CASES.map((c) => c.campaignType).filter(Boolean))]
      .sort()
      .forEach((t) => {
        const o = document.createElement("option");
        o.value = t;
        o.textContent = t;
        typeSel.appendChild(o);
      });
  }

  const grid = document.getElementById("case-grid");
  const emptyP = document.getElementById("case-empty");
  const searchEl = document.getElementById("search");
  const sortSel = document.getElementById("filter-sort");

  const gradients = [
    "linear-gradient(135deg,#FF2442,#FF8A3D)",
    "linear-gradient(135deg,#36C5F0,#2BD9A8)",
    "linear-gradient(135deg,#FFE03D,#FF2442)",
    "linear-gradient(135deg,#B66DFF,#36C5F0)",
    "linear-gradient(135deg,#2BD9A8,#FFE03D)",
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
      const hasImg = c.images && c.images[0];
      const img = hasImg
        ? `<div class="card-media-wrap"><img class="card-img" src="${c.images[0]}" alt="${c.title || ""}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="card-media img-fallback" style="display:none"><span class="ph">🖼️</span></div></div>`
        : `<div class="card-media" style="background:${mediaStyle(i)}"><span class="ph">🖼️</span></div>`;
      const link = c.url
        ? `<a class="card-link" href="${c.url}" target="_blank" rel="noopener">看原文 ↗</a>`
        : "";
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
          <div class="card-foot">
            <span class="card-date">${c.date || ""}</span>
            ${link}
          </div>
        </div>`;
      grid.appendChild(el);
    });
  }
  searchEl.addEventListener("input", renderCases);
  typeSel.addEventListener("change", renderCases);
  sortSel.addEventListener("change", renderCases);

  /* ---------- 案例数据：优先读云端，回退内置 ---------- */
  async function loadCases() {
    try {
      const r = await fetch(
        "https://cdn.jsdelivr.net/gh/momo-smartedition/ad-case-library@main/data/cases.json",
        { cache: "no-store" }
      );
      if (r.ok) {
        const j = await r.json();
        if (Array.isArray(j) && j.length) CASES = j;
      }
    } catch (e) {
      /* 离线 / 双击本地打开时，使用内置兜底数据 */
    }
    fillTypeOptions();
    renderCases();
  }

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
  const catColors = { 文案: "#FF2442", 洞察: "#36C5F0", 胡思乱想: "#B66DFF" };

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
      el.style.borderLeftColor = catColors[x.category] || "#FF2442";
      const tags = (x.tags || [])
        .map((t) => `<span class="idea-tag">#${t}</span>`)
        .join("");
      el.innerHTML = `
        <span class="idea-cat" style="background:${catColors[x.category] || "#FF2442"}">${x.category}</span>
        <div class="idea-content">${escapeHtml(x.content)}</div>
        ${tags ? `<div class="idea-tags">${tags}</div>` : ""}
        <div class="idea-date">${x.createdAt || ""}${x.local ? " · 本地新增" : ""}</div>`;
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
  loadCases();
  renderIdeas();
})();
