(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const audio = $("audio");

  const state = {
    results: [],
    queue: loadJSON("litetube_queue", []),
    currentIndex: -1,
    currentTrack: null,
    shuffle: false,
    repeat: false,
    quality: Number(localStorage.getItem("litetube_quality") || 64),
    searchTimer: null,
    suggestionTimer: null,
    suggestionAbort: null,
    suggestionIndex: -1,
    searchToken: 0,
    playlists: loadJSON("litetube_playlists", []),
    pendingPlaylistTrack: null,
    loadingAudio: false,
    recommendations: [],
    recommendationIndex: -1,
    history: [],
    historyIndex: -1,
    activeView: "home",
    activePlaylistId: null,
    dragging: false,
  };

  const el = {
    searchForm: $("searchForm"), searchInput: $("searchInput"), clearSearch: $("clearSearch"),
    suggestions: $("suggestions"), homeView: $("homeView"), searchView: $("searchView"),
    queueView: $("queueView"), playlistView: $("playlistView"), historyView: $("historyView"),
    resultTitle: $("resultTitle"), resultEyebrow: $("resultEyebrow"), searchStatus: $("searchStatus"),
    resultsList: $("resultsList"), queueList: $("queueList"), queueCount: $("queueCount"),
    playAllBtn: $("playAllBtn"), addAllQueueBtn: $("addAllQueueBtn"), queuePlayAllBtn: $("queuePlayAllBtn"),
    clearQueueBtn: $("clearQueueBtn"), recommendations: $("recommendations"), toast: $("toast"),
    player: document.querySelector(".player"), playerThumb: $("playerThumb"), playerTitle: $("playerTitle"),
    playerArtist: $("playerArtist"), playBtn: $("playBtn"), prevBtn: $("prevBtn"), nextBtn: $("nextBtn"),
    shuffleBtn: $("shuffleBtn"), repeatBtn: $("repeatBtn"), progress: $("progress"), currentTime: $("currentTime"),
    totalTime: $("totalTime"), muteBtn: $("muteBtn"), volume: $("volume"), qualitySelect: $("qualitySelect"),
    playlistModal: $("playlistModal"), playlistNameInput: $("playlistNameInput"), playlistCreateForm: $("playlistCreateForm"),
    closePlaylistModal: $("closePlaylistModal"), picker: $("playlistPicker"), pickerList: $("playlistPickerList"),
    closePicker: $("closePicker"), pickerNewPlaylist: $("pickerNewPlaylist"), sidebarPlaylists: $("sidebarPlaylists"),
    playlistsPage: $("playlistsPage"), playlistPageNew: $("playlistPageNew"), newPlaylistBtn: $("newPlaylistBtn"),
    topPlaylistBtn: $("topPlaylistBtn"), topQueueBtn: $("topQueueBtn"), homeSearchBtn: $("homeSearchBtn"),
    refreshRecommendations: $("refreshRecommendations"), historyList: $("historyList"), historyCount: $("historyCount"),
    searchBackBtn: $("searchBackBtn"), themeToggle: $("themeToggle"),
    checkUpdateBtn: $("checkUpdateBtn"), updateModal: $("updateModal"), updateTitle: $("updateTitle"),
    updateMessage: $("updateMessage"), updateNowBtn: $("updateNowBtn"), updateLaterBtn: $("updateLaterBtn"), closeUpdateModal: $("closeUpdateModal"),
  };

  function loadJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  }

  function saveState() {
    localStorage.setItem("litetube_queue", JSON.stringify(state.queue));
    localStorage.setItem("litetube_playlists", JSON.stringify(state.playlists));
    localStorage.setItem("litetube_quality", String(state.quality));
  }

  function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function formatTime(value) {
    if (!Number.isFinite(Number(value)) || Number(value) < 0) return "0:00";
    const s = Math.floor(Number(value));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  function normalizeTrack(raw) {
    if (!raw || typeof raw !== "object") return null;
    const id = String(raw.id || "").trim();
    if (!/^[\w-]{11}$/.test(id)) return null;
    return {
      id, title: String(raw.title || "Untitled"),
      artist: String(raw.artist || raw.uploader || raw.channel || "YouTube"),
      thumbnail: String(raw.thumbnail || `https://i.ytimg.com/vi/${id}/hqdefault.jpg`),
      duration: Number.isFinite(Number(raw.duration)) ? Number(raw.duration) : null,
      url: String(raw.url || `https://www.youtube.com/watch?v=${id}`),
    };
  }

  function normalizeTracks(payload) {
    const list = Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : [];
    return list.map(normalizeTrack).filter(Boolean);
  }

  async function fetchJSON(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    let data;
    try { data = await response.json(); } catch { throw new Error(`Invalid server response (${response.status}).`); }
    if (!response.ok) throw new Error(data?.error || `Request failed (${response.status}).`);
    return data;
  }

  function toast(message) {
    el.toast.textContent = message;
    el.toast.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => el.toast.classList.remove("show"), 2600);
  }

  function showView(view) {
    const views = [el.homeView, el.searchView, el.queueView, el.playlistView, el.historyView];
    views.forEach(v => v?.classList.remove("active"));
    const map = { home: el.homeView, search: el.searchView, queue: el.queueView, playlist: el.playlistView, history: el.historyView };
    (map[view] || el.homeView)?.classList.add("active");
    state.activeView = view;
    document.querySelectorAll(".nav-item").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view || btn.dataset.action === view));
    if (view === "playlist") renderPlaylists();
    if (view === "history") renderHistory();
  }

  function addToHistory(track) {
    if (!track) return;
    if (state.historyIndex < state.history.length - 1) state.history = state.history.slice(0, state.historyIndex + 1);
    if (state.history[state.history.length - 1]?.id === track.id) {
      state.historyIndex = state.history.length - 1;
      return;
    }
    state.history.push(track);
    if (state.history.length > 50) state.history.splice(0, state.history.length - 50);
    state.historyIndex = state.history.length - 1;
    renderHistory();
  }

  function setPlayer(track) {
    state.currentTrack = track;
    el.playerThumb.src = track.thumbnail;
    el.playerTitle.textContent = track.title;
    el.playerArtist.textContent = track.artist;
    renderResults();
    renderQueue();
    renderHistory();
    el.player.classList.add("has-track");
  }

  function updateVolumeUI() {
    const value = Number(el.volume.value);
    el.volume.style.setProperty("--vp", `${value * 100}%`);
    el.muteBtn.innerHTML = audio.muted || value === 0 ? '<i class="bi bi-volume-mute-fill"></i>' : value < .5 ? '<i class="bi bi-volume-down-fill"></i>' : '<i class="bi bi-volume-up-fill"></i>';
  }

  function updateProgress() {
    const duration = Number(audio.duration);
    const current = Number(audio.currentTime);
    const pct = duration > 0 ? (current / duration) * 100 : 0;
    el.progress.value = pct;
    el.progress.style.setProperty("--p", `${pct}%`);
    el.currentTime.textContent = formatTime(current);
    el.totalTime.textContent = formatTime(duration);
  }

  function addToQueue(track, silent = false) {
    if (!track) return;
    if (state.queue.some(t => t.id === track.id)) return silent ? false : toast("Already in queue");
    state.queue.push(track); saveState(); renderQueue();
    if (!silent) toast("Added to queue");
    return true;
  }

  function addAllToQueue() {
    let added = 0;
    state.results.forEach(track => { if (!state.queue.some(t => t.id === track.id)) { state.queue.push(track); added++; } });
    saveState(); renderQueue(); toast(added ? `${added} songs added to queue` : "Songs are already in queue");
  }

  async function playTrack(track, options = {}) {
    if (!track) return;
    const fromHistory = options.fromHistory === true;
    const fromQueue = options.fromQueue === true;
    if (state.currentTrack && state.currentTrack.id !== track.id && !fromHistory) addToHistory(state.currentTrack);
    if (!fromQueue) state.currentIndex = -1;
    state.loadingAudio = true; setPlayer(track); el.playBtn.innerHTML = '<i class="bi bi-three-dots"></i>';
    try {
      const data = await fetchJSON(`/api/audio/${encodeURIComponent(track.id)}?quality=${state.quality}`);
      if (!data.url) throw new Error("No playable audio stream was returned.");
      audio.src = data.url; audio.preload = "none"; audio.load(); await audio.play();
      state.loadingAudio = false; el.playBtn.innerHTML = '<i class="bi bi-pause-fill"></i>'; el.player.classList.add("playing");
      if (data.quality && Number(data.quality) !== state.quality) toast(`Using closest available audio: ${data.quality}k`);
    } catch (error) {
      state.loadingAudio = false; el.playBtn.innerHTML = '<i class="bi bi-play-fill"></i>'; el.player.classList.remove("playing");
      toast(error.message || "Unable to play this song.");
    }
  }

  function playResultsIndex(index) {
    const track = state.results[index];
    if (!track) return;
    state.currentIndex = -1;
    playTrack(track);
  }

  function playQueueIndex(index) {
    if (!state.queue[index]) return;
    state.currentIndex = index;
    playTrack(state.queue[index], { fromQueue: true });
  }

  function playRecommendation() {
    const list = state.recommendations || [];
    if (!list.length) { loadRecommendations(true); return; }
    let next = state.recommendationIndex + 1;
    if (state.shuffle && list.length > 1) next = Math.floor(Math.random() * list.length);
    state.recommendationIndex = next % list.length;
    state.currentIndex = -1;
    playTrack(list[state.recommendationIndex]);
  }

  function playAllResults() {
    if (!state.results.length) return;
    state.queue = [...state.results];
    state.currentIndex = 0;
    saveState(); renderQueue(); playQueueIndex(0);
  }

  function playWholeQueue() {
    if (!state.queue.length) return toast("Queue is empty");
    playQueueIndex(state.currentIndex >= 0 ? state.currentIndex : 0);
  }

  function removeFinishedQueueTrack() {
    if (state.currentIndex < 0 || state.currentIndex >= state.queue.length) return null;
    const index = state.currentIndex;
    const removed = state.queue.splice(index, 1)[0];
    state.currentIndex = -1;
    saveState(); renderQueue();
    return removed;
  }

  function nextTrack() {
    if (state.repeat && state.currentTrack) return playTrack(state.currentTrack, { fromQueue: state.currentIndex >= 0 });

    // A queue item has just finished: remove it, then the item that shifted into
    // its old position becomes the next song. This is the key YouTube-style queue flow.
    if (state.currentIndex >= 0 && state.currentIndex < state.queue.length) {
      const oldIndex = state.currentIndex;
      state.queue.splice(oldIndex, 1);
      saveState(); renderQueue();
      if (state.queue.length) {
        const nextIndex = state.shuffle && state.queue.length > 1 ? Math.floor(Math.random() * state.queue.length) : Math.min(oldIndex, state.queue.length - 1);
        return playQueueIndex(nextIndex);
      }
      state.currentIndex = -1;
      return playRecommendation();
    }

    // Search/recommendation song is not a queue item. If a queue exists, it wins.
    if (state.queue.length) return playQueueIndex(state.shuffle && state.queue.length > 1 ? Math.floor(Math.random() * state.queue.length) : 0);
    return playRecommendation();
  }

  function previousTrack() {
    if (audio.currentTime > 5) { audio.currentTime = 0; return; }
    if (state.historyIndex < 0 || !state.history[state.historyIndex]) { audio.currentTime = 0; return; }
    const previous = state.history[state.historyIndex];
    state.historyIndex--;
    state.currentIndex = -1;
    playTrack(previous, { fromHistory: true });
    renderHistory();
  }

  function removeFromQueue(index) {
    index = Number(index);
    if (index < 0 || index >= state.queue.length) return;
    const removed = state.queue.splice(index, 1)[0];
    if (state.currentIndex > index) state.currentIndex--;
    else if (state.currentIndex === index) state.currentIndex = -1;
    saveState(); renderQueue(); toast(`${removed.title} removed from queue`);
  }

  function moveArrayItem(arr, from, to) {
    if (from === to || from < 0 || to < 0 || from >= arr.length || to >= arr.length) return false;
    const [item] = arr.splice(from, 1); arr.splice(to, 0, item); return true;
  }

  function moveQueueItem(from, to) {
    const currentId = state.currentTrack?.id;
    if (!moveArrayItem(state.queue, from, to)) return;
    state.currentIndex = currentId ? state.queue.findIndex(t => t.id === currentId) : -1;
    saveState(); renderQueue();
  }

  async function search(query) {
    const q = query.trim(); if (!q) return;
    showView("search"); el.resultTitle.textContent = q; el.resultEyebrow.textContent = "SEARCH RESULTS";
    el.searchStatus.textContent = "Searching…"; el.searchStatus.classList.remove("error"); closeSuggestions();
    const token = ++state.searchToken;
    try {
      const data = await fetchJSON(`/api/search?q=${encodeURIComponent(q)}`);
      if (token !== state.searchToken) return;
      state.results = normalizeTracks(data); renderResults();
      el.searchStatus.textContent = state.results.length ? `${state.results.length} songs` : "No results found.";
      localStorage.setItem("litetube_last_search", q);
    } catch (error) {
      state.results = []; renderResults(); el.searchStatus.textContent = error.message || "Search failed."; el.searchStatus.classList.add("error");
    }
  }

  async function loadRecommendations(force = false) {
    el.recommendations.innerHTML = `<div class="loading-card"><i class="bi bi-stars"></i> Finding music for you…</div>`;
    try {
      const data = await fetchJSON(`/api/recommendations${force ? `?t=${Date.now()}` : ""}`);
      const tracks = normalizeTracks(data).slice(0, 20); state.recommendations = tracks; state.recommendationIndex = -1;
      if (!tracks.length) { el.recommendations.innerHTML = `<div class="loading-card">Recommendations are temporarily unavailable.</div>`; return; }
      el.recommendations.innerHTML = tracks.map((track, i) => `<article class="recommend-card" data-index="${i}"><img loading="lazy" src="${escapeHtml(track.thumbnail)}" alt=""><div><strong>${escapeHtml(track.title)}</strong><span>${escapeHtml(track.artist)}</span></div></article>`).join("");
      el.recommendations.querySelectorAll(".recommend-card").forEach((card, i) => card.addEventListener("click", () => playTrack(tracks[i])));
    } catch { el.recommendations.innerHTML = `<div class="loading-card">Recommendations are temporarily unavailable.</div>`; }
  }

  function closeSuggestions() { el.suggestions.classList.remove("open"); el.suggestions.innerHTML = ""; state.suggestionIndex = -1; }

  async function suggestions(query) {
    if (state.suggestionAbort) state.suggestionAbort.abort();
    state.suggestionAbort = new AbortController();
    try {
      const response = await fetch(`/api/suggest?q=${encodeURIComponent(query)}`, { signal: state.suggestionAbort.signal, headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error();
      const data = await response.json(); const items = Array.isArray(data?.suggestions) ? data.suggestions : [];
      if (!items.length) return closeSuggestions();
      el.suggestions.innerHTML = items.map((item, i) => `<button class="suggestion" data-index="${i}" type="button"><i class="bi bi-search"></i>${escapeHtml(item)}</button>`).join("");
      el.suggestions.classList.add("open");
      el.suggestions.querySelectorAll(".suggestion").forEach(btn => btn.addEventListener("click", () => { const value = items[Number(btn.dataset.index)]; el.searchInput.value = value; updateClear(); search(value); }));
    } catch (error) { if (error.name !== "AbortError") closeSuggestions(); }
  }

  function scheduleSuggestions() {
    clearTimeout(state.suggestionTimer); const q = el.searchInput.value.trim();
    if (q.length < 2) return closeSuggestions(); state.suggestionTimer = setTimeout(() => suggestions(q), 250);
  }

  function updateClear() { el.clearSearch.classList.toggle("show", Boolean(el.searchInput.value)); }

  function renderTrackList(container, tracks, mode = "results") {
    if (!tracks.length) {
      container.innerHTML = `<div class="empty"><i class="bi bi-music-note-list"></i><strong>${mode === "queue" ? "Queue is empty" : "No songs found"}</strong><span>${mode === "queue" ? "Add songs from search results." : "Try another search."}</span></div>`;
      return;
    }
    container.innerHTML = tracks.map((track, i) => {
      const playing = state.currentTrack?.id === track.id && !audio.paused;
      if (mode === "queue") return `<article class="track queue-track ${playing ? "playing" : ""}" data-index="${i}" data-id="${escapeHtml(track.id)}"><button class="track-play" type="button" aria-label="Play"><i class="bi ${playing ? "bi-pause-fill" : "bi-play-fill"}"></i></button><img class="track-thumb" loading="lazy" src="${escapeHtml(track.thumbnail)}" alt=""><div class="track-info"><div class="track-title" title="${escapeHtml(track.title)}">${escapeHtml(track.title)}</div><div class="track-artist" title="${escapeHtml(track.artist)}">${escapeHtml(track.artist)}</div></div><div class="track-duration">${formatTime(track.duration)}</div><div class="queue-actions"><button class="icon-btn drag-handle" type="button" title="Drag to reorder"><i class="bi bi-grip-vertical"></i></button><button class="icon-btn remove-queue" type="button" title="Remove from queue"><i class="bi bi-x-lg"></i></button></div></article>`;
      return `<article class="track ${playing ? "playing" : ""}" data-index="${i}" data-id="${escapeHtml(track.id)}"><button class="track-play" type="button" aria-label="Play"><i class="bi ${playing ? "bi-pause-fill" : "bi-play-fill"}"></i></button><img class="track-thumb" loading="lazy" src="${escapeHtml(track.thumbnail)}" alt=""><div class="track-info"><div class="track-title" title="${escapeHtml(track.title)}">${escapeHtml(track.title)}</div><div class="track-artist" title="${escapeHtml(track.artist)}">${escapeHtml(track.artist)}</div></div><div class="track-duration">${formatTime(track.duration)}</div><button class="track-action add-queue" type="button"><i class="bi bi-plus-lg"></i> Queue</button><button class="track-action add-playlist" type="button"><i class="bi bi-music-note-list"></i> Playlist</button></article>`;
    }).join("");

    container.querySelectorAll(".track").forEach(row => {
      const index = Number(row.dataset.index), track = tracks[index];
      row.querySelector(".track-play")?.addEventListener("click", e => { e.stopPropagation(); mode === "queue" ? playQueueIndex(index) : playResultsIndex(index); });
      row.querySelector(".add-queue")?.addEventListener("click", e => { e.stopPropagation(); addToQueue(track); });
      row.querySelector(".add-playlist")?.addEventListener("click", e => { e.stopPropagation(); openPlaylistPicker(track); });
      row.querySelector(".remove-queue")?.addEventListener("click", e => { e.stopPropagation(); removeFromQueue(index); });
    });
    if (mode === "queue") setupQueueDrag();
  }

  function renderResults() {
    renderTrackList(el.resultsList, state.results, "results");
    el.playAllBtn.classList.toggle("hidden", !state.results.length); el.addAllQueueBtn.classList.toggle("hidden", !state.results.length);
  }

  function renderQueue() {
    el.queueCount.textContent = state.queue.length; renderTrackList(el.queueList, state.queue, "queue");
  }

  function renderHistory() {
    if (!el.historyList) return;
    el.historyCount.textContent = state.history.length;
    if (!state.history.length) { el.historyList.innerHTML = `<div class="empty"><i class="bi bi-clock-history"></i><strong>No history yet</strong><span>Your last 50 played songs will appear here.</span></div>`; return; }
    const currentId = state.currentTrack?.id;
    el.historyList.innerHTML = state.history.slice().reverse().map((track, reverseIndex) => `<article class="history-row ${currentId === track.id ? "playing" : ""}"><img src="${escapeHtml(track.thumbnail)}" alt=""><div><strong>${escapeHtml(track.title)}</strong><span>${escapeHtml(track.artist)}</span></div><button class="icon-btn history-play" data-id="${escapeHtml(track.id)}" title="Play"><i class="bi bi-play-fill"></i></button></article>`).join("");
    el.historyList.querySelectorAll(".history-play").forEach(btn => btn.addEventListener("click", () => {
      const track = state.history.find(t => t.id === btn.dataset.id); if (!track) return; state.currentIndex = -1; playTrack(track);
    }));
  }

  function openCreatePlaylist() { el.playlistModal.classList.remove("hidden"); setTimeout(() => el.playlistNameInput.focus(), 30); }
  function closeCreatePlaylist() { el.playlistModal.classList.add("hidden"); }

  function createPlaylist(name) {
    const clean = String(name || "").trim(); if (!clean) return;
    if (state.playlists.some(p => p.name.toLowerCase() === clean.toLowerCase())) return toast("That playlist already exists");
    const playlist = { id: crypto.randomUUID(), name: clean, tracks: [] }; state.playlists.unshift(playlist); saveState(); renderPlaylists(); closeCreatePlaylist(); toast(`Created "${clean}"`);
  }

  function removePlaylistTrack(pid, index) {
    const p = state.playlists.find(x => x.id === pid); if (!p) return;
    index = Number(index); if (index < 0 || index >= p.tracks.length) return;
    const removed = p.tracks.splice(index, 1)[0]; saveState(); renderPlaylists(); toast(`${removed.title} removed from playlist`);
  }

  function movePlaylistTrack(pid, from, to) {
    const p = state.playlists.find(x => x.id === pid); if (!p) return;
    if (moveArrayItem(p.tracks, Number(from), Number(to))) { saveState(); renderPlaylists(); }
  }

  function playPlaylist(pid, startIndex = 0) {
    const p = state.playlists.find(x => x.id === pid); if (!p?.tracks.length) return toast("Playlist is empty");
    const start = Math.max(0, Math.min(Number(startIndex) || 0, p.tracks.length - 1));
    // Playlist playback uses a rotated private queue so starting at song 6 means
    // 6 → 7 → … → last → 1 → … → 5, then recommendations. The saved playlist itself is never reordered.
    state.queue = [...p.tracks.slice(start), ...p.tracks.slice(0, start)];
    state.currentIndex = 0; saveState(); renderQueue(); playQueueIndex(0);
  }

  function renderPlaylists() {
    el.sidebarPlaylists.innerHTML = state.playlists.length ? state.playlists.map(p => `<button class="sidebar-playlist ${state.activePlaylistId === p.id ? "active" : ""}" data-id="${escapeHtml(p.id)}"><i class="bi bi-music-note-list"></i>${escapeHtml(p.name)}<span>${p.tracks.length}</span></button>`).join("") : `<div class="side-empty">No playlists yet</div>`;
    el.sidebarPlaylists.querySelectorAll(".sidebar-playlist").forEach(btn => btn.addEventListener("click", () => showPlaylistPage(btn.dataset.id)));
    if (!state.playlists.length) { el.playlistsPage.innerHTML = `<div class="empty"><i class="bi bi-music-note-list"></i><strong>No playlists yet</strong><span>Create one, then add songs from any search result.</span></div>`; return; }

    el.playlistsPage.innerHTML = state.playlists.map(p => `<article class="playlist-card" data-pid="${escapeHtml(p.id)}"><div class="playlist-card-head"><div><span class="playlist-label">PLAYLIST</span><h3>${escapeHtml(p.name)}</h3><span>${p.tracks.length} songs</span></div><div class="playlist-actions"><button class="light-btn playlist-play" data-id="${escapeHtml(p.id)}"><i class="bi bi-play-fill"></i> Play all</button><button class="icon-btn playlist-delete" data-id="${escapeHtml(p.id)}" title="Delete playlist"><i class="bi bi-trash3"></i></button></div></div><div class="playlist-track-list" data-pid="${escapeHtml(p.id)}">${p.tracks.length ? p.tracks.map((track,i) => `<div class="playlist-track" data-index="${i}" data-id="${escapeHtml(track.id)}"><span class="track-number">${String(i+1).padStart(2,"0")}</span><button class="icon-btn playlist-drag-handle" type="button" title="Drag to reorder"><i class="bi bi-grip-vertical"></i></button><img loading="lazy" src="${escapeHtml(track.thumbnail)}" alt=""><div><strong>${escapeHtml(track.title)}</strong><small>${escapeHtml(track.artist)}</small></div><span class="playlist-duration">${formatTime(track.duration)}</span><button class="icon-btn playlist-track-play" data-pid="${escapeHtml(p.id)}" data-index="${i}" title="Play"><i class="bi bi-play-fill"></i></button><button class="icon-btn playlist-track-remove" data-pid="${escapeHtml(p.id)}" data-index="${i}" title="Remove"><i class="bi bi-x-lg"></i></button></div>`).join("") : `<div class="playlist-empty">This playlist is empty.</div>`}</div></article>`).join("");

    el.playlistsPage.querySelectorAll(".playlist-play").forEach(btn => btn.addEventListener("click", () => playPlaylist(btn.dataset.id, 0)));
    el.playlistsPage.querySelectorAll(".playlist-delete").forEach(btn => btn.addEventListener("click", () => { state.playlists = state.playlists.filter(p => p.id !== btn.dataset.id); if (state.activePlaylistId === btn.dataset.id) state.activePlaylistId = null; saveState(); renderPlaylists(); toast("Playlist deleted"); }));
    el.playlistsPage.querySelectorAll(".playlist-track-play").forEach(btn => btn.addEventListener("click", () => playPlaylist(btn.dataset.pid, Number(btn.dataset.index))));
    el.playlistsPage.querySelectorAll(".playlist-track-remove").forEach(btn => btn.addEventListener("click", e => { e.stopPropagation(); removePlaylistTrack(btn.dataset.pid, Number(btn.dataset.index)); }));
    setupPlaylistDrag();
  }

  function showPlaylistPage(id) {
    state.activePlaylistId = id; const p = state.playlists.find(x => x.id === id);
    el.playlistsPage.scrollTop = 0; $("playlistPageTitle").textContent = p ? p.name : "Playlists"; showView("playlist"); renderPlaylists();
  }

  function openPlaylistPicker(track) {
    state.pendingPlaylistTrack = track;
    if (!state.playlists.length) return openCreatePlaylist();
    el.pickerList.innerHTML = state.playlists.map(p => `<button class="picker-item" data-id="${escapeHtml(p.id)}"><i class="bi bi-music-note-list"></i>${escapeHtml(p.name)}<span>${p.tracks.length}</span></button>`).join("");
    el.picker.classList.remove("hidden");
    el.pickerList.querySelectorAll(".picker-item").forEach(btn => btn.addEventListener("click", () => { const p = state.playlists.find(x => x.id === btn.dataset.id); if (!p) return; if (p.tracks.some(t => t.id === track.id)) return toast("Already in playlist"); p.tracks.push(track); saveState(); renderPlaylists(); el.picker.classList.add("hidden"); toast(`Added to ${p.name}`); }));
  }

  function setupDrag(list, handleSelector, rowSelector, onMove, getRows) {
    list.querySelectorAll(handleSelector).forEach(handle => {
      handle.onpointerdown = (event) => {
        if (event.button !== 0 || state.dragging) return;
        const row = handle.closest(rowSelector); if (!row) return;
        event.preventDefault();
        state.dragging = true; handle.setPointerCapture?.(event.pointerId);
        const rect = row.getBoundingClientRect();
        const ghost = row.cloneNode(true); ghost.classList.add("dragging-ghost");
        Object.assign(ghost.style, { position: "fixed", left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, height: `${rect.height}px`, margin: "0", pointerEvents: "none", zIndex: "99999" });
        document.body.appendChild(ghost);
        const placeholder = document.createElement("div"); placeholder.className = "drag-placeholder"; placeholder.style.height = `${rect.height}px`;
        row.replaceWith(placeholder);
        const originalIndex = Number(row.dataset.index);
        const onMovePointer = (e) => {
          ghost.style.top = `${e.clientY - rect.height / 2}px`;
          const rows = getRows().filter(r => r !== row);
          let before = null;
          for (const r of rows) { const rr = r.getBoundingClientRect(); if (e.clientY < rr.top + rr.height / 2) { before = r; break; } }
          if (before) before.parentNode.insertBefore(placeholder, before); else list.appendChild(placeholder);
        };
        const cleanup = () => {
          document.removeEventListener("pointermove", onMovePointer);
          document.removeEventListener("pointerup", onUp);
          ghost.remove(); state.dragging = false;
        };
        const onUp = () => {
          const rowsNow = [...list.querySelectorAll(rowSelector)];
          let targetIndex = rowsNow.length;
          let cursor = placeholder.previousElementSibling;
          if (cursor) targetIndex = rowsNow.indexOf(cursor) + 1;
          if (placeholder.nextElementSibling) targetIndex = rowsNow.indexOf(placeholder.nextElementSibling);
          row.dataset.index = String(originalIndex);
          placeholder.replaceWith(row);
          if (targetIndex !== originalIndex) onMove(originalIndex, targetIndex);
          cleanup();
        };
        document.addEventListener("pointermove", onMovePointer, { passive: false });
        document.addEventListener("pointerup", onUp, { once: true });
      };
    });
  }

  function setupQueueDrag() {
    setupDrag(el.queueList, ".drag-handle", ".queue-track", (from,to) => moveQueueItem(from,to), () => [...el.queueList.querySelectorAll(".queue-track")]);
  }

  function setupPlaylistDrag() {
    el.playlistsPage.querySelectorAll(".playlist-track-list").forEach(list => {
      const pid = list.dataset.pid;
      setupDrag(list, ".playlist-drag-handle", ".playlist-track", (from,to) => movePlaylistTrack(pid,from,to), () => [...list.querySelectorAll(".playlist-track")]);
    });
  }

  function togglePlayPause() {
    if (!state.currentTrack) return state.queue.length ? playQueueIndex(0) : toast("Search for a song first");
    if (audio.paused) audio.play().catch(() => toast("Unable to resume audio")); else audio.pause();
  }

  function toggleShuffle() { state.shuffle = !state.shuffle; el.shuffleBtn.classList.toggle("active", state.shuffle); toast(state.shuffle ? "Shuffle on" : "Shuffle off"); }
  function toggleRepeat() { state.repeat = !state.repeat; el.repeatBtn.classList.toggle("active", state.repeat); toast(state.repeat ? "Repeat on" : "Repeat off"); }

  function applyTheme(theme) {
    document.documentElement.classList.toggle("dark", theme === "dark"); localStorage.setItem("litetube-theme", theme);
    if (el.themeToggle) el.themeToggle.innerHTML = theme === "dark" ? '<i class="bi bi-sun-fill"></i>' : '<i class="bi bi-moon-stars-fill"></i>';
  }

  let latestReleaseUrl = "";

  async function getUpdateConfig() {
    try {
      const response = await fetch("/update_config.json", { cache: "no-store" });
      if (!response.ok) return null;
      return await response.json();
    } catch { return null; }
  }

  async function checkForUpdate(showCurrent = false) {
    const config = await getUpdateConfig();
    const repo = String(config?.github_repo || "").trim();
    if (!repo || repo.includes("YOUR_GITHUB_USERNAME")) {
      if (showCurrent) toast("Add your GitHub repo in update_config.json first");
      return;
    }
    try {
      const currentResponse = await fetch("/api/version", { cache: "no-store" });
      const currentData = await currentResponse.json();
      const current = String(currentData.version || "1.0.0").replace(/^v/i, "");
      const releaseResponse = await fetch(`https://api.github.com/repos/${repo}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } });
      if (!releaseResponse.ok) throw new Error("GitHub release lookup failed");
      const release = await releaseResponse.json();
      const latest = String(release.tag_name || "").replace(/^v/i, "");
      if (!latest) return;
      if (compareVersions(latest, current) > 0) {
        latestReleaseUrl = release.html_url || `https://github.com/${repo}/releases/latest`;
        el.updateTitle.textContent = `Version ${latest} is available`;
        el.updateMessage.textContent = release.body ? `${release.name || "A new LiteTube version is ready."}\n\n${release.body.slice(0, 700)}` : `You are running ${current}. Update to ${latest} for the latest improvements.`;
        el.updateMessage.style.whiteSpace = "pre-line";
        el.updateNowBtn.classList.remove("hidden");
        el.updateModal.classList.remove("hidden");
      } else if (showCurrent) {
        el.updateTitle.textContent = "LiteTube is up to date";
        el.updateMessage.textContent = `You are running version ${current}.`;
        el.updateNowBtn.classList.add("hidden");
        el.updateModal.classList.remove("hidden");
      }
    } catch (error) {
      if (showCurrent) toast("Could not check GitHub for updates");
    }
  }

  function compareVersions(a, b) {
    const aa = String(a).split(".").map(x => parseInt(x, 10) || 0);
    const bb = String(b).split(".").map(x => parseInt(x, 10) || 0);
    for (let i = 0; i < Math.max(aa.length, bb.length); i++) {
      if ((aa[i] || 0) !== (bb[i] || 0)) return (aa[i] || 0) > (bb[i] || 0) ? 1 : -1;
    }
    return 0;
  }

  // Events
  el.searchForm.addEventListener("submit", e => { e.preventDefault(); search(el.searchInput.value); });
  el.searchInput.addEventListener("input", () => { updateClear(); scheduleSuggestions(); });
  el.searchInput.addEventListener("keydown", e => { if (e.key === "Escape") closeSuggestions(); });
  el.clearSearch.addEventListener("click", () => { el.searchInput.value = ""; updateClear(); closeSuggestions(); el.searchInput.focus(); });
  document.addEventListener("click", e => { if (!el.searchForm.contains(e.target)) closeSuggestions(); });
  document.querySelectorAll(".nav-item").forEach(btn => btn.addEventListener("click", () => {
    const action = btn.dataset.action;
    if (action === "playlists") return showView("playlist");
    if (action === "recent") return showView("history");
    if (action === "liked") return toast("Liked Songs is coming next");
    showView(btn.dataset.view || "home");
  }));
  el.topQueueBtn.addEventListener("click", () => showView("queue"));
  el.topPlaylistBtn.addEventListener("click", () => showView("playlist"));
  el.newPlaylistBtn.addEventListener("click", openCreatePlaylist); el.playlistPageNew.addEventListener("click", openCreatePlaylist);
  el.homeSearchBtn.addEventListener("click", () => el.searchInput.focus());
  el.searchBackBtn?.addEventListener("click", () => showView("home"));
  el.addAllQueueBtn.addEventListener("click", addAllToQueue); el.playAllBtn.addEventListener("click", playAllResults);
  el.queuePlayAllBtn.addEventListener("click", playWholeQueue); el.clearQueueBtn.addEventListener("click", () => { state.queue = []; state.currentIndex = -1; saveState(); renderQueue(); toast("Queue cleared"); });
  el.refreshRecommendations.addEventListener("click", () => loadRecommendations(true));
  document.querySelectorAll("[data-search]").forEach(btn => btn.addEventListener("click", () => { el.searchInput.value = btn.dataset.search; updateClear(); search(btn.dataset.search); }));
  el.playBtn.addEventListener("click", togglePlayPause); el.prevBtn.addEventListener("click", previousTrack); el.nextBtn.addEventListener("click", nextTrack); el.shuffleBtn.addEventListener("click", toggleShuffle); el.repeatBtn.addEventListener("click", toggleRepeat);
  el.progress.addEventListener("input", () => { if (Number.isFinite(audio.duration)) audio.currentTime = (Number(el.progress.value) / 100) * audio.duration; updateProgress(); });
  el.volume.addEventListener("input", () => { audio.volume = Number(el.volume.value); updateVolumeUI(); });
  el.muteBtn.addEventListener("click", () => { audio.muted = !audio.muted; updateVolumeUI(); });
  el.qualitySelect.addEventListener("change", () => { state.quality = Number(el.qualitySelect.value); saveState(); if (state.currentTrack) playTrack(state.currentTrack, { fromQueue: state.currentIndex >= 0 }); });
  el.closePlaylistModal.addEventListener("click", closeCreatePlaylist); el.playlistCreateForm.addEventListener("submit", e => { e.preventDefault(); createPlaylist(el.playlistNameInput.value); el.playlistNameInput.value = ""; });
  el.closePicker.addEventListener("click", () => el.picker.classList.add("hidden")); el.pickerNewPlaylist.addEventListener("click", () => { el.picker.classList.add("hidden"); openCreatePlaylist(); });
  el.themeToggle?.addEventListener("click", () => applyTheme(document.documentElement.classList.contains("dark") ? "light" : "dark"));
  el.checkUpdateBtn?.addEventListener("click", () => checkForUpdate(true));
  el.closeUpdateModal?.addEventListener("click", () => el.updateModal.classList.add("hidden"));
  el.updateLaterBtn?.addEventListener("click", () => el.updateModal.classList.add("hidden"));
  el.updateNowBtn?.addEventListener("click", () => { if (latestReleaseUrl) window.open(latestReleaseUrl, "_blank", "noopener"); });
  audio.addEventListener("play", () => { el.playBtn.innerHTML = '<i class="bi bi-pause-fill"></i>'; el.player.classList.add("playing"); renderResults(); renderQueue(); });
  audio.addEventListener("pause", () => { el.playBtn.innerHTML = '<i class="bi bi-play-fill"></i>'; el.player.classList.remove("playing"); renderResults(); renderQueue(); });
  audio.addEventListener("timeupdate", updateProgress); audio.addEventListener("loadedmetadata", updateProgress); audio.addEventListener("ended", nextTrack);

  // Initial state
  applyTheme(localStorage.getItem("litetube-theme") || "light");
  el.qualitySelect.value = String(state.quality);
  audio.volume = Number(el.volume.value); updateVolumeUI(); updateProgress();
  renderResults(); renderQueue(); renderPlaylists(); renderHistory(); loadRecommendations();
  setTimeout(() => checkForUpdate(false), 1800);
})();
