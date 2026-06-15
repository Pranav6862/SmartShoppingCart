/* ============================================================
   SmartCart AI Dashboard — JavaScript
   Senior UI/UX Implementation
   ============================================================ */

/* ── App State ────────────────────────────────────────────── */
const S = {
  socket        : null,
  running       : false,
  paused        : false,
  source        : "webcam",
  uploadedPath  : null,
  uploadedName  : null,
  scanCount     : 0,
  allProducts   : [],
  robotData     : null,
  moveLog       : [],
  lastDir       : "idle",
  qsOpen        : false,
  robotOpen     : true,
};

/* ── Direction Config ─────────────────────────────────────── */
const DIR = {
  following : { arrow:"TRACK", label:"FOLLOWING", sub:"Actively tracking customer", cls:"following" },
  forward   : { arrow:"UP",    label:"FORWARD",   sub:"Moving towards customer",    cls:"following" },
  backward  : { arrow:"DOWN",  label:"BACK",      sub:"Reversing",                  cls:"idle" },
  left      : { arrow:"LEFT",  label:"LEFT",      sub:"Steering left",              cls:"following" },
  right     : { arrow:"RIGHT", label:"RIGHT",     sub:"Steering right",             cls:"following" },
  idle      : { arrow:"IDLE",  label:"IDLE",      sub:"Standing by",                cls:"idle" },
  obstacle  : { arrow:"STOP",  label:"BLOCKED",   sub:"Path blocked - stopped",     cls:"obstacle" },
};

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initSocket();
  initDropZone();
  clockTick();
  setInterval(clockTick, 1000);
  loadProducts();
});

/* ── Clock ────────────────────────────────────────────────── */
function clockTick() {
  const t = new Date().toTimeString().split(" ")[0];
  setText("navClock", t);
}

/* ═══════════════════════════════════════════════════════════ */
/* SOCKET.IO                                                  */
/* ═══════════════════════════════════════════════════════════ */
function initSocket() {
  S.socket = io({ transports: ["websocket"] });

  S.socket.on("connect", () => {
    console.log("Socket connected");
  });

  S.socket.on("disconnect", () => {
    setPillOffline();
  });

  S.socket.on("status_update", d => {
    updateSystemStatus(d);
    if (d.robot) {
      updateRobotStatus(d.robot);
      updateFollowingCard(d.robot);
    }
  });

  S.socket.on("cart_update", d => {
    renderCart(d);
  });

  S.socket.on("scan_result", d => {
    S.scanCount++;
    setText("smScans", S.scanCount);
    triggerScanFlash(d.success);
    toast(
      d.success ? "success" : "error",
      d.success ? "Item Added" : "Not Found",
      d.message
    );
  });

  S.socket.on("checkout_complete", d => {
    showCheckoutModal(d);
  });
}

/* ═══════════════════════════════════════════════════════════ */
/* SYSTEM STATUS                                              */
/* ═══════════════════════════════════════════════════════════ */
function updateSystemStatus(d) {
  S.running = d.is_running;
  S.paused  = d.is_paused;

  /* Status pill */
  const pill = document.getElementById("statusPill");
  const dot  = document.getElementById("statusDot");
  const lbl  = document.getElementById("statusLabel");

  if (d.is_running && !d.is_paused) {
    pill.className    = "status-pill online";
    dot.style.background = "var(--green-500)";
    lbl.textContent   = "System Live";
  } else if (d.is_paused) {
    pill.className    = "status-pill paused";
    dot.style.background = "var(--amber-500)";
    lbl.textContent   = "Paused";
  } else {
    pill.className    = "status-pill";
    lbl.textContent   = "System Offline";
  }

  /* Nav stats */
  setText("navFps",    `${d.fps} FPS`);
  setText("navFrames", `Frame ${d.frame_count}`);
  setText("navPeople", `People ${d.people_count}`);
  setText("videoFps",  `${d.fps} FPS`);

  /* Video badges */
  const lb = document.getElementById("liveBadge");
  if (lb) {
    lb.textContent = d.is_running
      ? (d.source_mode === "webcam" ? "Live" : "Video")
      : "Offline";
  }

  const tb = document.getElementById("trackBadge");
  if (tb) {
    if (d.tracker_locked) {
      tb.textContent = `Customer #${d.tracker_id}`;
      tb.className   = "vchip vchip-track locked";
    } else {
      tb.textContent = "NO LOCK";
      tb.className   = "vchip vchip-track";
    }
  }

  const sb = document.getElementById("scanBadge");
  if (sb) {
    sb.textContent = d.scan_ready
      ? "● READY"
      : `⏳ ${d.scan_cooldown}s`;
    sb.className = `vchip vchip-scan ${d.scan_ready ? "ready" : ""}`;
  }

  setText("peopleBadge", `People ${d.people_count}`);

  /* Tracker pill */
  const tp = document.getElementById("trackerPill");
  if (tp) {
    if (d.tracker_locked) {
      tp.className = "status-pill online";
      setText("trackerPillLabel", `Tracking #${d.tracker_id}`);
    } else {
      tp.className = "status-pill";
      setText("trackerPillLabel", "No Target");
    }
  }

  /* Pause overlay + button */
  show("pauseOverlay", d.is_paused);
  const bp = document.getElementById("btnPause");
  if (bp) bp.textContent = d.is_paused ? "Resume" : "Pause";
}

