// ===== config =====
const BASE_URL = "http://127.0.0.1:8000";

// ===== token store =====
const store = {
  get access(){ return localStorage.getItem("access_token") || ""; },
  set access(v){ localStorage.setItem("access_token", v || ""); },
  get refresh(){ return localStorage.getItem("refresh_token") || ""; },
  set refresh(v){ localStorage.setItem("refresh_token", v || ""); },
  clear(){
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
};

// Logged-in helper
function isLoggedIn(){ return !!store.access; }

// ===== HTTP helper with auto refresh =====
async function http(path, opts = {}, retry = true){
  const headers = {"Content-Type": "application/json", ...(opts.headers || {})};
  if (store.access) headers.Authorization = `Bearer ${store.access}`;
  const res = await fetch(BASE_URL + path, {...opts, headers});
  if (res.status === 401 && retry && store.refresh){
    const ok = await refreshToken();
    if (ok) return http(path, opts, false);
  }
  return res;
}
async function refreshToken(){
  try{
    const r = await fetch(`${BASE_URL}/api/auth/token/refresh/`,{
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({refresh: store.refresh})
    });
    if (!r.ok) return false;
    const d = await r.json();
    store.access = (d.access || "").trim();
    return !!store.access;
  }catch{ return false; }
}

// ===== auth UI =====
const userBadge = document.getElementById("userBadge");
const loginBtn  = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");

function setAuthUI(user){
  if (user && user.username){
    userBadge.textContent = user.username;
    userBadge.classList.remove("hidden");
    logoutBtn.classList.remove("hidden");
    loginBtn.classList.add("hidden");
  } else {
    userBadge.textContent = "";
    userBadge.classList.add("hidden");
    logoutBtn.classList.add("hidden");
    loginBtn.classList.remove("hidden");
  }
  // whenever auth state changes, update Pay button availability
  setPayEnabled();
}

async function fetchMe(){
  try{
    const r = await http("/api/users/me/");
    if (!r.ok) { setAuthUI(null); return null; }
    const d = await r.json();
    setAuthUI(d);
    return d;
  }catch{ setAuthUI(null); return null; }
}

async function openLogin(){
  const username = prompt("Username");
  const password = prompt("Password");
  if (!username || !password) return;
  const r = await fetch(`${BASE_URL}/api/auth/token/`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({username, password})
  });
  if (!r.ok){ alert("Login failed"); return; }
  const d = await r.json();
  store.access = (d.access || "").trim();
  store.refresh = (d.refresh || "").trim();
  await fetchMe();      // update navbar
  await loadHistory();  // show bookings for this user
  setPayEnabled();
  alert("Logged in");
}

function logout(){
  store.clear();
  setAuthUI(null);
  loadHistory();
}

// ===== DOM refs =====
const rec       = document.getElementById("recMovies");
const pre       = document.getElementById("premiers");
const mvList    = document.getElementById("mvList");
const shList    = document.getElementById("shList");
const seatsBox  = document.getElementById("seats");
const selCount  = document.getElementById("selCount");
const payBtn    = document.getElementById("payBtn");
const bookMsg   = document.getElementById("bookMsg");
const historyBox= document.getElementById("history");
const cinDemoBtn= document.getElementById("cinDemoBtn");

// ===== state =====
let selectedCinema = { id: 1, name: "CinemaSeat Multiplex" };
let selectedMovie  = null;
let selectedShow   = null;
let selectedSeats  = new Set();
let seatMap        = []; // [{number, available}]
let seatCols       = 10;

// ===== helpers =====
function esc(s){ return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c])); }
function poster(m){
  // frontend fallback; backend also provides a fallback now
  return m.poster_url || `https://picsum.photos/seed/${encodeURIComponent(m.title || "movie")}/300/420`;
}

function movieCard(m){
  const a = document.createElement("a");
  a.href = "#";
  a.className = "shrink-0 w-[180px] bg-white rounded-xl overflow-hidden shadow hover:shadow-md transition";
  a.onclick = (e)=>{ e.preventDefault(); pickMovie(m); };
  a.innerHTML = `
    <img class="w-full h-[250px] object-cover" src="${poster(m)}" alt="${esc(m.title)}"/>
    <div class="p-2">
      <div class="font-semibold">${esc(m.title)}</div>
      <div class="text-xs text-zinc-500">${esc(m.language || "")} ${m.certificate ? `• ${esc(m.certificate)}` : ""}</div>
    </div>`;
  return a;
}

