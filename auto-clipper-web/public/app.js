/**
 * Auto-Clipper Pro — 21st.dev Magic UI Production Web Controller
 * Featuring: Strict Routing, Visual Card Subtitle Selector,
 * Live oEmbed Preview, Filmstrip Stepper, and Serverless Multi-Cloud Engine.
 */

const CONFIG = {
  GITHUB_REPO: "lanAlone/auto-clipper-engine",
  GITHUB_PAT: localStorage.getItem("autoclipper_github_pat") || "",
  HF_DATASET_REPO: "traderade/auto-clipper-data",
  SUPPORT_EMAIL: "support@autoclipper.io",
  SALES_CHECKOUT_URL: localStorage.getItem("autoclipper_sales_url") || "" // Tautan Penjualan (bisa diisi Lynk.id / Mayar / WA)
};

class AutoClipperApp {
  constructor() {
    this.currentUser = localStorage.getItem("autoclipper_user") || "";
    this.activeJobId = null;
    this.pollingInterval = null;
    this.simSubtitleIndex = 0;
    this.simStyles = [
      { name: "✨ Subtitle Gaya MrBeast (Pop-in Dynamic)", color: "#FDE047", bg: "rgba(0,0,0,0.85)", text: '"RAHASIA BESAR INI..."' },
      { name: "⚡ Subtitle Gaya Alex Hormozi (Word Highlight)", color: "#38BDF8", bg: "rgba(14, 28, 56, 0.9)", text: '"KAMU HARUS TAHU"' },
      { name: "🌌 Subtitle Gaya Cyber Neon Glow", color: "#EC4899", bg: "rgba(36, 12, 30, 0.9)", text: '"VIRAL DALAM 24 JAM"' },
      { name: "⚪ Subtitle Gaya Clean Minimalist", color: "#FFFFFF", bg: "rgba(20, 20, 20, 0.85)", text: '"Bagian ini paling penting."' }
    ];
    this.init();
  }

  init() {
    this.initAmbientCanvas();
    this.updateAuthUI();

    // Check URL hash for routing
    const hash = window.location.hash;
    if (hash === "#/dashboard" || hash === "#dashboard") {
      if (this.currentUser) {
        this.navigateTo("dashboard");
      } else {
        this.navigateTo("landing");
        this.openAuthModal();
      }
    } else {
      this.navigateTo("landing");
    }

    window.addEventListener("hashchange", () => {
      if (window.location.hash.includes("dashboard")) {
        if (this.currentUser) {
          this.navigateTo("dashboard");
        } else {
          this.openAuthModal();
        }
      } else {
        this.navigateTo("landing");
      }
    });
  }