function setPillOffline() {
  const pill = document.getElementById("statusPill");
  if (pill) pill.className = "status-pill";
  setText("statusLabel", "System Offline");
}

/* ═══════════════════════════════════════════════════════════ */
/* ROBOT STATUS STRIP                                         */
/* ═══════════════════════════════════════════════════════════ */
function updateRobotStatus(r) {
  S.robotData = r;

  /* Mode badge */
  const mode = document.getElementById("rshMode");
  if (mode) {
    if (!r.is_active) {
      mode.textContent = "OFFLINE";
      mode.className   = "rsh-mode";
    } else if (r.following_customer) {
      mode.textContent = "FOLLOWING";
      mode.className   = "rsh-mode following";
    } else {
      mode.textContent = "IDLE";
      mode.className   = "rsh-mode idle";
    }
  }

  /* Robot pill in navbar */
  const rp = document.getElementById("robotPill");
  if (rp) {
    if (r.following_customer) {
      rp.className = "status-pill online";
      setText("robotPillLabel", "Following Customer");
    } else if (r.is_active) {
      rp.className = "status-pill";
      setText("robotPillLabel", "Follow Ready");
    } else {
      rp.className = "status-pill";
      setText("robotPillLabel", "Follow Idle");
    }
  }

  /* Determine direction */
  let dir = r.direction || "idle";
  if (r.sensors && r.sensors.obstacle) dir = "obstacle";
  const cfg = DIR[dir] || DIR.idle;

  /* Direction cell */
  const dc = document.getElementById("rsDirCell");
  if (dc) {
    dc.className = `rs-cell direction-cell ${cfg.cls}`;
  }
  setText("rsDirArrow", cfg.arrow);
  setText("rsDirText",  cfg.label);

  /* Speed + Motors */
  setText("rsRpm",    r.motors.rpm.toFixed(0));
  setText("rsMotors",
    `${Math.abs(r.motors.left).toFixed(0)}% / ${Math.abs(r.motors.right).toFixed(0)}%`
  );
  setText("rsMoving", r.is_moving ? "Running" : "Stopped");

  /* Battery */
  const bPct  = r.power.battery;
  const bBar  = document.getElementById("rsBattBar");
  const bText = document.getElementById("rsBatt");

  if (bText) {
    bText.textContent = `${bPct.toFixed(0)}%`;
    bText.className   = `rs-value ${bPct > 50 ? "green" : bPct > 20 ? "amber" : "red"}`;
  }
  if (bBar) {
    bBar.style.width    = bPct + "%";
    bBar.className      = `batt-bar-fill ${bPct > 50 ? "high" : bPct > 20 ? "medium" : "low"}`;
  }

  /* Sensor */
  const front   = r.sensors.front;
  const frontFmt = front > 990 ? "--" : front.toFixed(0);
  setText("rsFront", `${frontFmt} cm`);

  /* Sensor bar segments */
  const danger   = front < 30;
  const close    = front < 80;
  const segments = [
    { id:"ss1", active: true },
    { id:"ss2", active: front < 900 },
    { id:"ss3", active: front < 200 },
    { id:"ss4", active: close },
    { id:"ss5", active: danger },
  ];
  segments.forEach(s => {
    const el = document.getElementById(s.id);
    if (!el) return;
    const cls = danger ? "red" : close ? "amber" : "green";
    el.className = `sensor-seg ${s.active ? `active ${cls}` : ""}`;
  });

  /* Distance */
  setText("rsDistance", r.navigation.distance.toFixed(3));

  /* Log direction change */
  if (dir !== S.lastDir) {
    addMoveLog(dir, cfg, r);
    S.lastDir = dir;
  }

  updateAlertBanner(r);
  drawRadar(r);
  drawAiOverlay(r);
}