function setPayEnabled(){
  const n = selectedSeats.size;
  const logged = isLoggedIn();
  selCount.textContent = `Selected: ${n}`;
  payBtn.disabled = (!logged || n === 0 || n > 6 || !selectedShow);
  payBtn.title = logged ? "" : "Sign in to book seats";
}

function renderSeatsGrid(){
  seatsBox.innerHTML = "";
  const maxNumber = Math.max(...seatMap.map(s => Number(s.number) || 0), 0);
  seatCols = maxNumber >= 60 ? 10 : 8;
  seatsBox.className = `grid gap-2 grid-cols-${seatCols} md:grid-cols-${seatCols}`;

  seatMap.forEach(seat => {
    const btn = document.createElement("button");
    const num = seat.number;
    const taken = !seat.available;

    btn.textContent = num;
    btn.className = "px-2 py-2 border rounded text-sm bg-white";
    if (taken){
      btn.classList.add("bg-zinc-300","text-zinc-600","cursor-not-allowed");
      btn.disabled = true;
    }
    if (selectedSeats.has(num)){
      btn.classList.add("bg-[#f84464]","text-white","border-[#f84464]");
    }

    btn.onclick = () => {
      if (taken) return;
      if (selectedSeats.has(num)){
        selectedSeats.delete(num);
      } else {
        if (selectedSeats.size >= 6){
          alert("You can select a maximum of 6 seats.");
          return;
        }
        selectedSeats.add(num);
      }
      renderSeatsGrid();
      setPayEnabled();
    };

    seatsBox.appendChild(btn);
  });

  setPayEnabled();
}

// ===== flow: cinema → movies → shows → seats =====
cinDemoBtn.onclick = () => {
  selectedCinema = { id: 1, name: "CinemaSeat Multiplex" };
  mvList.innerHTML = `<div class="text-zinc-500">Cinema selected. Click "Load Movies".</div>`;
  shList.innerHTML = `<div class="text-zinc-500">Pick a movie.</div>`;
  seatsBox.innerHTML = "";
  bookMsg.textContent = "";
  selectedMovie = null; selectedShow = null; selectedSeats.clear();
  setPayEnabled();
};

async function loadMovies(){
  mvList.innerHTML = `<div class="text-zinc-500">Loading movies...</div>`;
  try{
    const r = await http("/api/cinema/movies/");
    const ok = r.ok;
    const items = ok ? await r.json() : [];
    mvList.innerHTML = "";
    if (!ok || !Array.isArray(items) || !items.length){
      mvList.innerHTML = `<div class="text-zinc-500">No movies found.</div>`;
      return;
    }

    items.forEach(m=>{
      const row = document.createElement("div");
      row.className = "flex items-center justify-between border rounded-lg p-2 bg-zinc-50";
      row.innerHTML = `<div>${esc(m.title)}</div><button class="bg-[#f84464] text-white px-3 py-1.5 rounded-lg">Select</button>`;
      row.querySelector("button").onclick = ()=>pickMovie(m);
      mvList.appendChild(row);
    });

    rec.innerHTML = ""; pre.innerHTML = "";
    items.slice(0,10).forEach(m=>rec.appendChild(movieCard(m)));
    items.slice(-10).reverse().forEach(m=>pre.appendChild(movieCard(m)));

    shList.innerHTML = `<div class="text-zinc-500">Pick a movie.</div>`;
    seatsBox.innerHTML = "";
    selectedMovie = null; selectedShow = null; selectedSeats.clear(); setPayEnabled();

  }catch{
    mvList.innerHTML = `<div class="text-zinc-500">Network error.</div>`;
  }
}

async function pickMovie(m){
  selectedMovie = m; selectedShow = null; selectedSeats.clear(); setPayEnabled();
  seatsBox.innerHTML = "";
  bookMsg.textContent = "";
  shList.innerHTML = `<div class="text-zinc-500">Loading shows...</div>`;
  try{
    const r = await http(`/api/cinema/movies/${m.id}/shows/`);
    if (!r.ok){ shList.innerHTML = `<div class="text-zinc-500">No shows.</div>`; return; }
    const items = await r.json();
    shList.innerHTML = "";
    if (!Array.isArray(items) || !items.length){
      shList.innerHTML = `<div class="text-zinc-500">No shows.</div>`;
      return;
    }
    items.forEach(s=>{
      const when = s.start_time ? new Date(s.start_time).toLocaleString() : `Show ${s.id}`;
      const row = document.createElement("div");
      row.className = "flex items-center justify-between border rounded-lg p-2 bg-zinc-50";
      row.innerHTML = `<div>${esc(when)}</div><button class="bg-[#f84464] text-white px-3 py-1.5 rounded-lg">Select</button>`;
      row.querySelector("button").onclick = ()=>pickShow(s);
      shList.appendChild(row);
    });
  }catch{
    shList.innerHTML = `<div class="text-zinc-500">Network error.</div>`;
  }
}

