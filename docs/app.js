const SPOTIFY_URL = id => `https://open.spotify.com/episode/${id}`;

const state = {
  store: { episodes: [], items: [] },
  filters: { q: "", episode: "", category: "", updates: "" },
  sort: "ep-desc",
};

const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "href" || k === "target" || k === "rel") node.setAttribute(k, v);
    else node[k] = v;
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
};

function episodeFor(n) {
  return state.store.episodes.find(e => e.number === n);
}

function episodeLink(item) {
  const ep = episodeFor(item.episode);
  if (!ep) return null;
  const label = `ep ${ep.number} · ${ep.date} · ${item.timestamp_display}`;
  if (ep.spotify_id) {
    return el("a", {
      class: "episode-link",
      href: SPOTIFY_URL(ep.spotify_id),
      target: "_blank",
      rel: "noopener",
    }, label);
  }
  return el("span", { class: "episode-link" }, label);
}

function hasUpdates(item) {
  return Array.isArray(item.updates) && item.updates.length > 0;
}

function matches(item) {
  const { q, episode, category, updates } = state.filters;
  if (episode && String(item.episode) !== episode) return false;
  if (category && item.category !== category) return false;
  if (updates === "yes" && !hasUpdates(item)) return false;
  if (updates === "no" && hasUpdates(item)) return false;
  if (q) {
    const hay = `${item.title} ${item.pov_summary} ${item.quote} ${item.status}`.toLowerCase();
    if (!hay.includes(q.toLowerCase())) return false;
  }
  return true;
}

function sorted(items) {
  const by = state.sort;
  const copy = items.slice();
  if (by === "ep-asc") {
    copy.sort((a, b) => a.episode - b.episode || a.timestamp_sec - b.timestamp_sec);
  } else if (by === "updates") {
    copy.sort((a, b) => (hasUpdates(b) ? 1 : 0) - (hasUpdates(a) ? 1 : 0) || b.episode - a.episode || a.timestamp_sec - b.timestamp_sec);
  } else {
    copy.sort((a, b) => b.episode - a.episode || a.timestamp_sec - b.timestamp_sec);
  }
  return copy;
}

function render() {
  const list = document.getElementById("items");
  const countEl = document.getElementById("count");
  const empty = document.getElementById("empty");
  list.innerHTML = "";
  const filtered = sorted(state.store.items.filter(matches));
  const withUpdates = filtered.filter(hasUpdates).length;
  countEl.textContent = `${filtered.length} of ${state.store.items.length} items · ${withUpdates} with updates`;
  empty.hidden = filtered.length > 0;
  for (const item of filtered) {
    list.appendChild(
      el("li", { class: "item" }, [
        el("div", { class: "item-head" }, [
          el("h2", { class: "item-title" }, item.title),
          el("span", { class: "badge category" }, item.category),
          episodeLink(item),
        ]),
        el("p", { class: "pov" }, item.pov_summary),
        item.quote ? el("blockquote", { class: "quote" }, `"${item.quote}"`) : null,
        el("div", { class: "status" }, [el("strong", {}, "hosts' status: "), item.status]),
        renderUpdates(item),
      ])
    );
  }
}

function renderUpdates(item) {
  if (!item.updates_fetched_at) return null;
  const updates = item.updates ?? [];
  const summary = item.updates_summary ?? "";
  const wrapper = el("details", { class: "updates" });
  if (updates.length > 0) wrapper.open = true;
  wrapper.appendChild(
    el("summary", { class: "updates-summary" },
      updates.length > 0
        ? `news since · ${updates.length} update${updates.length === 1 ? "" : "s"}`
        : "news since · none"
    )
  );
  const body = el("div", { class: "updates-body" });
  if (summary) body.appendChild(el("p", { class: "updates-text" }, summary));
  if (updates.length) {
    const ul = el("ul", { class: "updates-list" });
    for (const u of updates) {
      const headline = u.url
        ? el("a", { href: u.url, target: "_blank", rel: "noopener" }, u.headline)
        : el("span", {}, u.headline);
      const meta = [u.source, u.date].filter(Boolean).join(" · ");
      ul.appendChild(
        el("li", {}, [
          headline,
          meta ? el("span", { class: "updates-meta" }, ` — ${meta}`) : null,
          u.summary ? el("p", { class: "updates-item-sum" }, u.summary) : null,
        ])
      );
    }
    body.appendChild(ul);
  }
  wrapper.appendChild(body);
  return wrapper;
}

function populateSelect(id, values, label = v => v) {
  const sel = document.getElementById(id);
  for (const v of values) {
    sel.appendChild(el("option", { value: v }, label(v)));
  }
  sel.addEventListener("change", e => {
    state.filters[id] = e.target.value;
    render();
  });
}

async function init() {
  const res = await fetch("items.json", { cache: "no-cache" });
  if (!res.ok) {
    document.getElementById("count").textContent = "could not load items.json";
    return;
  }
  state.store = await res.json();

  const epNumbers = [...new Set(state.store.items.map(i => i.episode))].sort((a, b) => b - a);
  populateSelect("episode", epNumbers, n => {
    const ep = episodeFor(n);
    return ep ? `ep ${n} · ${ep.date}` : `ep ${n}`;
  });
  const cats = [...new Set(state.store.items.map(i => i.category))].sort();
  populateSelect("category", cats);

  document.getElementById("updates").addEventListener("change", e => {
    state.filters.updates = e.target.value;
    render();
  });
  document.getElementById("sort").addEventListener("change", e => {
    state.sort = e.target.value;
    render();
  });
  document.getElementById("search").addEventListener("input", e => {
    state.filters.q = e.target.value;
    render();
  });

  render();
}

init();