/* ═══════════════════════════════════════════════════════════ */
/* FOLLOWING CARD                                             */
/* ═══════════════════════════════════════════════════════════ */
function updateFollowingCard(r) {
  let dir = r.direction || "idle";
  if (r.sensors && r.sensors.obstacle) dir = "obstacle";
  const cfg = DIR[dir] || DIR.idle;

  /* Direction box */
  const box = document.getElementById("rfcDirBox");
  if (box) box.className = `rfc-dir ${cfg.cls}`;

  setText("rfcArrow",    cfg.arrow);
  setText("rfcDirLabel", cfg.label);

  /* Target */
  if (r.following_customer) {
    setText("rfcTarget", `Customer Locked`);
    const tv = document.getElementById("rfcTarget");
    if (tv) tv.className = "rfc-stat-value green";
    setText("rfcStatus", cfg.sub);
  } else {
    setText("rfcTarget", "None");
    const tv = document.getElementById("rfcTarget");
    if (tv) tv.className = "rfc-stat-value";
    setText("rfcStatus", "Not tracking");
  }

  /* Proximity */
  const front = r.sensors.front;
  const fmtFront = front > 990
    ? "No target"
    : `${front.toFixed(0)} cm`;

  setText("rfcProx", fmtFront);

  const pv = document.getElementById("rfcProx");
  if (pv) {
    pv.className = front < 30
      ? "rfc-stat-value red"
      : front < 80
      ? "rfc-stat-value amber"
      : "rfc-stat-value green";
  }
  setText("rfcProxSub",
    front < 30 ? "Too close" :
    front < 80 ? "Approaching" : "Safe distance"
  );

  /* Heading */
  setText("rfcHeading", `${r.navigation.heading.toFixed(1)}°`);
  const compass = getCompassDir(r.navigation.heading);
  setText("rfcHeadingSub", compass);
}

function getCompassDir(deg) {
  const dirs = ["N","NE","E","SE","S","SW","W","NW","N"];
  return dirs[Math.round(deg / 45) % 8];
}

/* ═══════════════════════════════════════════════════════════ */
/* MOVEMENT LOG                                               */
/* ═══════════════════════════════════════════════════════════ */
function addMoveLog(dir, cfg, r) {
  const now = new Date().toTimeString().split(" ")[0];
  S.moveLog.unshift({ time: now, dir, cfg, r: { ...r } });
  if (S.moveLog.length > 8) S.moveLog.pop();
  renderMoveLog();
}

function renderMoveLog() {
  const list = document.getElementById("mlList");
  if (!list) return;

  list.innerHTML = S.moveLog.map((e, i) => {
    const cls = e.dir === "following" ? "following"
              : e.dir === "obstacle"  ? "obstacle"
              : e.dir === "idle"      ? "idle"
              : "turning";
    return `
      <div class="ml-entry" style="opacity:${1 - i * 0.1}">
        <span class="ml-time">${e.time}</span>
        <span class="ml-icon">${e.cfg.arrow}</span>
        <span class="ml-desc">${e.cfg.sub}</span>
        <span class="ml-badge ${cls}">${e.cfg.label}</span>
      </div>
    `;
  }).join("");
}

