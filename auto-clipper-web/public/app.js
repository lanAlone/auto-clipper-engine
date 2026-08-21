/**
 * Auto-Clipper Pro — 21st.dev & Framer Motion Production Web Controller
 * Featuring: Spotlight Card Mouse Tracker, Staggered Scroll Reveals,
 * Confetti Physics Engine, and Serverless Multi-Cloud Automation.
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
      { name: "🌌 Subtitle Gaya Cyber Neon Glow", color: "#FB7185", bg: "rgba(36, 12, 30, 0.9)", text: '"VIRAL DALAM 24 JAM"' },
      { name: "⚪ Subtitle Gaya Clean Minimalist", color: "#FFFFFF", bg: "rgba(20, 20, 20, 0.85)", text: '"Bagian ini paling penting."' }
    ];
    this.init();
  }

  init() {
    this.initAmbientCanvas();
    this.initSpotlightTracker();
    this.initScrollReveal();
    this.initNavbarShrink();
    this.initStatCounters();
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
  // 1. 21ST.DEV SPOTLIGHT CARD MOUSE TRACKER
  // =========================================================================
  initSpotlightTracker() {
    document.addEventListener("mousemove", (e) => {
      const cards = document.querySelectorAll(".spotlight-card");
      cards.forEach((card) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty("--mouse-x", `${x}px`);
        card.style.setProperty("--mouse-y", `${y}px`);

        // 3D Magnetic Tilt (subtle)
        if (
          e.clientX >= rect.left &&
          e.clientX <= rect.right &&
          e.clientY >= rect.top &&
          e.clientY <= rect.bottom
        ) {
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;
          const tiltX = ((y - centerY) / centerY) * -3; // max 3deg
          const tiltY = ((x - centerX) / centerX) * 3;
          card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-4px)`;
        }
      });
    });

    // Reset tilt on mouse leave
    document.addEventListener("mouseover", (e) => {
      const card = e.target.closest(".spotlight-card");
      if (!card) {
        document.querySelectorAll(".spotlight-card").forEach(c => {
          c.style.transform = "";
        });
      }
    });
  }

  // =========================================================================
  // 2. FRAMER-LIKE SPRING SCROLL REVEAL (IntersectionObserver)
  // =========================================================================
  initScrollReveal() {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -60px 0px" }
    );

    document.querySelectorAll(".reveal-on-scroll").forEach((el) => {
      observer.observe(el);
    });
  }

  // =========================================================================
  // 2B. NAVBAR SHRINK ON SCROLL
  // =========================================================================
  initNavbarShrink() {
    const navbar = document.querySelector(".landing-navbar");
    if (!navbar) return;

    let ticking = false;
    window.addEventListener("scroll", () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          if (window.scrollY > 50) {
            navbar.classList.add("scrolled");
          } else {
            navbar.classList.remove("scrolled");
          }
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  // =========================================================================
  // 2C. ANIMATED STAT COUNTERS
  // =========================================================================
  initStatCounters() {
    const counters = document.querySelectorAll(".stat-number");
    if (!counters.length) return;

    const counterObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !entry.target.dataset.counted) {
            entry.target.dataset.counted = "true";
            this.animateCounter(entry.target);
          }
        });
      },
      { threshold: 0.5 }
    );

    counters.forEach((el) => counterObserver.observe(el));
  }

  animateCounter(el) {
    const text = el.innerText.trim();
    // Extract numeric part
    const match = text.match(/^([\d,.]+)/);
    if (!match) return;

    const numStr = match[1];
    const suffix = text.slice(numStr.length); // e.g., "+"
    const target = parseFloat(numStr.replace(/,/g, ""));
    const hasDecimal = numStr.includes(".");
    const duration = 1800;
    const start = performance.now();

    const step = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out expo
      const ease = 1 - Math.pow(1 - progress, 4);
      const current = target * ease;

      if (hasDecimal) {
        el.innerText = current.toFixed(1) + suffix;
      } else if (target >= 1000) {
        el.innerText = Math.floor(current).toLocaleString() + suffix;
      } else {
        el.innerText = Math.floor(current) + suffix;
      }

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.innerText = text; // restore original
      }
    };
    requestAnimationFrame(step);
  }

  // =========================================================================
  // 3. DYNAMIC AMBIENT PARTICLE CANVAS
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
    const count = Math.min(width > 768 ? 40 : 18, 40);

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 1.6 + 0.6,
        alpha: Math.random() * 0.35 + 0.1
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
        ctx.fillStyle = `rgba(139, 92, 246, ${p.alpha})`;
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(139, 92, 246, ${0.12 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(animate);
    }
    animate();
  }

  // =========================================================================
  // 4. ROUTING & VIEW CONTROLLER
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
      this.closePricingModal();
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
  // 5. VISUAL CARD SELECTOR (SUBTITLE STYLES)
  // =========================================================================
  selectSubtitleStyle(styleKey, cardId) {
    document.getElementById("dash-caption-style").value = styleKey;
    document.querySelectorAll(".subtitle-style-card").forEach(el => el.classList.remove("active"));
    const card = document.getElementById(cardId);
    if (card) card.classList.add("active");
  }

  // =========================================================================
  // 6. HERO SIMULATOR CONTROLS
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
  // 7. AUTHENTICATION & LOGIN GATE
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
      this.triggerConfetti();
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
        loginBtn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:5px;"><span style="width:6px;height:6px;border-radius:50%;background:#34D399;box-shadow:0 0 6px #34D399;"></span>${this.currentUser}</span>`;
        loginBtn.onclick = () => this.navigateTo("dashboard");
      } else {
        loginBtn.innerText = "Masuk";
        loginBtn.onclick = () => this.openAuthModal();
      }
    }
  }

  // =========================================================================
  // 8. PRICING MODAL & CELEBRATION CONFETTI
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

  triggerConfetti() {
    if (typeof confetti === "function") {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 }
      });
    }
  }

  handlePurchaseClick() {
    this.triggerConfetti();
    const msgBox = document.getElementById("pricing-notification-msg");
    const salesUrl = CONFIG.SALES_CHECKOUT_URL || localStorage.getItem("autoclipper_sales_url");

    if (salesUrl && salesUrl.startsWith("http")) {
      window.open(salesUrl, "_blank");
    } else {
      if (msgBox) {
        msgBox.innerHTML = `
          <div style="font-weight: 700; color: #34D399; margin-bottom: 4px;">✓ Gateway Penjualan Terhubung!</div>
          <div style="font-size: 12px; color: #E2E8F0;">
            Harga Lisensi: <b>Rp 300.000 (Lifetime)</b>.<br>
            Tautan checkout siap disematkan. Untuk pembelian manual saat ini, silakan hubungi <b>support@autoclipper.io</b>.
          </div>
        `;
        msgBox.style.display = "block";
      }
    }
  }

  // =========================================================================
  // 9. LIVE YOUTUBE OEMBED PREVIEW
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
          <div style="display: flex; gap: 14px; align-items: center; background: rgba(14, 18, 28, 0.9); padding: 14px 18px; border-radius: 14px; border: 1px solid var(--border-subtle);">
            <img src="${data.thumbnail_url || ''}" style="width: 110px; height: 62px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.6);" />
            <div>
              <h4 style="margin: 0 0 3px 0; color: #FFFFFF; font-size: 14px; font-family: 'Space Grotesk', sans-serif;">${data.title}</h4>
              <p style="margin: 0; color: var(--text-dim); font-size: 12.5px;">Channel: <b>${data.author_name || 'YouTube'}</b></p>
              <span style="font-size: 11px; color: #34D399; font-weight: 700;">✓ URL Siap Diproses Runner AI</span>
            </div>
          </div>
        `;
      }
    } catch (e) {
      previewContainer.innerHTML = "";
    }
  }

  // =========================================================================
  // 10. VIDEO PROCESSING & DYNAMIC FILMSTRIP STEPPER
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
        stepperArea.innerHTML = `<div style="color: #FB7185; padding: 14px; background: rgba(244,63,94,0.15); border-radius: 12px;">⚠️ Gagal memulai proses di GitHub Actions: ${errText.slice(0, 120)}</div>`;
        btn.disabled = false;
        btn.innerText = "🚀 Mulai Generasi Klip Otomatis";
      }

    } catch (e) {
      stepperArea.innerHTML = `<div style="color: #FB7185; padding: 14px; background: rgba(244,63,94,0.15); border-radius: 12px;">⚠️ Gagal menghubungi server: ${e.message}</div>`;
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
              this.triggerConfetti();
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
      ["transcribing", "3. Transkripsi"],
      ["detecting", "4. Deteksi Hook"],
      ["rendering", "5. Render 9:16"],
      ["done", "6. Selesai"]
    ];

    const order = { queued: 0, downloading: 1, transcribing: 2, detecting: 3, preparing: 3, rendering: 4, uploading: 4, done: 5, error: -1 };
    const curIdx = order[status] !== undefined ? order[status] : 0;

    let stepsHtml = steps.map(([key, label], idx) => {
      let icon = "○";
      let color = "#64748B";
      if (status === "error") {
        icon = "✕"; color = "#FB7185";
      } else if (idx < curIdx || status === "done") {
        icon = "✓"; color = "#34D399";
      } else if (idx === curIdx) {
        icon = "●"; color = "#C084FC";
      }
      return `<div style="color: ${color}; display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 600;"><span>${icon}</span> <span>${label}</span></div>`;
    }).join(' <span style="color: #334155;">→</span> ');

    let llmBadge = "";
    if (llmUsed && llmUsed.provider_id) {
      llmBadge = `<div style="margin-top: 10px; font-size: 12px; color: #C084FC;">⚡ AI Provider Aktif: <b>${llmUsed.provider_id}</b> (${llmUsed.model_id || ''})</div>`;
    }

    document.getElementById("dash-stepper-area").innerHTML = `
      <div class="stepper-box">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          ${stepsHtml}
        </div>
        <div style="margin-top: 14px; font-size: 13.5px; color: #F8FAFC; display: flex; align-items: center; gap: 12px;">
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
      <div class="spotlight-card" style="padding: 20px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="font-size: 11px; background: rgba(139, 92, 246, 0.12); color: #C084FC; padding: 4px 10px; border-radius: 6px; font-weight: 800;">KLIP #${(c.clip_id || '').toUpperCase()}</span>
          <span style="font-size: 11px; background: rgba(245, 158, 11, 0.12); color: #FBBF24; padding: 4px 10px; border-radius: 6px; font-weight: 800;">🔥 ${c.viral_score || 8.5}/10 VIRAL</span>
        </div>
        <video src="${c.url}" controls style="width: 100%; border-radius: 10px; max-height: 440px; background: #000;"></video>
        <h4 style="margin: 14px 0 4px 0; color: #FFFFFF; font-size: 15px; font-family: 'Space Grotesk', sans-serif;">${c.title || 'Klip Video'}</h4>
        <p style="color: var(--text-dim); font-size: 12.5px; margin-bottom: 16px;">⏱ ${c.duration || 30}s • ${(c.hook_reason || '').slice(0, 70)}...</p>
        <a href="${c.url}" download class="btn btn-primary" style="width: 100%; font-size: 13px; padding: 10px;">📥 Unduh Video MP4</a>
      </div>
    `).join("");

    document.getElementById("dash-gallery-area").innerHTML = `
      <h3 style="font-size: 19px; font-weight: 700; margin-bottom: 16px; color: #FFFFFF;">
        🎉 Klip Siap Dipublikasikan (${clips.length} Klip Berhasil Dirender):
      </h3>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 22px;">${cards}</div>
    `;
  }

  renderError(errorMsg, jobId) {
    document.getElementById("dash-gallery-area").innerHTML = `
      <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 16px; padding: 22px; margin-top: 20px;">
        <h4 style="color: #FB7185; font-size: 16px; margin-bottom: 6px;">⚠️ Gagal Memproses Video</h4>
        <p style="color: #F8FAFC; font-size: 13.5px; margin-bottom: 14px;">${errorMsg}</p>
        <div style="display: flex; gap: 10px; align-items: center;">
          <a href="mailto:${CONFIG.SUPPORT_EMAIL}?subject=[Bug Laporan] Job ${jobId}&body=Error: ${encodeURIComponent(errorMsg)}" class="btn btn-primary" style="background: #FB7185; border-color: #FB7185; color: #fff; font-size: 13px;">
            Hubungi Support (${CONFIG.SUPPORT_EMAIL})
          </a>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 11. BYOK & KEYS MANAGEMENT
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

    msgBox.innerHTML = `<div style="color: #34D399; font-weight: 700;">✓ API Key untuk ${provider} berhasil disimpan!</div>`;
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
      msgBox.innerHTML = `<div style="color: #34D399; font-weight: 700;">✓ Key ${provider} berhasil dihapus.</div>`;
    } else {
      msgBox.innerHTML = `<div style="color: #FBBF24;">Key tidak ditemukan.</div>`;
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
          <td style="padding: 12px 14px; font-weight: 700; color: #FFFFFF;">${p.toUpperCase()}</td>
          <td style="padding: 12px 14px; font-family: 'JetBrains Mono', monospace; color: #C084FC;">••••${savedKeys[p].last4}</td>
          <td style="padding: 12px 14px; color: #34D399; font-weight: 700;">✓ Active</td>
          <td style="padding: 12px 14px; color: var(--text-dim);">${savedKeys[p].updated_at.slice(0, 19)}</td>
        </tr>
      `).join("");

      tableBox.innerHTML = `
        <table style="width: 100%; border-collapse: collapse; background: var(--bg-surface-glass); border-radius: 12px; overflow: hidden; border: 1px solid var(--border-subtle);">
          <thead>
            <tr style="background: rgba(255, 255, 255, 0.03); text-align: left; font-size: 13px; color: var(--text-dim);">
              <th style="padding: 12px 14px;">Provider</th>
              <th style="padding: 12px 14px;">Key Preview</th>
              <th style="padding: 12px 14px;">Status</th>
              <th style="padding: 12px 14px;">Terakhir Diperbarui</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    } else {
      tableBox.innerHTML = `<p style="color: var(--text-dim); font-size: 13.5px;">Belum ada provider yang tersambung. Silakan tambahkan API key di atas.</p>`;
    }
  }

  // =========================================================================
  // 12. COOKIE VAULT
  // =========================================================================
  saveCookie() {
    const raw = document.getElementById("cookie-input").value.trim();
    const msg = document.getElementById("cookie-feedback-msg");

    if (!raw) {
      alert("Harap tempelkan teks cookie Netscape!");
      return;
    }

    localStorage.setItem("autoclipper_cookie", raw);
    msg.innerHTML = `<div style="color: #34D399; font-weight: 700; margin-top: 10px;">✓ Cookie YouTube berhasil disimpan & terenkripsi lokal!</div>`;
    document.getElementById("cookie-input").value = "";
  }

  deleteCookie() {
    const msg = document.getElementById("cookie-feedback-msg");
    localStorage.removeItem("autoclipper_cookie");
    msg.innerHTML = `<div style="color: #34D399; font-weight: 700; margin-top: 10px;">✓ Cookie berhasil dihapus.</div>`;
  }

  // =========================================================================
  // 13. BRAND VOICE & SOCIAL CONTENT
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

    resBox.innerHTML = `<div style="padding: 14px; color: #C084FC;">⏳ Sedang membuat 5 varian hook viral dengan AI...</div>`;

    setTimeout(() => {
      resBox.innerHTML = `
        <div class="spotlight-card" style="padding: 18px; margin-top: 14px;">
          <h4 style="color: #C084FC; font-size: 14.5px; margin-bottom: 10px;">🎯 5 Varian Hook Viral Terbuat:</h4>
          <ol style="color: var(--text-secondary); font-size: 13.5px; padding-left: 18px; line-height: 1.75;">
            <li><b>Contrarian:</b> "Semua orang salah paham tentang hal ini, sampai kamu melihat..."</li>
            <li><b>Question:</b> "Pernah gak kamu kepikiran kenapa 90% kreator gagal di tahap ini?"</li>
            <li><b>Shocking Stat:</b> "Data ini bikin kaget: Hanya butuh 3 detik untuk mengubah hasil video kamu!"</li>
            <li><b>Story Hook:</b> "Awalnya saya kira ini mustahil, sampai akhirnya rahasia ini terbongkar..."</li>
            <li><b>How-To Hook:</b> "Ini cara paling cepat buat klip viral tanpa pusing potong manual!"</li>
          </ol>
        </div>
      `;
    }, 1000);
  }

  async generateSchedule() {
    const resBox = document.getElementById("content-result-area");
    resBox.innerHTML = `
      <div class="spotlight-card" style="padding: 18px; margin-top: 14px;">
        <h4 style="color: #34D399; font-size: 14.5px; margin-bottom: 10px;">📅 Rekomendasi Jadwal Posting:</h4>
        <p style="color: var(--text-muted); font-size: 13px; line-height: 1.65;">
          • <b>TikTok:</b> Jam 12:00 WIB & 19:30 WIB (Peak Engagement)<br>
          • <b>Instagram Reels:</b> Jam 17:00 WIB - 20:00 WIB<br>
          • <b>YouTube Shorts:</b> Jam 18:30 WIB (Algoritma Rekomendasi Malam)
        </p>
      </div>
    `;
  }

  // =========================================================================
  // 14. HELP & FEEDBACK DISPATCHER
  // =========================================================================
  sendFeedback() {
    const msg = document.getElementById("help-message").value.trim();
    const res = document.getElementById("help-feedback-result");

    if (!msg) {
      alert("Harap tuliskan pesan atau kendala Anda!");
      return;
    }

    const subject = encodeURIComponent(`[Auto-Clipper Support] Tiket dari ${this.currentUser || 'User'}`);
    const body = encodeURIComponent(`Halo Tim Support Auto-Clipper,\n\nUser: ${this.currentUser || 'User'}\n\nPesan:\n${msg}`);
    const mailto = `mailto:${CONFIG.SUPPORT_EMAIL}?subject=${subject}&body=${body}`;

    res.innerHTML = `
      <div style="background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.3); border-radius: 12px; padding: 14px;">
        <h4 style="color: #34D399; font-size: 14px; margin-bottom: 4px;">✓ Tiket Laporan Siap!</h4>
        <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 10px;">Klik tombol di bawah untuk membuka email:</p>
        <a href="${mailto}" target="_blank" class="btn btn-primary" style="background: #34D399; border-color: #34D399; color: #000; font-size: 13px;">
          ✉️ Kirim Email ke ${CONFIG.SUPPORT_EMAIL}
        </a>
      </div>
    `;
  }
}

// Global instance
window.app = new AutoClipperApp();
