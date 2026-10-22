/* Companion dog controller.
   Public API (window.Companion):
     init({renderMarkdown, onResume, stages})  mount the dog into #work (call once)
     start()                                   a generation (or a resume) begins: wake up, get to work
     onEvent(e)                                feed every pipeline event: picks the matching animation
     fail(title, text, resumable)              sad dog + bubble (optionally with a Resume button)
     sleep()                                   go back to sleep
     info()                                    which dog is loaded + how each pose is resolved (used by preview.html)
     preview(pose)                             force a pose (used by preview.html)
   Which dog? If static/companion/pack/pack.json exists, that sprite pack is used
   (see pack/README.md); otherwise the built-in SVG dog (rover-art.js).
   On page load the dog arrives, then cycles through idle animations. During generation
   it reads/writes/sniffs, and when the AI fit assessment arrives it tells the user in a bubble. */
(function () {
  "use strict";

  // pipeline stage -> animation while that stage is running
  const STAGE_POSE = {
    scrape: "search", skills: "read", select: "think", rewrite: "write",
    about: "write", build: "think", render: "read", fit: "read",
  };
  const WAKE_MS = 1300;          // length of the yawn/stretch animation
  const IDLE_SLEEP_MS = 60000;   // falls asleep again after this long without work

  const POSES = ["sleep", "wake", "idle", "read", "write", "search", "think", "celebrate", "talk", "sad"];
  const PACK_DIR = "/static/companion/pack/";   // user sprite pack lives here
  let opts = {}, wrap, view, bubble, titleEl, scoreEl, bodyEl, actionsEl;
  let pose = "sleep", target = "sleep", lastBubble = null, mounted = false, started = false;
  let jobStarted = false;
  const timers = {};

  const later = (name, fn, ms) => { clearTimeout(timers[name]); timers[name] = setTimeout(fn, ms); };
  const cancel = (...names) => names.forEach(n => clearTimeout(timers[n]));

  function setPose(p) { pose = p; if (view) view.setPose(p); }

  /* Switch to pose p; a sleeping sprite reverses the lie-down animation to wake up. */
  function goto(p) {
    target = p;
    if (pose === "sleep") {
      const ms = view && view.wakeMs ? view.wakeMs() : WAKE_MS;
      if (!ms) { setPose(p); return; }      // this dog has no wake-up animation
      cancel("wake");
      if (view && typeof view.playWake === "function") {
        pose = "wake";
        view.playWake(() => { if (pose === "wake") setPose(target); });
      } else {
        setPose("wake");
        later("wake", () => setPose(target), ms);
      }
    } else if (pose !== "wake") {
      setPose(p);
    } // while waking up, only the target changes
  }

  function scheduleSleep(ms) { later("sleep", sleep, ms || IDLE_SLEEP_MS); }

  function sleep() {
    cancel("wake", "celebrate", "talk", "sleep");
    target = "sleep"; setPose("sleep");
  }

  function hideBubble() { if (bubble) bubble.hidden = true; }

  function showBubble({ title, html, text, score, actions }) {
    titleEl.textContent = title || "";
    scoreEl.hidden = !score; scoreEl.textContent = score ? `Fit score: ${score}/10` : "";
    bodyEl.classList.toggle("plain", html == null);
    if (html != null) bodyEl.innerHTML = html; else bodyEl.textContent = text || "";
    bodyEl.scrollTop = 0;
    actionsEl.innerHTML = "";
    (actions || []).forEach(a => {
      const b = document.createElement("button");
      b.type = "button"; b.className = a.primary ? "primary" : ""; b.textContent = a.label;
      b.onclick = a.onClick; actionsEl.appendChild(b);
    });
    bubble.classList.toggle("rover-bubble-above", !!score);
    bubble.hidden = false;
    lastBubble = { title, html, text, score, actions };
  }

  function start() {
    jobStarted = true;
    cancel("startupIntro", "celebrate", "talk", "sleep");
    hideBubble(); lastBubble = null;
    goto("read");
    scheduleSleep();
  }

  function summary(text) {
    const m = String(text || "").match(/(?:fit score|overall fit|match score|score)[^\d]{0,24}(\d+(?:\.\d+)?)\s*(?:\/\s*10|out of 10)/i);
    const html = opts.renderMarkdown ? opts.renderMarkdown(text) : null;
    cancel("sleep", "celebrate", "talk");

    // Wybudza psa z animacją przed pokazaniem podsumowania
    const wakeMs = view && view.wakeMs ? view.wakeMs() : WAKE_MS;
    if (pose === "sleep" || pose === "idle") {
      goto("wake");
      later("summary-wake", () => {
        goto("idle");
        showBubble({ title: "Here is my take on this job offer", html, text, score: m && m[1] });
        later("idle", () => {
          setPose("talk");
          later("talk", () => { setPose("idle"); scheduleSleep(); },
            Math.min(2500 + String(text || "").length * 10, 9000));
        }, 2200);
      }, wakeMs);
    } else {
      goto("idle");
      showBubble({ title: "Here is my take on this job offer", html, text, score: m && m[1] });
      later("idle", () => {
        setPose("talk");
        later("talk", () => { setPose("idle"); scheduleSleep(); },
          Math.min(2500 + String(text || "").length * 10, 9000));
      }, 2200);
    }
  }

  function fail(title, text, resumable) {
    cancel("idle", "talk");
    goto("sad");
    const actions = resumable && opts.onResume
      ? [{ label: "▶ Resume", primary: true, onClick: () => { hideBubble(); opts.onResume(); } }] : [];
    showBubble({ title: title || "Oops!", text, actions });
    scheduleSleep(IDLE_SLEEP_MS * 2);
  }

  function onEvent(e) {
    if (!mounted || !e || e.stage === "end" || e.stage === "profile") return;
    const label = (opts.stages && opts.stages[e.stage]) || e.stage;
    if (e.status === "running") {
      cancel("sleep", "celebrate", "talk");
      if (lastBubble && lastBubble.actions && lastBubble.actions.length) hideBubble();
      if (e.stage === "fit") hideBubble();
      goto(STAGE_POSE[e.stage] || "read");
    } else if (e.stage === "fit" && e.status === "done") {
      summary(e.detail);
    } else if (e.status === "error") {
      const detail = String(e.detail || "Unknown error").slice(0, 400);
      fail(`Oops — ${label} failed`,
        detail + (e.resumable ? "\n\nEverything finished so far is saved. Press Resume and I will continue from here." : ""),
        !!e.resumable);
    }
  }

  /* ---------- view 1: built-in SVG dog (animated by companion.css) ---------- */
  function svgView(host) {
    host.innerHTML = window.ROVER_SVG;
    const svg = host.querySelector(".rover");
    return {
      setPose: p => { svg.dataset.pose = p; },
      wakeMs: () => WAKE_MS,
      info: () => ({ source: "svg", name: "Built-in SVG dog", poses: Object.fromEntries(POSES.map(p => [p, "own"])) }),
    };
  }

  /* ---------- view 2: user sprite pack (pack/pack.json) ---------- */
  // when a pose has no animation of its own, try these (in order)
  const FALLBACK = { wake: [], sleep: ["idle"], idle: [], read: ["idle"], write: ["read", "idle"],
    search: ["think", "idle"], think: ["idle"], celebrate: ["talk", "idle"], talk: ["idle"], sad: ["idle"] };

  function spriteView(host, m) {
    const scale = Number(m.scale) || 1, W = (Number(m.width) || 128) * scale, H = (Number(m.height) || 128) * scale;
    host.style.width = W + "px"; host.style.height = H + "px";
    if (m.left != null) host.style.left = m.left + "px";
    if (m.bottom != null) host.style.bottom = m.bottom + "px";
    const el = document.createElement("div");
    el.className = "rover-sprite";
    if (m.flipX) el.style.transform = "scaleX(-1)";
    if (m.pixelated) el.style.imageRendering = "pixelated";
    host.appendChild(el);

    const anims = m.animations || {};
    const url = f => {
      const u = new URL(f, location.origin + PACK_DIR);
      if (u.origin !== location.origin) throw new Error("external files are not allowed: " + f);
      return u.href;
    };
    const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    const imagePromises = new Map();
    let raf = 0, playToken = 0, idleTimer = 0;
    let activePose = null, desiredPose = null, readState = "off", lastIdleChoice = "";

    function resolve(name, useFallback = true, seen = new Set()) {
      if (seen.has(name)) return null;
      seen.add(name);
      let a = anims[name];
      if (typeof a === "string") {
        const r = resolve(a, useFallback, seen);
        return r && { anim: r.anim, how: "alias:" + a };
      }
      if (a) return { anim: a, how: "own" };
      if (useFallback) for (const f of FALLBACK[name] || []) {
        const r = resolve(f, true, seen);
        if (r) return { anim: r.anim, how: "fallback:" + f };
      }
      return null;
    }
    const frameList = a => Array.isArray(a && a.frames) ? a.frames : null;
    const frameCount = a => a && a.sheet ? (Number(a.count) || 1) : ((frameList(a) || []).length);
    const fpsOf = a => Number(a && a.fps) || Number(m.fps) || 10;
    const durationOf = (a, count = frameCount(a)) => count ? count * 1000 / fpsOf(a) : 0;

    // Decode only the frames for the animation about to play. This avoids a burst
    // of hundreds of image requests on initial page load and prevents first-use stalls.
    function preloadImage(src) {
      if (imagePromises.has(src)) return imagePromises.get(src);
      const img = new Image();
      img.decoding = "async";
      const loaded = new Promise(resolveLoaded => {
        img.onload = () => resolveLoaded(true);
        img.onerror = () => {
          console.warn("Companion pack: cannot load", src);
          resolveLoaded(false);
        };
      });
      img.src = src;
      const promise = typeof img.decode === "function"
        ? img.decode().then(() => true, () => loaded)
        : loaded;
      imagePromises.set(src, promise);
      // Keep the cache bounded; the browser still keeps its normal HTTP cache.
      if (imagePromises.size > 180) {
        const oldest = imagePromises.keys().next().value;
        if (oldest !== src) imagePromises.delete(oldest);
      }
      return promise;
    }

    function draw(a, i, n) {
      if (a.sheet) {
        el.style.backgroundImage = `url("${url(a.sheet)}")`;
        el.style.backgroundSize = `${n * 100}% 100%`;
        el.style.backgroundPosition = `${n > 1 ? (i / (n - 1)) * 100 : 0}% 0`;
      } else {
        el.style.backgroundImage = `url("${url(frameList(a)[i])}")`;
        el.style.backgroundSize = "100% 100%";
        el.style.backgroundPosition = "center";
      }
    }

    function stopPlayer() {
      playToken++;
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    }
    function stopIdleTimer() {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = 0;
    }

    function playFrames(a, indexes = null, options = {}) {
      stopPlayer();
      const token = playToken;
      if (!a) { if (options.onComplete) options.onComplete(); return 0; }
      if (a.gif) {
        const src = url(a.gif);
        preloadImage(src).then(() => {
          if (token !== playToken) return;
          el.style.backgroundImage = `url("${src}")`;
          el.style.backgroundSize = "100% 100%";
          el.style.backgroundPosition = "center";
          if (options.onStart) options.onStart();
        });
        return Number(a.duration) || 0;
      }
      const n = frameCount(a);
      if (!n) { if (options.onComplete) options.onComplete(); return 0; }
      const list = indexes || Array.from({ length: n }, (_, i) => i);
      if (!list.length) { if (options.onComplete) options.onComplete(); return 0; }
      const fps = fpsOf(a), frameMs = 1000 / fps;
      const loop = options.loop == null ? a.loop !== false : !!options.loop;
      const srcs = a.sheet ? [url(a.sheet)] : list.map(i => url(frameList(a)[i]));
      Promise.all(srcs.map(preloadImage)).then(() => {
        if (token !== playToken) return;
        draw(a, list[0], n);
        if (options.onStart) options.onStart();
        if (list.length < 2 || reduce) {
          if (!loop) draw(a, list[list.length - 1], n);
          if (!loop && options.onComplete) options.onComplete();
          return;
        }
        let startTime = performance.now(), lastSlot = -1;
        const tick = now => {
          if (token !== playToken) return;
          let slot = Math.floor((now - startTime) / frameMs);
          if (slot >= list.length) {
            if (!loop) {
              draw(a, list[list.length - 1], n);
              raf = 0;
              if (options.onComplete) options.onComplete();
              return;
            }
            const cycles = Math.floor(slot / list.length);
            startTime += cycles * list.length * frameMs;
            slot = Math.floor((now - startTime) / frameMs);
          }
          if (slot !== lastSlot) {
            draw(a, list[slot % list.length], n);
            lastSlot = slot;
          }
          raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
      });
      return durationOf(a, list.length);
    }

    const idleNames = Object.keys(anims)
      .filter(name => /^_\d+Idle$/.test(name) && anims[name] && typeof anims[name] === "object")
      .sort((a, b) => Number(a.match(/^_(\d+)/)[1]) - Number(b.match(/^_(\d+)/)[1]));

    // Keep the dog calm between animations: show _1Idle/001.png as a static pose.
    // Occasionally play one random idle animation once, then return to the static frame.
    function showIdleBase(onReady) {
      stopPlayer();
      const base = anims["_1Idle"];
      const frames = frameList(base);
      const fallback = resolve("idle");
      const sourceAnim = base && frames && frames.length
        ? base
        : (fallback && frameList(fallback.anim) && frameList(fallback.anim).length
            ? fallback.anim
            : null);

      if (!sourceAnim) {
        if (onReady) onReady();
        return;
      }

      const token = playToken;
      preloadImage(url(frameList(sourceAnim)[0])).then(() => {
        // Ignore stale loads if another pose/animation starts while the image loads.
        if (token !== playToken || activePose !== "idle") return;
        draw(sourceAnim, 0, frameCount(sourceAnim));
        if (onReady) onReady();
      });
    }

    function startIdleCycle() {
      stopIdleTimer();
      if (activePose !== "idle") return;

      showIdleBase(() => {
        if (activePose !== "idle") return;
        // Keep _1Idle/001.png visible for around 15–25 seconds between actions.
        const delay = Math.random() * 15000;
        idleTimer = setTimeout(playRandomIdleOnce, delay);
      });
    }

    function playRandomIdleOnce() {
      if (activePose !== "idle") return;

      // Lick is a rare extra action; it is also played only once.
      const useLick = !!anims.Lick && Math.random() < 0.08;
      let picked = null;

      if (useLick) {
        picked = "Lick";
      } else {
        const primaryIdle = idleNames.includes("_1Idle") ? "_1Idle" : null;

        // Preserve the requested preference for _1Idle (85% of idle-action draws).
        if (primaryIdle && Math.random() < 0.85) {
          picked = primaryIdle;
        } else {
          const choices = idleNames.filter(name =>
            name !== "_1Idle" && name !== lastIdleChoice
          );
          const pool = choices.length
            ? choices
            : idleNames.filter(name => name !== "_1Idle");
          if (pool.length) picked = pool[Math.floor(Math.random() * pool.length)];
          if (!picked && primaryIdle) picked = primaryIdle;
        }
      }

      const anim = picked === "Lick" ? anims.Lick : (picked ? anims[picked] : null);
      if (!anim) {
        startIdleCycle();
        return;
      }

      lastIdleChoice = picked;
      playFrames(anim, null, {
        loop: false,
        onComplete: () => {
          if (activePose === "idle") startIdleCycle();
        },
      });
    }

    function playResolvedPose(p, onComplete) {
      const previousPose = activePose;
      activePose = p;
      stopIdleTimer();
      if (p === "idle") {
        startIdleCycle();
        return;
      }
      const r = resolve(p);
      if (!r) { if (onComplete) onComplete(); return; }

      // Tired is the lie-down movement. Sleep starts only after it has finished.
      if (p === "sleep" && previousPose !== "sleep" && previousPose !== "tired" && anims.Tired && resolve("sleep", false)) {
        playFrames(anims.Tired, null, {
          loop: false,
          onComplete: () => {
            if (activePose === "sleep") playFrames(r.anim, null, { loop: true, onComplete });
          },
        });
        return;
      }
      if (p === "wake") {
        playFrames(r.anim, null, { loop: false, onComplete });
        return;
      }
      playFrames(r.anim, null, { loop: r.anim.loop !== false, onComplete });
    }

    function readingAnimation() {
      const a = anims.Reading;
      if (!a || !frameList(a)) return null;
      const n = frameCount(a);
      const intro = Math.max(0, Math.min(n, Number(a.introFrames) || 0));
      const outro = Math.max(0, Math.min(n - intro, Number(a.outroFrames) || 0));
      if (!intro || !outro || intro + outro >= n) return null;
      return {
        anim: a,
        intro: Array.from({ length: intro }, (_, i) => i),
        loop: Array.from({ length: n - intro - outro }, (_, i) => intro + i),
        outro: Array.from({ length: outro }, (_, i) => n - outro + i),
      };
    }

    function setSpritePose(p, onComplete) {
      desiredPose = p;
      const isReading = p === "read" || p === "write";
      const reading = readingAnimation();

      if (isReading && reading) {
        if (readState === "intro" || readState === "loop") {
          activePose = p;
          return;
        }
        // If the dog goes back to reading while putting the book away, interrupt the exit.
        readState = "off";
        activePose = p;
        stopIdleTimer();
        readState = "intro";
        playFrames(reading.anim, reading.intro, {
          loop: false,
          onComplete: () => {
            if (readState !== "intro" || !(desiredPose === "read" || desiredPose === "write")) return;
            readState = "loop";
            playFrames(reading.anim, reading.loop, { loop: true });
          },
        });
        return;
      }

      if ((readState === "intro" || readState === "loop") && reading) {
        stopIdleTimer();
        readState = "outro";
        playFrames(reading.anim, reading.outro, {
          loop: false,
          onComplete: () => {
            if (readState !== "outro") return;
            readState = "off";
            playResolvedPose(desiredPose, onComplete);
          },
        });
        return;
      }
      if (readState === "outro") return; // retain the last requested pose until the book is put away
      readState = "off";
      playResolvedPose(p, onComplete);
    }

    return {
      setPose: setSpritePose,
      wakeMs() {
        const r = resolve("wake", false);
        if (!r) return 0;
        const a = r.anim, n = frameCount(a);
        return Number(a.duration) || (n ? durationOf(a) + 40 : WAKE_MS);
      },
      playWake(onComplete) {
        desiredPose = "wake";
        readState = "off";
        playResolvedPose("wake", onComplete);
      },
      playIntro(onComplete) {
        desiredPose = "celebrate";
        readState = "off";
        activePose = "celebrate";
        stopIdleTimer();
        const r = resolve("celebrate", false) || resolve("Come", false);
        if (!r) { if (onComplete) onComplete(); return; }
        playFrames(r.anim, null, {
          loop: false,
          onComplete: () => { if (activePose === "celebrate" && onComplete) onComplete(); },
        });
      },
      info: () => ({ source: "pack", name: m.name || "Custom sprite pack",
        poses: Object.fromEntries(POSES.map(p => { const r = resolve(p); return [p, r ? r.how : "missing"]; })) }),
    };
  }

  async function loadPack() {
    try {
      const r = await fetch(PACK_DIR + "pack.json", { cache: "no-store" });
      if (!r.ok) return null;                        // no pack.json -> built-in dog
      const m = await r.json();
      if (!m || typeof m.animations !== "object") throw new Error('pack.json needs an "animations" object');
      return m;
    } catch (e) { console.warn("Companion: ignoring sprite pack,", e.message); return null; }
  }

  async function mount() {
    const host = document.getElementById("work");
    if (!host) return false;
    wrap = document.createElement("div");
    wrap.className = "rover-wrap"; wrap.tabIndex = 0; wrap.setAttribute("role", "button");
    wrap.setAttribute("aria-label", "Helper dog: click to show or hide his last message");

    const pack = await loadPack();
    try { view = pack ? spriteView(wrap, pack) : null; }
    catch (e) { console.warn("Companion: sprite pack failed, using built-in dog.", e); view = null; wrap.innerHTML = ""; wrap.removeAttribute("style"); }
    if (!view) {
      if (!window.ROVER_SVG) return false;
      view = svgView(wrap);
    }
    console.info("Companion:", view.info().name);

    bubble = document.createElement("div");
    bubble.className = "rover-bubble"; bubble.hidden = true; bubble.setAttribute("role", "dialog");
    bubble.innerHTML = '<button type="button" class="rover-bubble-x" aria-label="Close">×</button>' +
      '<div class="rover-bubble-title"></div><div class="rover-bubble-score" hidden></div>' +
      '<div class="rover-bubble-body"></div><div class="rover-bubble-actions"></div>';
    titleEl = bubble.querySelector(".rover-bubble-title");
    scoreEl = bubble.querySelector(".rover-bubble-score");
    bodyEl = bubble.querySelector(".rover-bubble-body");
    actionsEl = bubble.querySelector(".rover-bubble-actions");
    bubble.querySelector(".rover-bubble-x").onclick = hideBubble;

    const poke = () => {
      if (lastBubble) { bubble.hidden ? showBubble(lastBubble) : hideBubble(); return; }
      if (pose === "sleep") {           // tiny easter egg: wake him up for a moment
        goto("idle");
      }
      scheduleSleep(IDLE_SLEEP_MS);
    };
    wrap.onclick = poke;
    wrap.onkeydown = ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); poke(); } };

    host.append(bubble, wrap);
    if (jobStarted) {
      view.setPose(pose);               // a generation may have started while the pack was loading
    } else {
      pose = "celebrate"; target = "idle";
      const finishIntro = () => {
        if (pose === "celebrate") {
          setPose("idle");
          scheduleSleep(IDLE_SLEEP_MS);
        }
      };
      if (view.playIntro) view.playIntro(finishIntro);
      else {
        view.setPose("celebrate");
        later("startupIntro", finishIntro, 2200);
      }
    }
    return true;
  }

  window.Companion = {
    init(o) {
      opts = o || {};
      if (started) return;
      started = true;
      mount().then(ok => { mounted = ok; }).catch(e => console.error("Companion failed to start", e));
    },
    start, onEvent, sleep,
    fail(title, text, resumable) { if (mounted) fail(title, text, resumable); },
    info() { return view ? view.info() : { source: "none", poses: {} }; },
    preview(p) { cancel("wake", "celebrate", "talk", "sleep"); target = p; setPose(p); },
  };
})();