/* ═══════════════════════════════════════════════════════════ */
/* CART RENDERING                                             */
/* ═══════════════════════════════════════════════════════════ */
function renderCart(d) {
  const curr = d.currency || "$";

  /* Session meta */
  setText("smSession",  d.session_id || "--");
  setText("smCustomer", d.customer   || "--");

  /* Badge */
  const cnt = d.item_count || 0;
  setText("cartBadge", `${cnt} item${cnt !== 1 ? "s" : ""}`);

  /* Totals */
  setText("tSubtotal", `${curr}${fmt(d.subtotal)}`);
  setText("tTax",      `${curr}${fmt(d.tax)}`);
  setText("tTotal",    `${curr}${fmt(d.total)}`);
  setText("tTaxLabel", `Tax (${d.tax_rate || "8%"})`);
  setText("videoTotal",`Cart: ${curr}${fmt(d.total)}`);

  /* Items */
  const list   = document.getElementById("cartList");
  const empty  = document.getElementById("emptyState");
  if (!list) return;

  const items = d.items || [];

  if (items.length === 0) {
    list.innerHTML = "";
    const e = (empty || createEmpty()).cloneNode(true);
    e.id = "emptyState";
    e.classList.remove("hidden");
    list.appendChild(e);
    return;
  }

  /* Remove empty state */
  const ex = document.getElementById("emptyState");
  if (ex && ex.parentNode === list) ex.remove();

  /* Track existing rows */
  const existing = {};
  list.querySelectorAll(".cart-row[data-bc]").forEach(el => {
    existing[el.dataset.bc] = el;
  });

  const barcodes = new Set(items.map(i => i.barcode));

  /* Remove deleted */
  Object.keys(existing).forEach(bc => {
    if (!barcodes.has(bc)) {
      existing[bc].style.animation = "none";
      existing[bc].style.opacity   = "0";
      existing[bc].style.transform = "translateX(20px)";
      existing[bc].style.transition = "all 0.2s ease";
      setTimeout(() => existing[bc].remove(), 200);
    }
  });

  /* Update or create */
  items.forEach(item => {
    const bc = item.barcode;
    if (existing[bc]) {
      /* Update in place */
      existing[bc].querySelector(".cr-qty").textContent   = item.quantity;
      existing[bc].querySelector(".cr-price").textContent = `${curr}${fmt(item.price)}`;
      existing[bc].querySelector(".cr-total").textContent = `${curr}${fmt(item.total_price)}`;
      /* Flash */
      existing[bc].classList.add("flash");
      setTimeout(() => existing[bc].classList.remove("flash"), 600);
    } else {
      /* Create new row */
      const row = document.createElement("div");
      row.className    = "cart-row";
      row.dataset.bc   = bc;
      row.innerHTML    = rowHTML(item, curr);
      list.appendChild(row);
    }
  });
}

function rowHTML(item, curr) {
  const name  = escapeHtml((item.name  || "").slice(0, 20));
  const brand = escapeHtml((item.brand || "").slice(0, 14));
  const bc    = escapeHtml(item.barcode);
  return `
    <div class="cart-item-name-wrap">
      <div class="cc-img">Item</div>
      <div class="cr-info">
        <div class="cr-name"  title="${escapeHtml(item.name || "")}">${name}</div>
        <div class="cr-brand">${brand}</div>
      </div>
    </div>
    <div class="cr-qty">${item.quantity}</div>
    <div class="cr-price">${curr}${fmt(item.price)}</div>
    <div class="cr-total">${curr}${fmt(item.total_price)}</div>
    <div class="cr-actions">
      <button class="cr-btn inc"
              onclick="cartAction('increment','${bc}')"
              title="Add one">+</button>
      <button class="cr-btn dec"
              onclick="cartAction('decrement','${bc}')"
              title="Remove one">−</button>
      <button class="cr-btn del"
              onclick="cartAction('remove','${bc}')"
              title="Remove all">×</button>
    </div>
  `;
}

function createEmpty() {
  const d = document.createElement("div");
  d.className = "empty-state";
  d.id        = "emptyState";
  d.innerHTML = `
    <div class="es-icon">Cart</div>
    <div class="es-title">Cart is empty</div>
    <div class="es-sub">Start the session and scan a product</div>
  `;
  return d;
}

/* ═══════════════════════════════════════════════════════════ */
/* SESSION CONTROL                                            */
/* ═══════════════════════════════════════════════════════════ */
function setSource(mode) {
  S.source = mode;
  document.getElementById("srcWebcam")
    .classList.toggle("selected", mode === "webcam");
  document.getElementById("srcVideo")
    .classList.toggle("selected", mode === "video");
  show("uploadArea", mode === "video");
}