async function pickShow(s){
  selectedShow = s; selectedSeats.clear(); setPayEnabled();
  bookMsg.textContent = "";
  seatsBox.innerHTML = `<div class="text-zinc-500">Loading seats...</div>`;
  try{
    const r = await http(`/api/cinema/shows/${s.id}/seats/`);
    if (!r.ok){ seatsBox.innerHTML = `<div class="text-zinc-500">Failed to load seats.</div>`; return; }
    const items = await r.json(); // [{number, available}]
    seatMap = (Array.isArray(items) ? items : []).slice().sort((a,b)=>(Number(a.number||0) - Number(b.number||0)));
    renderSeatsGrid();
  }catch{
    seatsBox.innerHTML = `<div class="text-zinc-500">Network error.</div>`;
  }
}

// ===== Pay: create bookings for selected seats =====
payBtn.onclick = async () => {
  if (!isLoggedIn()) { alert("Please sign in first."); return; }
  if (!selectedShow || selectedSeats.size === 0) return;
  if (selectedSeats.size > 6) { alert("Maximum 6 seats allowed."); return; }

  const numbers = Array.from(selectedSeats);
  bookMsg.textContent = `Booking ${numbers.length} seat(s)...`;
  payBtn.disabled = true;

  let okCount = 0, conflicts = 0, failures = 0, lastErr = "";
  for (const num of numbers){
    const r = await http(`/api/cinema/bookings/`, {
      method:"POST",
      body: JSON.stringify({ show_id: selectedShow.id, seat_number: num })
    });
    if (r.status === 409) { conflicts++; continue; }
    if (r.ok) { okCount++; }
    else { failures++; try{ lastErr = (await r.text()) || `HTTP ${r.status}`; }catch{} }
  }

  await pickShow(selectedShow);   // refresh availability
  selectedSeats.clear();
  setPayEnabled();
  await loadHistory();            // refresh history after booking

  const out = [];
  if (okCount) out.push(`Confirmed: ${okCount}`);
  if (conflicts) out.push(`Already taken: ${conflicts}`);
  if (failures) out.push(`Failed: ${failures}${lastErr ? " ("+lastErr+")" : ""}`);
  bookMsg.textContent = out.join(" • ") || "No changes";
};

// ===== Booking history =====
async function loadHistory(){
  historyBox.innerHTML = `<div class="text-zinc-500">Loading...</div>`;
  try{
    const r = await http(`/api/cinema/my-bookings/`);
    if (!r.ok){ historyBox.innerHTML = `<div class="text-zinc-500">Failed (login required)</div>`; return; }
    const items = await r.json();
    if (!Array.isArray(items) || !items.length){
      historyBox.innerHTML = `<div class="text-zinc-500">No bookings yet.</div>`;
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "grid md:grid-cols-2 gap-3";
    items.forEach(b=>{
      const when = b.show_start_time ? new Date(b.show_start_time).toLocaleString() : (b.show_id ? `Show #${b.show_id}` : "Show");
      const title = b.movie_title || "Movie";
      const seat  = b.seat_number != null ? b.seat_number : "";
      const card = document.createElement("div");
      card.className = "border rounded-lg p-3 bg-zinc-50";
      card.innerHTML = `
        <div class="font-semibold">Booking #${esc(b.id)}</div>
        <div class="text-sm text-zinc-700">${esc(title)}</div>
        <div class="text-sm text-zinc-600">${esc(when)}</div>
        <div class="text-sm text-zinc-600">Seat: ${esc(seat)}</div>
      `;
      wrap.appendChild(card);
    });
    historyBox.innerHTML = "";
    historyBox.appendChild(wrap);
  }catch{
    historyBox.innerHTML = `<div class="text-zinc-500">Network error.</div>`;
  }
}

// ===== seed carousels and auth badge on load =====
(async function init(){
  await fetchMe(); // will set navbar if tokens exist
  setPayEnabled();

  try{
    const r = await http("/api/cinema/movies/");
    if (r.ok){
      const items = await r.json();
      rec.innerHTML = ""; pre.innerHTML = "";
      items.slice(0,10).forEach(m=>rec.appendChild(movieCard(m)));
      items.slice(-10).reverse().forEach(m=>pre.appendChild(movieCard(m)));
    }
  }catch{}
})();
