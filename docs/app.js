const SPOTIFY_URL = id => `https://open.spotify.com/episode/${id}`;

const state = { store: { episodes: [], items: [] }, filters: { q: "", episode: "", category: "" } };

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

function matches(item) {
  const { q, episode, category } = state.filters;
  if (episode && String(item.episode) !== episode) return false;
  if (category && item.category !== category) return false;
  if (q) {
    const hay = `${item.title} ${item.pov_summary} ${item.quote} ${item.status}`.toLowerCase();
    if (!hay.includes(q.toLowerCase())) return false;
  }
  return true;
}

function render() {
  const list = document.getElementById("items");
  const countEl = document.getElementById("count");
  const empty = document.getElementById("empty");
  list.innerHTML = "";
  const filtered = state.store.items.filter(matches);
  countEl.textContent = `${filtered.length} of ${state.store.items.length} items`;
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
        el("div", { class: "status" }, [el("strong", {}, "status: "), item.status]),
      ])
    );
  }
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

  document.getElementById("search").addEventListener("input", e => {
    state.filters.q = e.target.value;
    render();
  });

  render();
}

init();