async function startSession() {
  const name = document.getElementById("customerInput")?.value?.trim()
             || "Customer";

  if (S.source === "video" && !S.uploadedPath) {
    toast("warning", "No Video", "Please upload a video file first.");
    return;
  }

  const btn = document.getElementById("btnStart");
  if (btn) { btn.textContent = "Starting..."; btn.disabled = true; }

  try {
    const res  = await post("/api/start", {
      mode      : S.source,
      customer  : name,
      video_path: S.uploadedPath
    });
    const data = await res.json();

    if (data.success) {
      S.running   = true;
      S.scanCount = 0;

      /* Hide overlay */
      show("startupOverlay", false);

      setText("smSession",  data.session_id || "--");
      setText("smCustomer", data.customer   || "--");

      toast("success", "Session Started",
        `${data.mode === "webcam" ? "Webcam" : "Video file"} source active`);
    } else {
      toast("error", "Failed to Start", data.message || "Unknown error");
      if (btn) { btn.textContent = "Start SmartCart Session"; btn.disabled = false; }
    }
  } catch (e) {
    toast("error", "Connection Error", "Could not reach server.");
    if (btn) { btn.textContent = "Start SmartCart Session"; btn.disabled = false; }
  }
}

async function stopSession() {
  if (!confirm("Stop the current session?")) return;

  await fetch("/api/stop", { method: "POST" });

  S.running      = false;
  S.paused       = false;
  S.uploadedPath = null;
  S.scanCount    = 0;
  S.moveLog      = [];
  S.lastDir      = "idle";

  /* Show startup overlay again */
  show("startupOverlay", true);

  /* Reset btn */
  const btn = document.getElementById("btnStart");
  if (btn) { btn.textContent = "Start SmartCart Session"; btn.disabled = false; }

  setPillOffline();
  toast("info", "Session Stopped", "Start a new session when ready.");
}

async function togglePause() {
  const res  = await fetch("/api/pause", { method: "POST" });
  const data = await res.json();
  S.paused   = data.paused;
  toast("info",
    data.paused ? "Paused" : "Resumed",
    data.paused ? "Video stream paused." : "Video stream resumed."
  );
}

/* ═══════════════════════════════════════════════════════════ */
/* CART ACTIONS                                               */
/* ═══════════════════════════════════════════════════════════ */
async function cartAction(action, barcode) {
  const res  = await post(`/api/cart/${action}`, { barcode });
  const data = await res.json();
  /* Cart update comes via socket */
  if (!data.success) {
    toast("error", "Action Failed", data.message || "");
  }
}

async function quickScan(barcode) {
  if (!S.running) {
    toast("warning", "Not Running", "Start a session first.");
    return;
  }
  const res  = await post("/api/scan", { barcode });
  const data = await res.json();

  if (!data.success) {
    toast("error", "Scan Failed", data.message);
  }
}

async function undoAction() {
  const res  = await fetch("/api/cart/undo", { method: "POST" });
  const data = await res.json();
  toast(
    data.success ? "info" : "error",
    data.success ? "Undone"  : "Cannot Undo",
    data.message || ""
  );
}

async function confirmClear() {
  if (!confirm("Clear all items from the cart?")) return;
  await fetch("/api/cart/clear", { method: "POST" });
  toast("info", "Cart Cleared", "All items removed.");
}

async function doCheckout() {
  if (!S.running) {
    toast("warning", "Not Running", "Start a session first.");
    return;
  }
  const cart = await (await fetch("/api/cart")).json();
  if (!cart || cart.item_count === 0) {
    toast("warning", "Empty Cart", "Add items before checking out.");
    return;
  }
  const res  = await fetch("/api/cart/checkout", { method: "POST" });
  const data = await res.json();

  if (data.success) showCheckoutModal(data);
  else toast("error", "Checkout Failed", data.message || "");
}

/* ═══════════════════════════════════════════════════════════ */
/* TRACKER                                                    */
/* ═══════════════════════════════════════════════════════════ */
async function lockCustomer() {
  const res  = await fetch("/api/tracker/lock",   { method: "POST" });
  const data = await res.json();
  toast(
    data.success ? "success" : "warning",
    data.success ? "Customer Locked" : "No Person Found",
    data.message || ""
  );
}

async function unlockCustomer() {
  await fetch("/api/tracker/unlock", { method: "POST" });
  toast("info", "Unlocked", "Customer tracking released.");
}