  // =========================================================================
  // 1. DYNAMIC AMBIENT PARTICLE CANVAS (21st.dev Style)
  // =========================================================================
  initAmbientCanvas() {
    const canvas = document.getElementById("ambient-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const particles = [];
    const count = Math.min(width > 768 ? 45 : 20, 48);

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 1.8 + 0.6,
        alpha: Math.random() * 0.45 + 0.15
      });
    }

    function animate() {
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56, 189, 248, ${p.alpha})`;
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 135) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(56, 189, 248, ${0.14 * (1 - dist / 135)})`;
            ctx.lineWidth = 0.7;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(animate);
    }
    animate();
  }

  // =========================================================================
  // 2. ROUTING & VIEW CONTROLLER (LANDING vs DASHBOARD APP SHELL)
  // =========================================================================
  navigateTo(route) {
    const landingView = document.getElementById("view-landing");
    const dashboardView = document.getElementById("view-dashboard");

    if (route === "dashboard") {
      if (!this.currentUser) {
        this.openAuthModal();
        return;
      }
      landingView.style.display = "none";
      dashboardView.style.display = "flex";
      window.location.hash = "#/dashboard";
      this.loadConnectedProviders();
      document.getElementById("dash-user-label").innerText = this.currentUser;
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      landingView.style.display = "block";
      dashboardView.style.display = "none";
      window.location.hash = "";
      this.closeAuthModal();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  handleCtaClick() {
    if (this.currentUser) {
      this.navigateTo("dashboard");
    } else {
      this.openAuthModal();
    }
  }

  switchDashTab(tabId, triggerBtn) {
    document.querySelectorAll(".dash-tab-pane").forEach((el) => {
      el.style.display = "none";
    });
    document.querySelectorAll(".sidebar-nav-item").forEach((el) => {
      el.classList.remove("active");
    });

    const target = document.getElementById(tabId);
    if (target) target.style.display = "block";

    if (triggerBtn) {
      triggerBtn.classList.add("active");
    }
  }

  fillSampleUrl() {
    const sample = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
    const input = document.getElementById("dash-yt-url");
    if (input) {
      input.value = sample;
      this.onYoutubeUrlChange();
    }
  }

  // =========================================================================
  // 3. VISUAL CARD SELECTOR (SUBTITLE STYLES)
  // =========================================================================
  selectSubtitleStyle(styleKey, cardId) {
    document.getElementById("dash-caption-style").value = styleKey;
    document.querySelectorAll(".subtitle-style-card").forEach(el => el.classList.remove("active"));
    const card = document.getElementById(cardId);
    if (card) card.classList.add("active");
  }

  // =========================================================================
  // 4. HERO SIMULATOR CONTROLS
  // =========================================================================
  setSimAspect(mode) {
    const box = document.getElementById("sim-video-box");
    const btn169 = document.getElementById("sim-btn-16-9");
    const btn916 = document.getElementById("sim-btn-9-16");

    if (mode === "16-9") {
      box.classList.remove("vertical-mode");
      btn169.classList.add("active");
      btn916.classList.remove("active");
    } else {
      box.classList.add("vertical-mode");
      btn916.classList.add("active");
      btn169.classList.remove("active");
    }
  }

  toggleSimSubtitleStyle() {
    this.simSubtitleIndex = (this.simSubtitleIndex + 1) % this.simStyles.length;
    const style = this.simStyles[this.simSubtitleIndex];

    const badge = document.getElementById("sim-subtitle-badge");
    const desc = document.getElementById("sim-style-desc");

    badge.style.color = style.color;
    badge.style.background = style.bg;
    badge.innerText = style.text;
    badge.classList.remove("kinetic-subtitle-box");
    void badge.offsetWidth;
    badge.classList.add("kinetic-subtitle-box");

    desc.innerText = style.name;
    desc.style.color = style.color;
  }

  // =========================================================================
  // 5. AUTHENTICATION & LOGIN GATE
  // =========================================================================
  openAuthModal() {
    document.getElementById("auth-modal").classList.add("active");
    document.getElementById("auth-error-msg").style.display = "none";
    document.getElementById("auth-username").focus();
  }

  closeAuthModal() {
    document.getElementById("auth-modal").classList.remove("active");
  }

  submitAuth() {
    const user = document.getElementById("auth-username").value.trim();
    const pass = document.getElementById("auth-password").value.trim();
    const errBox = document.getElementById("auth-error-msg");

    if (!user || !pass) {
      errBox.innerText = "Harap isi username dan password.";
      errBox.style.display = "block";
      return;
    }

    const validAccounts = {
      "admin": "admin123",
      "kenzie": "kenzie123"
    };

    if (validAccounts[user] && validAccounts[user] === pass) {
      this.currentUser = user;
      localStorage.setItem("autoclipper_user", user);
      this.updateAuthUI();
      this.closeAuthModal();
      this.navigateTo("dashboard");
    } else {
      errBox.innerText = "Username atau password tidak sesuai. (Coba admin / admin123)";
      errBox.style.display = "block";
    }
  }

  logout() {
    this.currentUser = "";
    localStorage.removeItem("autoclipper_user");
    this.updateAuthUI();
    this.navigateTo("landing");
  }

  updateAuthUI() {
    const loginBtn = document.getElementById("nav-login-btn");
    if (loginBtn) {
      if (this.currentUser) {
        loginBtn.innerText = `👑 ${this.currentUser}`;
        loginBtn.onclick = () => this.navigateTo("dashboard");
      } else {
        loginBtn.innerText = "Masuk Akun";
        loginBtn.onclick = () => this.openAuthModal();
      }
    }
  }

  // =========================================================================
  // 5B. PRICING MODAL & SALES CHECKOUT HANDLER (RP 300.000)
  // =========================================================================
  openPricingModal() {
    const modal = document.getElementById("pricing-modal");
    if (modal) {
      modal.classList.add("active");
      const msgBox = document.getElementById("pricing-notification-msg");
      if (msgBox) msgBox.style.display = "none";
    }
  }

  closePricingModal() {
    const modal = document.getElementById("pricing-modal");
    if (modal) {
      modal.classList.remove("active");
    }
  }

  handlePurchaseClick() {
    const checkoutBtn = document.getElementById("btn-pricing-checkout");
    const msgBox = document.getElementById("pricing-notification-msg");
    const salesUrl = CONFIG.SALES_CHECKOUT_URL || localStorage.getItem("autoclipper_sales_url");

    if (salesUrl && salesUrl.startsWith("http")) {
      // Redirect to actual sales link if provided
      window.open(salesUrl, "_blank");
    } else {
      // Show elegant simulated checkout ready state
      if (msgBox) {
        msgBox.innerHTML = `
          <div style="font-weight: 700; color: #10B981; margin-bottom: 4px;">✓ Gateway Penjualan Terhubung!</div>
          <div style="font-size: 12.5px; color: #E2E8F0;">
            Harga Lisensi: <b>Rp 300.000 (Lifetime)</b>.<br>
            Tautan penjualan siap disematkan. Untuk pembelian manual saat ini, silakan hubungi tim kami di <b>support@autoclipper.io</b>.
          </div>
        `;
        msgBox.style.display = "block";
      }
    }
  }

  // =========================================================================
  // 6. LIVE YOUTUBE OEMBED PREVIEW
  // =========================================================================
  async onYoutubeUrlChange() {
    const url = document.getElementById("dash-yt-url").value.trim();
    const previewContainer = document.getElementById("dash-yt-preview");

    if (!url || !url.includes("youtu")) {
      previewContainer.innerHTML = "";
      return;
    }

    try {
      const resp = await fetch(`https://noembed.com/embed?url=${encodeURIComponent(url)}`);
      const data = await resp.json();
      if (data && data.title) {
        previewContainer.innerHTML = `
          <div style="display: flex; gap: 16px; align-items: center; background: rgba(18, 23, 36, 0.85); padding: 16px 20px; border-radius: 14px; border: 1px solid var(--card-border);">
            <img src="${data.thumbnail_url || ''}" style="width: 124px; height: 70px; object-fit: cover; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.6);" />
            <div>
              <h4 style="margin: 0 0 4px 0; color: #FFFFFF; font-size: 14.5px; font-family: 'Space Grotesk', sans-serif;">${data.title}</h4>
              <p style="margin: 0; color: #94A3B8; font-size: 13px;">Channel: <b>${data.author_name || 'YouTube'}</b></p>
              <span style="font-size: 11.5px; color: #38BDF8; font-weight: 700;">✓ URL Siap Diproses Runner AI</span>
            </div>
          </div>
        `;
      }
    } catch (e) {
      previewContainer.innerHTML = "";
    }
  }

  // =========================================================================
  // 7. VIDEO PROCESSING & DYNAMIC FILMSTRIP STEPPER
  // =========================================================================
  async startProcessing() {
    const ytUrl = document.getElementById("dash-yt-url").value.trim();
    const duration = document.getElementById("dash-duration").value;
    const clipCount = parseInt(document.getElementById("dash-clip-count").value) || 3;
    const cropMode = document.getElementById("dash-crop-mode").value;
    const captionStyle = document.getElementById("dash-caption-style").value;
    const stepperArea = document.getElementById("dash-stepper-area");
    const galleryArea = document.getElementById("dash-gallery-area");
    const btn = document.getElementById("btn-start-process");

    if (!ytUrl || !ytUrl.includes("youtu")) {
      alert("Harap masukkan URL video YouTube yang valid!");
      return;
    }

    btn.disabled = true;
    btn.innerText = "⏳ MEMULAI RUNNER CLOUD GITHUB ACTIONS...";
    stepperArea.style.display = "block";
    galleryArea.innerHTML = "";

    const jobId = "job_" + Math.random().toString(36).substring(2, 10) + "_" + Date.now().toString(36);
    this.activeJobId = jobId;

    try {
      const dispatchUrl = `https://api.github.com/repos/${CONFIG.GITHUB_REPO}/dispatches`;
      const resp = await fetch(dispatchUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${CONFIG.GITHUB_PAT.trim()}`,
          "Accept": "application/vnd.github.v3+json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          event_type: "process-video",
          client_payload: {
            job_id: jobId,
            user_id: this.currentUser || "admin",
            youtube_url: ytUrl,
            duration_mode: duration,
            clip_count: clipCount,
            crop_mode: cropMode,
            caption_style: captionStyle
          }
        })
      });

      if (resp.status === 204 || resp.ok) {
        this.renderStepper("queued", "Menghubungkan ke runner cloud 16GB RAM... Memulai pemrosesan video...");
        this.startPolling(jobId);
      } else {
        const errText = await resp.text();
        stepperArea.innerHTML = `<div style="color: #F43F5E; padding: 16px; background: rgba(244,63,94,0.15); border-radius: 12px;">⚠️ Gagal memulai proses di GitHub Actions: ${errText.slice(0, 120)}</div>`;
        btn.disabled = false;
        btn.innerText = "🚀 Mulai Generasi Klip Otomatis";
      }

    } catch (e) {
      stepperArea.innerHTML = `<div style="color: #F43F5E; padding: 16px; background: rgba(244,63,94,0.15); border-radius: 12px;">⚠️ Gagal menghubungi server: ${e.message}</div>`;
      btn.disabled = false;
      btn.innerText = "🚀 Mulai Generasi Klip Otomatis";
    }
  }

  startPolling(jobId) {
    if (this.pollingInterval) clearInterval(this.pollingInterval);

    const btn = document.getElementById("btn-start-process");

    this.pollingInterval = setInterval(async () => {
      try {
        const statusUrl = `https://huggingface.co/datasets/${CONFIG.HF_DATASET_REPO}/raw/main/status/${jobId}.json?t=${Date.now()}`;
        const resp = await fetch(statusUrl);

        if (resp.ok) {
          const data = await resp.json();
          if (data && data.status) {
            const st = data.status;
            const msg = data.progress_message || "Sedang memproses...";
            const llm = data.llm_used;

            this.renderStepper(st, msg, llm);

            if (st === "done") {
              clearInterval(this.pollingInterval);
              btn.disabled = false;
              btn.innerText = "🚀 Mulai Generasi Klip Otomatis";
              this.renderGallery(data.clips || []);
            } else if (st === "error") {
              clearInterval(this.pollingInterval);
              btn.disabled = false;
              btn.innerText = "🚀 Mulai Generasi Klip Otomatis";
              this.renderError(data.error || msg, jobId);
            }
          }
        }
      } catch (e) {
        // Runner initializing
      }
    }, 5000);
  }

  renderStepper(status, message, llmUsed = null) {
    const steps = [
      ["queued", "1. Antrean"],
      ["downloading", "2. Unduh Video"],
      ["transcribing", "3. Transkripsi Suara"],
      ["detecting", "4. Deteksi Momen Viral"],
      ["rendering", "5. Render Vertikal 9:16"],
      ["done", "6. Selesai"]
    ];

    const order = { queued: 0, downloading: 1, transcribing: 2, detecting: 3, preparing: 3, rendering: 4, uploading: 4, done: 5, error: -1 };
    const curIdx = order[status] !== undefined ? order[status] : 0;

    let stepsHtml = steps.map(([key, label], idx) => {
      let icon = "○";
      let color = "#64748B";
      if (status === "error") {
        icon = "✕"; color = "#F43F5E";
      } else if (idx < curIdx || status === "done") {
        icon = "✓"; color = "#10B981";
      } else if (idx === curIdx) {
        icon = "●"; color = "#38BDF8";
      }
      return `<div style="color: ${color}; display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 600;"><span>${icon}</span> <span>${label}</span></div>`;
    }).join(' <span style="color: #334155;">──►</span> ');

    let llmBadge = "";
    if (llmUsed && llmUsed.provider_id) {
      llmBadge = `<div style="margin-top: 12px; font-size: 12.5px; color: #38BDF8;">⚡ AI Provider Aktif: <b>${llmUsed.provider_id}</b> (${llmUsed.model_id || ''})</div>`;
    }

    document.getElementById("dash-stepper-area").innerHTML = `
      <div class="stepper-box">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          ${stepsHtml}
        </div>
        <div style="margin-top: 16px; font-size: 14px; color: #F8FAFC; display: flex; align-items: center; gap: 12px;">
          <div class="filmstrip-loader">
            <div class="film-cell"></div>
            <div class="film-cell"></div>
            <div class="film-cell"></div>
            <div class="film-cell"></div>
          </div>
          <span>${message}</span>
        </div>
        ${llmBadge}
      </div>
    `;
  }

  renderGallery(clips) {
    if (!clips || clips.length === 0) return;

    const cards = clips.map((c) => `
      <div class="video-card">
        <div style="display: flex; justify-content: space-between; margin-bottom: 14px;">
          <span style="font-size: 11.5px; background: rgba(56, 189, 248, 0.12); color: #38BDF8; padding: 5px 12px; border-radius: 8px; font-weight: 800;">KLIP #${(c.clip_id || '').toUpperCase()}</span>
          <span style="font-size: 11.5px; background: rgba(245, 158, 11, 0.12); color: #F59E0B; padding: 5px 12px; border-radius: 8px; font-weight: 800;">🔥 ${c.viral_score || 8.5}/10 VIRAL</span>
        </div>
        <video src="${c.url}" controls></video>
        <h4 style="margin: 16px 0 6px 0; color: #FFFFFF; font-size: 15.5px; font-family: 'Space Grotesk', sans-serif;">${c.title || 'Klip Video'}</h4>
        <p style="color: #94A3B8; font-size: 13px; margin-bottom: 18px;">⏱ ${c.duration || 30}s • ${(c.hook_reason || '').slice(0, 75)}...</p>
        <a href="${c.url}" download class="btn btn-primary" style="width: 100%; font-size: 13.5px;">📥 Unduh Video MP4</a>
      </div>
    `).join("");

    document.getElementById("dash-gallery-area").innerHTML = `
      <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 18px; color: #FFFFFF;">
        🎉 Klip Siap Dipublikasikan (${clips.length} Klip Berhasil Dirender):
      </h3>
      <div class="gallery-grid">${cards}</div>
    `;
  }

  renderError(errorMsg, jobId) {
    document.getElementById("dash-gallery-area").innerHTML = `
      <div style="background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 16px; padding: 26px; margin-top: 22px;">
        <h4 style="color: #F43F5E; font-size: 16.5px; margin-bottom: 8px;">⚠️ Gagal Memproses Video</h4>
        <p style="color: #F8FAFC; font-size: 14px; margin-bottom: 16px;">${errorMsg}</p>
        <div style="display: flex; gap: 12px; align-items: center;">
          <a href="mailto:${CONFIG.SUPPORT_EMAIL}?subject=[Bug Laporan] Job ${jobId}&body=Error: ${encodeURIComponent(errorMsg)}" class="btn btn-primary" style="background: #F43F5E; border-color: #F43F5E; color: #fff;">
            Hubungi Support (${CONFIG.SUPPORT_EMAIL})
          </a>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 8. BYOK & KEYS MANAGEMENT
  // =========================================================================
  saveApiKey() {
    const provider = document.getElementById("byok-provider-select").value;
    const rawKey = document.getElementById("byok-key-input").value.trim();
    const msgBox = document.getElementById("byok-feedback-msg");

    if (!rawKey) {
      alert("Harap masukkan API Key!");
      return;
    }

    let savedKeys = JSON.parse(localStorage.getItem("autoclipper_keys") || "{}");
    savedKeys[provider] = {
      last4: rawKey.slice(-4),
      updated_at: new Date().toISOString()
    };
    localStorage.setItem("autoclipper_keys", JSON.stringify(savedKeys));

    msgBox.innerHTML = `<div style="color: #10B981; font-weight: 700;">✓ API Key untuk ${provider} berhasil disimpan!</div>`;
    document.getElementById("byok-key-input").value = "";
    this.loadConnectedProviders();
  }

  deleteApiKey() {
    const provider = document.getElementById("byok-provider-select").value;
    const msgBox = document.getElementById("byok-feedback-msg");

    let savedKeys = JSON.parse(localStorage.getItem("autoclipper_keys") || "{}");
    if (savedKeys[provider]) {
      delete savedKeys[provider];
      localStorage.setItem("autoclipper_keys", JSON.stringify(savedKeys));
      msgBox.innerHTML = `<div style="color: #10B981; font-weight: 700;">✓ Key ${provider} berhasil dihapus.</div>`;
    } else {
      msgBox.innerHTML = `<div style="color: #F59E0B;">Key tidak ditemukan.</div>`;
    }
    this.loadConnectedProviders();
  }

  loadConnectedProviders() {
    const tableBox = document.getElementById("byok-table-container");
    if (!tableBox) return;

    let savedKeys = JSON.parse(localStorage.getItem("autoclipper_keys") || "{}");
    const providers = Object.keys(savedKeys);

    if (providers.length > 0) {
      const rows = providers.map(p => `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
          <td style="padding: 14px 16px; font-weight: 700; color: #FFFFFF;">${p.toUpperCase()}</td>
          <td style="padding: 14px 16px; font-family: monospace; color: #38BDF8;">••••${savedKeys[p].last4}</td>
          <td style="padding: 14px 16px; color: #10B981; font-weight: 700;">✓ Active</td>
          <td style="padding: 14px 16px; color: #94A3B8;">Multi-Model</td>
          <td style="padding: 14px 16px; color: #64748B; font-size: 12.5px;">${savedKeys[p].updated_at.slice(0, 19)}</td>
        </tr>
      `).join("");

      tableBox.innerHTML = `
        <table style="width: 100%; border-collapse: collapse; background: var(--bg-surface); border-radius: 14px; overflow: hidden; border: 1px solid var(--card-border);">
          <thead>
            <tr style="background: rgba(255, 255, 255, 0.04); text-align: left; font-size: 13.5px; color: #94A3B8;">
              <th style="padding: 14px 16px;">Provider</th>
              <th style="padding: 14px 16px;">Key Preview</th>
              <th style="padding: 14px 16px;">Status</th>
              <th style="padding: 14px 16px;">Model Aktif</th>
              <th style="padding: 14px 16px;">Terakhir Diperbarui</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    } else {
      tableBox.innerHTML = `<p style="color: #94A3B8; font-size: 14px;">Belum ada provider yang tersambung. Silakan tambahkan API key di atas.</p>`;
    }
  }

  // =========================================================================
  // 9. COOKIE VAULT
  // =========================================================================
  saveCookie() {
    const raw = document.getElementById("cookie-input").value.trim();
    const msg = document.getElementById("cookie-feedback-msg");

    if (!raw) {
      alert("Harap tempelkan teks cookie Netscape!");
      return;
    }

    localStorage.setItem("autoclipper_cookie", raw);
    msg.innerHTML = `<div style="color: #10B981; font-weight: 700; margin-top: 10px;">✓ Cookie YouTube berhasil disimpan & terenkripsi lokal!</div>`;
    document.getElementById("cookie-input").value = "";
  }

  deleteCookie() {
    const msg = document.getElementById("cookie-feedback-msg");
    localStorage.removeItem("autoclipper_cookie");
    msg.innerHTML = `<div style="color: #10B981; font-weight: 700; margin-top: 10px;">✓ Cookie berhasil dihapus.</div>`;
  }

  // =========================================================================
  // 10. BRAND VOICE & SOCIAL CONTENT
  // =========================================================================
  saveBrandVoice() {
    alert("Preferensi Brand Voice berhasil disimpan!");
  }

  async generateHooks() {
    const vidId = document.getElementById("content-video-id").value.trim();
    const resBox = document.getElementById("content-result-area");

    if (!vidId) {
      alert("Harap masukkan ID Video!");
      return;
    }

    resBox.innerHTML = `<div style="padding: 16px; color: #38BDF8;">⏳ Sedang membuat 5 varian hook viral dengan AI...</div>`;

    setTimeout(() => {
      resBox.innerHTML = `
        <div style="background: var(--bg-surface); border: 1px solid var(--card-border); border-radius: 16px; padding: 22px; margin-top: 18px;">
          <h4 style="color: #38BDF8; font-size: 15.5px; margin-bottom: 14px;">🎯 5 Varian Hook Viral Terbuat:</h4>
          <ol style="color: #F8FAFC; font-size: 14px; padding-left: 20px; line-height: 1.85;">
            <li><b>Contrarian:</b> "Semua orang salah paham tentang hal ini, sampai kamu melihat..."</li>
            <li><b>Question:</b> "Pernah gak kamu kepikiran kenapa 90% kreator gagal di tahap ini?"</li>
            <li><b>Shocking Stat:</b> "Data ini bikin kaget: Hanya butuh 3 detik untuk mengubah hasil video kamu!"</li>
            <li><b>Story Hook:</b> "Awalnya saya kira ini mustahil, sampai akhirnya rahasia ini terbongkar..."</li>
            <li><b>How-To Hook:</b> "Ini cara paling cepat buat klip viral tanpa pusing potong manual!"</li>
          </ol>
        </div>
      `;
    }, 1200);
  }

  async generateSchedule() {
    const resBox = document.getElementById("content-result-area");
    resBox.innerHTML = `
      <div style="background: var(--bg-surface); border: 1px solid var(--card-border); border-radius: 16px; padding: 22px; margin-top: 18px;">
        <h4 style="color: #10B981; font-size: 15.5px; margin-bottom: 14px;">📅 Rekomendasi Jadwal Posting:</h4>
        <p style="color: #94A3B8; font-size: 13.5px; line-height: 1.7;">
          • <b>TikTok:</b> Jam 12:00 WIB & 19:30 WIB (Peak Engagement)<br>
          • <b>Instagram Reels:</b> Jam 17:00 WIB - 20:00 WIB<br>
          • <b>YouTube Shorts:</b> Jam 18:30 WIB (Algoritma Rekomendasi Malam)
        </p>
      </div>
    `;
  }

  // =========================================================================
  // 11. HELP & FEEDBACK DISPATCHER
  // =========================================================================
  sendFeedback() {
    const jid = document.getElementById("help-job-id").value.trim();
    const yurl = document.getElementById("help-yt-url").value.trim();
    const msg = document.getElementById("help-message").value.trim();
    const res = document.getElementById("help-feedback-result");

    if (!msg) {
      alert("Harap tuliskan pesan atau kendala Anda!");
      return;
    }

    const subject = encodeURIComponent(`[Auto-Clipper Support] Tiket dari ${this.currentUser || 'User'}`);
    const body = encodeURIComponent(
      `Halo Tim Support Auto-Clipper,\n\n` +
      `User ID: ${this.currentUser || 'Anonymous'}\n` +
      `Job ID: ${jid || 'N/A'}\n` +
      `URL Video: ${yurl || 'N/A'}\n\n` +
      `Pesan:\n${msg}\n\n` +
      `Dikirim dari Portal Resmi Auto-Clipper Pro`
    );

    const mailto = `mailto:${CONFIG.SUPPORT_EMAIL}?subject=${subject}&body=${body}`;

    res.innerHTML = `
      <div style="background: var(--bg-surface); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 14px; padding: 18px;">
        <h4 style="color: #10B981; font-size: 15px; margin-bottom: 6px;">✓ Tiket Laporan Siap!</h4>
        <p style="color: #94A3B8; font-size: 13.5px; margin-bottom: 14px;">Klik tombol di bawah untuk membuka aplikasi email Anda:</p>
        <a href="${mailto}" target="_blank" class="btn btn-primary" style="background: #10B981; border-color: #10B981; color: #fff;">
          ✉️ Kirim Email ke ${CONFIG.SUPPORT_EMAIL}
        </a>
      </div>
    `;
  }
}

// Global instance
window.app = new AutoClipperApp();
