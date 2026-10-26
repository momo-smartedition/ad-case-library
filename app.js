(function () {
  "use strict";
  const IDEAS = window.IDEAS || [];
  let CLOUD_IDEAS = [];
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

  /* ---------- 小报：组合框（下拉 + 搜索结合） ---------- */
  const grid = document.getElementById("case-grid");
  const emptyP = document.getElementById("case-empty");
  const sortSel = document.getElementById("filter-sort");

  // 通用组合框：点开是下拉列表，输入框也能打字模糊搜；选「全部」清空
  function makeCombobox(rootId, optsProvider, onChange) {
    const root = document.getElementById(rootId);
    const input = root.querySelector(".cb-input");
    const toggle = root.querySelector(".cb-toggle");
    const panel = root.querySelector(".cb-panel");

    function render(open) {
      const val = input.value.trim().toLowerCase();
      const opts = optsProvider();
      const list = ["__all__"].concat(
        opts.filter((o) => !val || o.toLowerCase().includes(val))
      );
      panel.innerHTML = "";
      list.forEach((o) => {
        const isAll = o === "__all__";
        const d = document.createElement("div");
        d.className = "cb-option" + (isAll ? " cb-all" : "");
        d.textContent = isAll ? "全部" : o;
        d.addEventListener("mousedown", (e) => {
          e.preventDefault();
          input.value = isAll ? "" : o;
          panel.classList.add("hidden");
          onChange();
        });
        panel.appendChild(d);
      });
      panel.classList.toggle("hidden", !open);
    }

    input.addEventListener("focus", () => render(true));
    input.addEventListener("click", () => render(true));
    input.addEventListener("input", () => {
      render(true);
      onChange();
    });
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      if (panel.classList.contains("hidden")) render(true);
      else panel.classList.add("hidden");
    });
    document.addEventListener("click", (e) => {
      if (!root.contains(e.target)) panel.classList.add("hidden");
    });

    return {
      refresh() {
        render(false);
      },
      getValue() {
        return input.value.trim();
      },
    };
  }

  const advertiserOpts = () =>
    [...new Set(CASES.map((c) => c.advertiser).filter(Boolean))].sort((a, b) =>
      a.localeCompare(b, "zh")
    );
  const agencyOpts = () =>
    [...new Set(CASES.map((c) => c.agency).filter(Boolean))].sort((a, b) =>
      a.localeCompare(b, "zh")
    );
  const typeOpts = () =>
    [...new Set(CASES.map((c) => c.campaignType).filter(Boolean))].sort((a, b) =>
      a.localeCompare(b, "zh")
    );

  const cbAdvertiser = makeCombobox("cb-advertiser", advertiserOpts, renderCases);
  const cbAgency = makeCombobox("cb-agency", agencyOpts, renderCases);
  const cbType = makeCombobox("cb-type", typeOpts, renderCases);

  function fillFilters() {
    cbAdvertiser.refresh();
    cbAgency.refresh();
    cbType.refresh();
  }

  const gradients = [
    "linear-gradient(135deg,#FF2442,#FF8A3D)",
    "linear-gradient(135deg,#36C5F0,#2BD9A8)",
    "linear-gradient(135deg,#FFE03D,#FF2442)",
    "linear-gradient(135deg,#B66DFF,#36C5F0)",
    "linear-gradient(135deg,#2BD9A8,#FFE03D)",
  ];
  const mediaStyle = (i) => gradients[i % gradients.length];

  function renderCases() {
    const kwAdv = cbAdvertiser.getValue().toLowerCase();
    const kwAgency = cbAgency.getValue().toLowerCase();
    const type = cbType.getValue();
    const sort = sortSel.value;
    let list = CASES.filter((c) => {
      const hitAdv =
        !kwAdv || (c.advertiser || "").toLowerCase().includes(kwAdv);
      const hitAgency =
        !kwAgency || (c.agency || "").toLowerCase().includes(kwAgency);
      const hitType = !type || (c.campaignType || "").toLowerCase().includes(type.toLowerCase());
      return hitAdv && hitAgency && hitType;
    });
    list.sort((a, b) => {
      // 优先按优质分降序（奖项/高分自然排最前），同分再按日期
      const sa = a.score || 0, sb = b.score || 0;
      if (sa !== sb) return sb - sa;
      return sort === "date-asc"
        ? a.date.localeCompare(b.date)
        : b.date.localeCompare(a.date);
    });

    grid.innerHTML = "";
    emptyP.classList.toggle("hidden", list.length > 0);
    list.forEach((c, i) => {
      const el = document.createElement("article");
      el.className = "card";
      const hasImg = c.images && c.images[0];
      const img = hasImg
        ? `<div class="card-media-wrap"><img class="card-img" src="${c.images[0]}" alt="${c.title || ""}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="card-media img-fallback" style="display:none"><span class="ph">🖼️</span></div></div>`
        : `<div class="card-media award-ph"><div class="ph-inner"><span class="ph-emoji">🏆</span><div class="ph-award">${c.award || "获奖案例"}</div><div class="ph-brand">${c.advertiser || ""}</div></div></div>`;
      const tierBadge = c.award_tier
        ? `<span class="badge tier tier-${c.award_tier}">${c.award_tier === "S" ? "杰出大奖" : c.award_tier === "A" ? "知名奖项" : "入围/提名"}</span>`
        : "";
      const scoreBadge = c.score
        ? `<span class="badge score">⭐ ${c.score}</span>`
        : "";
      const link = c.url
        ? `<a class="card-link" href="${c.url}" target="_blank" rel="noopener">看原文 ↗</a>`
        : "";
      el.innerHTML = `
        ${img}
        <div class="card-body">
          <div class="card-meta">
            ${tierBadge}
            ${scoreBadge}
            ${c.award ? `<span class="badge award">🏆 ${c.award}</span>` : ""}
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
  sortSel.addEventListener("change", renderCases);

  /* ---------- 云端数据：多 CDN 镜像依次尝试（国内友好），最后回退同站点副本 ---------- */
  const CDN_BASES = [
    "https://gcore.jsdelivr.net/gh/momo-smartedition/ad-case-library@main",
    "https://testingcf.jsdelivr.net/gh/momo-smartedition/ad-case-library@main",
    "https://cdn.jsdelivr.net/gh/momo-smartedition/ad-case-library@main",
  ];
  async function fetchCloud(relPath) {
    for (const base of CDN_BASES) {
      try {
        const r = await fetch(base + "/" + relPath, { cache: "no-store" });
        if (r.ok) {
          const j = await r.json();
          if (Array.isArray(j) && j.length) return j;
        }
      } catch (e) {
        /* 该镜像连不上，试下一个 */
      }
    }
    try {
      const r = await fetch(relPath, { cache: "no-store" }); // 同站点部署副本兜底
      if (r.ok) {
        const j = await r.json();
        if (Array.isArray(j) && j.length) return j;
      }
    } catch (e) {}
    return null;
  }

  /* ---------- 案例数据：优先读云端，回退内置 ---------- */
  async function loadCases() {
    const j = await fetchCloud("data/cases.json");
    if (j) CASES = j;
    fillFilters();
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
    const all = [...CLOUD_IDEAS, ...local].sort((a, b) =>
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
      const imgs =
        x.images && x.images.length
          ? `<div class="idea-imgs">${x.images
              .map(
                (s) =>
                  `<img src="${s}" alt="" referrerpolicy="no-referrer" onerror="this.style.display='none'">`
              )
              .join("")}</div>`
          : "";
      el.innerHTML = `
        <span class="idea-cat" style="background:${catColors[x.category] || "#FF2442"}">${x.category}</span>
        <div class="idea-content">${escapeHtml(x.content)}</div>
        ${imgs}
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

  /* ---------- idea 数据：优先读云端，回退内置 ---------- */
  async function loadIdeasCloud() {
    const j = await fetchCloud("data/ideas.json");
    if (j) CLOUD_IDEAS = j;
    renderIdeas();
  }

  /* ---------- 新建弹窗（支持配图） ---------- */
  const modal = document.getElementById("modal");
  const openBtn = document.getElementById("new-idea");
  const cancelBtn = document.getElementById("idea-cancel");
  const saveBtn = document.getElementById("idea-save");
  const imgInput = document.getElementById("idea-images");
  const imgPreview = document.getElementById("idea-preview");
  let pendingImages = []; // 待保存的图片（data URL）

  function renderPreview() {
    imgPreview.innerHTML = "";
    pendingImages.forEach((src, i) => {
      const wrap = document.createElement("div");
      wrap.className = "thumb";
      wrap.innerHTML = `<img src="${src}" alt=""><button type="button" class="thumb-x">×</button>`;
      wrap.querySelector(".thumb-x").addEventListener("click", () => {
        pendingImages.splice(i, 1);
        renderPreview();
      });
      imgPreview.appendChild(wrap);
    });
  }

  imgInput.addEventListener("change", () => {
    [...imgInput.files].forEach((f) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        pendingImages.push(e.target.result);
        renderPreview();
      };
      reader.readAsDataURL(f);
    });
    imgInput.value = "";
  });

  function resetModal() {
    pendingImages = [];
    imgPreview.innerHTML = "";
    imgInput.value = "";
    document.getElementById("idea-content").value = "";
    document.getElementById("idea-tags").value = "";
  }

  openBtn.addEventListener("click", () => {
    resetModal();
    modal.classList.remove("hidden");
  });
  cancelBtn.addEventListener("click", () => {
    resetModal();
    modal.classList.add("hidden");
  });
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      resetModal();
      modal.classList.add("hidden");
    }
  });
  saveBtn.addEventListener("click", () => {
    const category = document.getElementById("idea-cat").value;
    const content = document.getElementById("idea-content").value.trim();
    const tags = document
      .getElementById("idea-tags")
      .value.split(/[,，]/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!content && pendingImages.length === 0) {
      alert("内容或图片至少填一项哦");
      return;
    }
    const local = loadIdeas();
    local.push({
      id: "local_" + Date.now(),
      category,
      content,
      tags,
      images: pendingImages.slice(),
      createdAt: new Date().toISOString().slice(0, 10),
      local: true,
    });
    saveIdeas(local);
    resetModal();
    modal.classList.add("hidden");
    renderIdeas();
  });

  /* ---------- 初始渲染 ---------- */
  loadCases();
  loadIdeasCloud();
})();