async function switchCustomer() {
  await fetch("/api/tracker/switch", { method: "POST" });
  toast("info", "Switched", "Tracking next detected person.");
}

/* ═══════════════════════════════════════════════════════════ */
/* FILE UPLOAD                                                */
/* ═══════════════════════════════════════════════════════════ */
function initDropZone() {
  const dz = document.getElementById("dropZone");
  if (!dz) return;

  dz.addEventListener("dragover", e => {
    e.preventDefault();
    dz.classList.add("dragover");
  });
  dz.addEventListener("dragleave", () => {
    dz.classList.remove("dragover");
  });
  dz.addEventListener("drop", e => {
    e.preventDefault();
    dz.classList.remove("dragover");
    const f = e.dataTransfer.files[0];
    if (f) uploadFile(f);
  });
}

function onFileSelect(e) {
  const f = e.target.files[0];
  if (f) uploadFile(f);
}

async function uploadFile(file) {
  show("uploadBar",     true);
  show("uploadSuccess", false);

  const fill = document.getElementById("ubarFill");
  const uTxt = document.getElementById("ubarText");
  let prog    = 0;

  const iv = setInterval(() => {
    prog = Math.min(prog + 6, 88);
    if (fill) fill.style.width = prog + "%";
    if (uTxt) uTxt.textContent = `Uploading… ${prog}%`;
  }, 100);

  const fd = new FormData();
  fd.append("video", file);

  try {
    const res  = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await res.json();
    clearInterval(iv);

    if (data.success) {
      if (fill) fill.style.width = "100%";
      S.uploadedPath = data.path;
      setTimeout(() => {
        show("uploadBar",     false);
        show("uploadSuccess", true);
        setText("uploadedName", data.filename);
        toast("success", "Uploaded", data.filename);
      }, 400);
    } else {
      if (uTxt) uTxt.textContent = "Upload failed: " + data.message;
    }
  } catch {
    clearInterval(iv);
    if (uTxt) uTxt.textContent = "Upload error";
  }
}

/* ═══════════════════════════════════════════════════════════ */
/* PRODUCTS                                                   */
/* ═══════════════════════════════════════════════════════════ */
async function loadProducts() {
  try {
    const res  = await fetch("/api/products");
    const data = await res.json();
    if (data.success) {
      S.allProducts = data.products;
      renderProducts(data.products);
    }
  } catch (e) { console.log("Products:", e); }
}

function openProducts() {
  show("productsModal", true);
  const inp = document.getElementById("prodSearch");
  if (inp) { inp.value = ""; inp.focus(); }
  filterProducts();
}

function closeProducts() {
  show("productsModal", false);
}

function filterProducts() {
  const q = (document.getElementById("prodSearch")?.value || "").toLowerCase();
  const f = q
    ? S.allProducts.filter(p =>
        (p.name     || "").toLowerCase().includes(q) ||
        (p.brand    || "").toLowerCase().includes(q) ||
        (p.category || "").toLowerCase().includes(q) ||
        (p.barcode  || "").includes(q)
      )
    : S.allProducts;
  renderProducts(f);
}

function renderProducts(prods) {
  const list = document.getElementById("prodList");
  if (!list) return;

  if (!prods || prods.length === 0) {
    list.innerHTML = `
      <div style="text-align:center;padding:40px;color:#94a3b8">
        No products found
      </div>`;
    return;
  }

  list.innerHTML = prods.map(p => `
    <div style="
      display:grid;
      grid-template-columns:140px 1fr 100px 80px 72px;
      align-items:center; gap:8px;
      padding:10px 12px;
      border:1px solid var(--border);
      border-radius:8px; margin-bottom:4px;
      transition:all 0.15s;
      cursor:pointer;
    "
    onmouseover="this.style.background='var(--gray-50)'"
    onmouseout="this.style.background=''"
    onclick="quickScanFromProduct('${escapeHtml(p.barcode)}')">
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--gray-400)">
        ${escapeHtml(p.barcode)}
      </span>
      <div>
        <div style="font-size:13px;font-weight:600;color:var(--text-primary)">
          ${escapeHtml(p.name || "")}
        </div>
        <div style="font-size:11px;color:var(--text-muted)">
          ${escapeHtml(p.brand || "")} · ${escapeHtml(p.category || "")}
        </div>
      </div>
      <span style="font-size:11px;color:var(--text-secondary)">
        ${escapeHtml(p.unit || "")}
      </span>
      <span style="font-family:var(--font-mono);font-size:13px;
                   font-weight:700;color:var(--success)">
        $${fmt(p.price)}
      </span>
      <button
        onclick="event.stopPropagation();quickScanFromProduct('${escapeHtml(p.barcode)}')"
        style="
          padding:5px 10px; border-radius:6px;
          border:1px solid var(--indigo-100);
          background:var(--indigo-50); color:var(--accent);
          font-size:11px; font-weight:700; cursor:pointer;
          transition:all 0.15s; font-family:var(--font);
        "
        onmouseover="this.style.background='var(--indigo-100)'"
        onmouseout="this.style.background='var(--indigo-50)'"
      >
        Add
      </button>
    </div>
  `).join("");
}

async function quickScanFromProduct(barcode) {
  closeProducts();
  await quickScan(barcode);
}

/* ═══════════════════════════════════════════════════════════ */
/* SCAN FLASH                                                 */
/* ═══════════════════════════════════════════════════════════ */
function triggerScanFlash(success) {
  const el = document.getElementById("scanFlash");
  if (!el) return;
  el.style.background = success
    ? "rgba(16,185,129,0.15)"
    : "rgba(239,68,68,0.12)";
  el.classList.add("active");
  setTimeout(() => el.classList.remove("active"), 800);
}

/* ═══════════════════════════════════════════════════════════ */
/* CHECKOUT MODAL                                             */
/* ═══════════════════════════════════════════════════════════ */
function showCheckoutModal(data) {
  const r    = data.receipt || {};
  const t    = data.totals  || {};
  const curr = t.currency   || "$";

  setText("modalReceipt", r.text || "Checkout complete!");
  setText("modalTotal",   `${curr}${fmt(t.total)}`);
  show("checkoutModal", true);
}

function closeCheckout() {
  show("checkoutModal", false);
  stopSession();
}

/* ═══════════════════════════════════════════════════════════ */
/* ROBOT STRIP TOGGLE                                         */
/* ═══════════════════════════════════════════════════════════ */
function toggleRobotStrip() {
  S.robotOpen = !S.robotOpen;
  const body   = document.getElementById("robotStripBody");
  const toggle = document.getElementById("rshToggle");
  if (body)   body.style.display   = S.robotOpen ? "" : "none";
  if (toggle) toggle.className     = `rsh-toggle ${S.robotOpen ? "open" : ""}`;
}

/* ═══════════════════════════════════════════════════════════ */
/* QUICK SCAN TOGGLE                                          */
/* ═══════════════════════════════════════════════════════════ */
function toggleQS() {
  S.qsOpen = !S.qsOpen;
  const body = document.getElementById("qsBody");
  const btn  = document.getElementById("qsToggleBtn");
  if (body) body.classList.toggle("open", S.qsOpen);
  if (btn)  btn.textContent = S.qsOpen ? "Hide ▲" : "Show ▼";
}

/* ═══════════════════════════════════════════════════════════ */
/* TOAST SYSTEM                                               */
/* ═══════════════════════════════════════════════════════════ */
const TOAST_ICONS = {
  success : "OK",
  error   : "!",
  warning : "!",
  info    : "i",
};

function toast(type, title, message = "") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const el       = document.createElement("div");
  el.className   = `toast ${type}`;
  el.innerHTML   = `
    <span class="toast-icon">${TOAST_ICONS[type] || "•"}</span>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-msg">${message}</div>` : ""}
    </div>
  `;

  container.appendChild(el);

  /* Auto remove */
  setTimeout(() => {
    el.style.transition = "all 0.3s ease";
    el.style.opacity    = "0";
    el.style.transform  = "translateX(20px)";
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

/* ═══════════════════════════════════════════════════════════ */
/* UTILITIES                                                  */
/* ═══════════════════════════════════════════════════════════ */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function show(id, visible) {
  const el = typeof id === "string"
    ? document.getElementById(id)
    : id;
  if (!el) return;
  if (visible) el.classList.remove("hidden");
  else         el.classList.add("hidden");
}

function fmt(n) {
  return (n || 0).toFixed(2);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[ch]));
}

function post(url, body) {
  return fetch(url, {
    method  : "POST",
    headers : { "Content-Type": "application/json" },
    body    : JSON.stringify(body),
  });
}

/* ═══════════════════════════════════════════════════════════ */
/* UI/UX ENHANCEMENTS                                         */
/* ═══════════════════════════════════════════════════════════ */

/* 1. Critical Alert Banner */
function updateAlertBanner(r) {
  const banner = document.getElementById("criticalAlert");
  const title = document.getElementById("caTitle");
  const sub = document.getElementById("caSub");
  
  if (!banner) return;

  if (r.sensors && r.sensors.obstacle) {
    banner.className = "critical-alert-banner danger";
    title.textContent = "Obstacle Detected";
    sub.textContent = "Path blocked. Please clear the area immediately.";
  } else if (r.power && r.power.battery < 15) {
    banner.className = "critical-alert-banner";
    title.textContent = "Low Battery Warning";
    sub.textContent = `Battery is at ${r.power.battery.toFixed(0)}%. Return to charging station soon.`;
  } else {
    banner.className = "critical-alert-banner hidden";
  }
}

/* 2. Radar Canvas View */
function drawRadar(r) {
  const canvas = document.getElementById("radarCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  const cx = W / 2;
  const cy = H / 2;
  const R = W / 2 - 4;

  ctx.clearRect(0, 0, W, H);

  // Background Rings
  ctx.strokeStyle = "rgba(0,0,0,0.05)";
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, R * 0.66, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, R * 0.33, 0, Math.PI * 2); ctx.stroke();

  // Radar Sweep effect (fake sweep using time)
  const time = Date.now() / 1000;
  const sweepAngle = (time * Math.PI) % (Math.PI * 2);
  
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(sweepAngle);
  const grad = ctx.createLinearGradient(0, 0, R, 0);
  grad.addColorStop(0, "rgba(99, 102, 241, 0.5)"); // Indigo
  grad.addColorStop(1, "rgba(99, 102, 241, 0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.arc(0, 0, R, 0, Math.PI / 4);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // Heading Arrow
  const headRad = (r.navigation.heading - 90) * Math.PI / 180;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(headRad);
  ctx.fillStyle = "var(--accent)";
  ctx.beginPath();
  ctx.moveTo(0, -R * 0.8);
  ctx.lineTo(6, 0);
  ctx.lineTo(-6, 0);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // Obstacle Dot (if < 100cm, draw it on the heading arc)
  if (r.sensors && r.sensors.front < 100) {
    const distRatio = Math.max(0.1, r.sensors.front / 100);
    const ox = cx + Math.cos(headRad) * (R * distRatio);
    const oy = cy + Math.sin(headRad) * (R * distRatio);
    
    ctx.fillStyle = "var(--danger)";
    ctx.beginPath();
    ctx.arc(ox, oy, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

/* 3. AI Canvas Overlay */
function drawAiOverlay(r) {
  const canvas = document.getElementById("aiOverlay");
  const img = document.getElementById("videoFeed");
  if (!canvas || !img) return;

  // Sync canvas size to image display size
  canvas.width = img.clientWidth;
  canvas.height = img.clientHeight;
  const ctx = canvas.getContext("2d");
  
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (r.following_customer) {
    // Draw mock bounding box in center to represent locked customer
    const bw = 120;
    const bh = 240;
    const bx = (canvas.width - bw) / 2;
    const by = (canvas.height - bh) / 2 + 20;

    ctx.strokeStyle = "var(--success)";
    ctx.lineWidth = 3;
    ctx.strokeRect(bx, by, bw, bh);

    ctx.fillStyle = "var(--success)";
    ctx.font = "bold 14px Inter";
    ctx.fillText("TARGET LOCKED", bx, by - 10);
  }
}

/* 4. Keyboard Hotkeys */
document.addEventListener("keydown", (e) => {
  // Ignore if typing in an input
  if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
  
  switch(e.key.toLowerCase()) {
    case " ":
      e.preventDefault(); // prevent scrolling
      togglePause();
      break;
    case "l":
      lockCustomer();
      break;
    case "c":
      doCheckout();
      break;
    case "escape":
      stopSession();
      break;
  }
});
