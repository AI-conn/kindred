/* Kindred — vanilla JS frontend. No build step, no external libraries.
   Codes exactly against the Kindred API contract:
     GET  /api/health
     GET  /api/personas
     POST /api/profile  (contract surface; the plan flow uses the profile
                         embedded in the /api/plan response)
     POST /api/plan
     POST /api/compare
*/
(function () {
  "use strict";

  var MAX_SEEDS = 5;

  var SLOT_META = {
    dinner: { label: "Dinner", icon: "🍽️" },
    watch: { label: "Watch", icon: "🎬" },
    listen: { label: "Listen", icon: "🎧" },
    read: { label: "Read", icon: "📖" }
  };

  var EXTRA_PLACEHOLDERS = ["another favourite", "one more you love"];

  /* ---------- State ---------- */
  var state = {
    refinements: new Set(),
    lastSeeds: [],
    lastLocation: "",
    lastPlan: null,
    lastProfile: null,
    lastCompare: null,
    lastAction: null, // { type: "plan" } | { type: "compare" }
    busy: false
  };

  /* ---------- DOM ---------- */
  function $(id) { return document.getElementById(id); }

  var els = {
    badge: $("health-badge"),
    personaRow: $("persona-row"),
    personaChips: $("persona-chips"),
    seedForm: $("seed-form"),
    seedInputsWrap: $("seed-inputs"),
    addSeedBtn: $("add-seed-btn"),
    seedLimitNote: $("seed-limit-note"),
    locationInput: $("location-input"),
    formError: $("form-error"),
    planBtn: $("plan-btn"),
    loading: $("loading-state"),
    errorState: $("error-state"),
    errorMessage: $("error-message"),
    retryBtn: $("retry-btn"),
    profileStrip: $("profile-strip"),
    resolvedChips: $("resolved-chips"),
    tasteTags: $("taste-tags"),
    unresolvedList: $("unresolved-list"),
    planView: $("plan-view"),
    planIntro: $("plan-intro"),
    planTimeline: $("plan-timeline"),
    planNotes: $("plan-notes"),
    compareBtn: $("compare-btn"),
    compareView: $("compare-view"),
    backToPlanBtn: $("back-to-plan-btn"),
    deltaBanner: $("delta-banner"),
    compareWith: $("compare-with"),
    compareWithout: $("compare-without"),
    baselineMethod: $("baseline-method"),
    baselineNote: $("baseline-note")
  };

  /* ---------- Helpers ---------- */
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function slotMeta(slot) {
    return SLOT_META[slot] || { label: slot ? slot.charAt(0).toUpperCase() + slot.slice(1) : "Pick", icon: "✦" };
  }

  function domainLabel(subtype) {
    if (!subtype) return "";
    // Subtypes may arrive as bare names ("movie") or URN tails; show the tail.
    var text = String(subtype);
    var idx = text.lastIndexOf(":");
    if (idx >= 0) text = text.slice(idx + 1);
    return text.replace(/_/g, " ");
  }

  function affinityPercent(value) {
    if (typeof value !== "number" || !isFinite(value)) return null;
    var pct;
    if (value <= 1) pct = value * 100;
    else if (value <= 100) pct = value;
    else pct = 100;
    return Math.max(0, Math.min(100, Math.round(pct)));
  }

  function tagPills(tags, className) {
    if (!Array.isArray(tags) || tags.length === 0) return "";
    var html = tags.map(function (tag) {
      var name = typeof tag === "string" ? tag : tag && tag.name;
      return name ? '<span class="tag-pill ' + esc(className || "") + '">' + esc(name) + "</span>" : "";
    }).join("");
    return html ? '<div class="tag-row pick-tags">' + html + "</div>" : "";
  }

  function fetchJSON(url, options) {
    return fetch(url, options).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        if (text) {
          try { data = JSON.parse(text); } catch (e) { data = null; }
        }
        if (!res.ok) {
          var detail = data && typeof data.detail === "string" ? data.detail : "";
          var err = new Error(detail || ("Request failed (" + res.status + ")"));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  function postJSON(url, body) {
    return fetchJSON(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  }

  function seedInputs() {
    return Array.prototype.slice.call(els.seedInputsWrap.querySelectorAll(".seed-input"));
  }

  function currentSeeds() {
    return seedInputs()
      .map(function (input) { return input.value.trim(); })
      .filter(function (value) { return value.length > 0; });
  }

  function currentLocation() {
    return els.locationInput.value.trim();
  }

  /* ---------- View state ---------- */
  function setBusy(busy) {
    state.busy = busy;
    els.planBtn.disabled = busy;
    els.compareBtn.disabled = busy;
    els.addSeedBtn.disabled = busy || seedInputs().length >= MAX_SEEDS;
    Array.prototype.forEach.call(document.querySelectorAll(".refinement-btn"), function (btn) {
      btn.disabled = busy;
    });
  }

  function showLoading() {
    els.errorState.hidden = true;
    els.profileStrip.hidden = true;
    els.planView.hidden = true;
    els.compareView.hidden = true;
    els.loading.hidden = false;
    els.loading.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function hideLoading() { els.loading.hidden = true; }

  function showError(message) {
    hideLoading();
    if (message) els.errorMessage.textContent = message;
    els.errorState.hidden = false;
    // If a plan already exists, keep it visible below the error so a failed
    // refinement or comparison never takes the evening away.
    if (state.lastPlan) {
      els.profileStrip.hidden = !state.lastProfile;
      els.planView.hidden = false;
    }
    els.errorState.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---------- Health badge (data-driven) ---------- */
  function loadHealth() {
    fetchJSON("/api/health")
      .then(function (health) {
        if (health && health.transport === "fixture") {
          els.badge.textContent = "Demo data mode — connect a Qloo API key for live results";
          els.badge.className = "badge badge--fixture";
        } else if (health && health.transport === "live") {
          els.badge.textContent = "Live · Qloo Taste API";
          els.badge.className = "badge badge--live";
        } else {
          els.badge.textContent = "Kindred";
          els.badge.className = "badge";
        }
      })
      .catch(function () {
        els.badge.textContent = "Connection unavailable";
        els.badge.className = "badge";
      });
  }

  /* ---------- Personas ---------- */
  function fillSeeds(seeds) {
    var list = (seeds || []).slice(0, MAX_SEEDS);
    while (seedInputs().length < list.length) addSeedField();
    seedInputs().forEach(function (input, i) {
      input.value = list[i] || "";
    });
    updateAddSeedState();
  }

  function loadPersonas() {
    fetchJSON("/api/personas")
      .then(function (data) {
        var personas = data && Array.isArray(data.personas) ? data.personas : [];
        if (personas.length === 0) return;
        els.personaChips.innerHTML = "";
        personas.forEach(function (persona) {
          var chip = document.createElement("button");
          chip.type = "button";
          chip.className = "persona-chip";
          chip.setAttribute("aria-pressed", "false");
          chip.textContent = persona.label || persona.id || "Persona";
          chip.addEventListener("click", function () {
            Array.prototype.forEach.call(els.personaChips.querySelectorAll(".persona-chip"), function (c) {
              c.setAttribute("aria-pressed", "false");
            });
            chip.setAttribute("aria-pressed", "true");
            fillSeeds(persona.seeds || []);
            hideFormError();
          });
          els.personaChips.appendChild(chip);
        });
        els.personaRow.hidden = false;
      })
      .catch(function () {
        // Personas are an accelerator, not a requirement — free-form seeding
        // stays fully available if they fail to load.
        els.personaRow.hidden = true;
      });
  }

  /* ---------- Seed fields ---------- */
  function addSeedField() {
    var inputs = seedInputs();
    if (inputs.length >= MAX_SEEDS) return;
    var number = inputs.length + 1;
    var label = document.createElement("label");
    label.className = "seed-field";
    label.innerHTML =
      '<span class="seed-field-label">Favourite ' + number + "</span>" +
      '<input type="text" class="seed-input" name="seed" autocomplete="off" placeholder="' +
      esc(EXTRA_PLACEHOLDERS[number - 4] || "another favourite") + '" />';
    els.seedInputsWrap.appendChild(label);
    var input = label.querySelector(".seed-input");
    if (input) input.focus();
    updateAddSeedState();
  }

  function updateAddSeedState() {
    var atMax = seedInputs().length >= MAX_SEEDS;
    els.addSeedBtn.disabled = state.busy || atMax;
    els.seedLimitNote.hidden = !atMax;
  }

  function hideFormError() { els.formError.hidden = true; els.formError.textContent = ""; }

  function showFormError(text) {
    els.formError.textContent = text;
    els.formError.hidden = false;
  }

  /* ---------- Profile strip ---------- */
  function renderProfile(profile) {
    state.lastProfile = profile || null;
    if (!profile) { els.profileStrip.hidden = true; return; }

    var resolved = Array.isArray(profile.resolved) ? profile.resolved : [];
    els.resolvedChips.innerHTML = resolved.map(function (item) {
      var domain = domainLabel(item.subtype);
      return (
        '<span class="resolved-chip">' + esc(item.name || item.seed || "") +
        (domain ? ' <span class="chip-domain">' + esc(domain) + "</span>" : "") +
        "</span>"
      );
    }).join("");

    els.tasteTags.innerHTML = (Array.isArray(profile.tags) ? profile.tags : []).map(function (tag) {
      var name = typeof tag === "string" ? tag : tag && tag.name;
      return name ? '<span class="tag-pill">' + esc(name) + "</span>" : "";
    }).join("");

    var unresolved = Array.isArray(profile.unresolved) ? profile.unresolved : [];
    els.unresolvedList.innerHTML = unresolved.map(function (seed) {
      return '<p class="unresolved-item">couldn&rsquo;t place: ' + esc(seed) + "</p>";
    }).join("");

    els.profileStrip.hidden = false;
  }

  /* ---------- Plan rendering ---------- */
  function renderPickCard(slotObj) {
    var meta = slotMeta(slotObj.slot);
    var pick = slotObj.pick;
    var head =
      '<p class="slot-label"><span class="slot-icon" aria-hidden="true">' + meta.icon + "</span>" + esc(meta.label) + "</p>";

    if (!pick) {
      return (
        '<li class="timeline-item"><article class="plan-card plan-card--empty">' + head +
        '<p class="empty-pick">No match in the taste graph for this one — try broadening your seeds.</p>' +
        "</article></li>"
      );
    }

    var pct = affinityPercent(pick.affinity);
    var affinityHtml = pct === null ? "" :
      '<div class="affinity">' +
        '<div class="affinity-head"><span>Taste-graph affinity</span>' +
        '<span class="affinity-value">' + pct + "%</span></div>" +
        '<div class="affinity-track"><div class="affinity-fill" style="width:' + pct + '%"></div></div>' +
      "</div>";

    var whyHtml = pick.why ?
      '<div class="why-block"><span class="why-prefix">Why this fits you —</span> ' + esc(pick.why) + "</div>" : "";

    var alternates = Array.isArray(slotObj.alternates) ? slotObj.alternates : [];
    var altNames = alternates
      .map(function (alt) { return alt && alt.name; })
      .filter(Boolean);
    var alternatesHtml = altNames.length ?
      '<p class="alternates"><span class="alternates-label">Also in the running:</span> ' +
      esc(altNames.join(", ")) + "</p>" : "";

    var subtype = domainLabel(pick.subtype);

    return (
      '<li class="timeline-item"><article class="plan-card">' + head +
      '<h3 class="pick-name">' + esc(pick.name || "") + "</h3>" +
      (subtype ? '<p class="pick-subtype">' + esc(subtype) + "</p>" : "") +
      (pick.description ? '<p class="pick-description">' + esc(pick.description) + "</p>" : "") +
      affinityHtml +
      whyHtml +
      tagPills(pick.tags) +
      alternatesHtml +
      "</article></li>"
    );
  }

  function renderPlan(plan) {
    state.lastPlan = plan;
    renderProfile(plan.profile);

    els.planIntro.textContent = plan.intro || "";
    var slots = Array.isArray(plan.slots) ? plan.slots : [];
    els.planTimeline.innerHTML = slots.map(renderPickCard).join("");

    var notes = plan.meta && Array.isArray(plan.meta.notes) ? plan.meta.notes : [];
    els.planNotes.textContent = notes.join("\n");
    els.planNotes.hidden = notes.length === 0;

    els.compareView.hidden = true;
    els.planView.hidden = false;
  }

  /* ---------- Plan request ---------- */
  function requestPlan() {
    var seeds = currentSeeds();
    if (seeds.length === 0) {
      showFormError("Add at least one favourite to plan your evening.");
      var first = seedInputs()[0];
      if (first) first.focus();
      return Promise.resolve();
    }
    hideFormError();
    state.lastSeeds = seeds;
    state.lastLocation = currentLocation();
    state.lastAction = { type: "plan" };

    var body = { seeds: seeds, refinements: Array.from(state.refinements) };
    if (state.lastLocation) body.location = state.lastLocation;

    setBusy(true);
    showLoading();
    return postJSON("/api/plan", body)
      .then(function (plan) {
        hideLoading();
        els.errorState.hidden = true;
        renderPlan(plan);
        els.planView.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function () {
        showError("We couldn't reach Kindred just now. Your favourites are still here — try again in a moment.");
      })
      .then(function () { setBusy(false); });
  }

  /* ---------- Comparison ---------- */
  function renderCompactWith(slotObj) {
    var meta = slotMeta(slotObj.slot);
    var pick = slotObj.pick;
    var head =
      '<p class="slot-label"><span class="slot-icon" aria-hidden="true">' + meta.icon + "</span>" + esc(meta.label) + "</p>";
    if (!pick) {
      return '<div class="compact-card">' + head +
        '<p class="empty-pick">No match in the taste graph for this one — try broadening your seeds.</p></div>';
    }
    return (
      '<div class="compact-card">' + head +
      '<h4 class="compact-name">' + esc(pick.name || "") + "</h4>" +
      (pick.description ? '<p class="compact-why">' + esc(pick.description) + "</p>" : "") +
      (pick.why ? '<p class="compact-why"><span class="why-prefix">Why this fits you —</span> ' + esc(pick.why) + "</p>" : "") +
      "</div>"
    );
  }

  function renderCompactWithout(slotObj) {
    var meta = slotMeta(slotObj.slot);
    return (
      '<div class="compact-card">' +
      '<p class="slot-label">' + esc(meta.label) + "</p>" +
      '<h4 class="compact-name">' + esc(slotObj.name || "") + "</h4>" +
      (slotObj.why ? '<p class="compact-why">' + esc(slotObj.why) + "</p>" : "") +
      "</div>"
    );
  }

  function renderCompare(data) {
    state.lastCompare = data;
    var withPlan = data.with_qloo || {};
    var without = data.without_qloo || {};
    var delta = data.delta || {};
    var evidence = delta.evidence_backed_picks || {};

    var withSlots = Array.isArray(withPlan.slots) ? withPlan.slots : [];
    var withoutSlots = Array.isArray(without.slots) ? without.slots : [];
    var totalWith = withSlots.length || delta.domains_covered || 0;
    var totalWithout = withoutSlots.length || totalWith;

    var withCount = typeof evidence.with_qloo === "number" ? evidence.with_qloo : 0;
    var withoutCount = typeof evidence.without_qloo === "number" ? evidence.without_qloo : 0;

    var subParts = [];
    if (typeof delta.taste_tags_used === "number") subParts.push("Taste tags used: " + delta.taste_tags_used);
    if (typeof delta.domains_covered === "number") subParts.push("Domains covered: " + delta.domains_covered);

    els.deltaBanner.innerHTML =
      "Evidence-backed picks: " + withCount + " of " + totalWith + " with Qloo · " +
      withoutCount + " of " + totalWithout + " without" +
      (subParts.length ? '<span class="delta-sub">' + esc(subParts.join(" · ")) + "</span>" : "");

    // Keep the comparison's left column in sync with the freshest plan data.
    if (withPlan.profile || withPlan.slots) renderProfile(withPlan.profile || state.lastProfile);
    els.compareWith.innerHTML = withSlots.map(renderCompactWith).join("");
    els.compareWithout.innerHTML = withoutSlots.map(renderCompactWithout).join("");

    // Verbatim from the response — no paraphrase, no added claims.
    els.baselineMethod.textContent = without.method || "";
    els.baselineMethod.hidden = !without.method;
    els.baselineNote.textContent = without.note || "";
    els.baselineNote.hidden = !without.note;

    els.planView.hidden = true;
    els.compareView.hidden = false;
  }

  function requestCompare() {
    var seeds = state.lastSeeds.length ? state.lastSeeds : currentSeeds();
    if (seeds.length === 0) {
      showFormError("Add at least one favourite to plan your evening.");
      return Promise.resolve();
    }
    state.lastAction = { type: "compare" };
    var body = { seeds: seeds };
    var location = state.lastLocation || currentLocation();
    if (location) body.location = location;

    setBusy(true);
    showLoading();
    return postJSON("/api/compare", body)
      .then(function (data) {
        hideLoading();
        els.errorState.hidden = true;
        if (data.with_qloo) state.lastPlan = data.with_qloo;
        renderCompare(data);
        els.compareView.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function () {
        showError("We couldn't build the comparison just now. Your plan is still here — try again in a moment.");
      })
      .then(function () { setBusy(false); });
  }

  function backToPlan() {
    els.compareView.hidden = true;
    if (state.lastPlan) {
      renderPlan(state.lastPlan);
      els.planView.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  /* ---------- Events ---------- */
  els.seedForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!state.busy) requestPlan();
  });

  els.addSeedBtn.addEventListener("click", addSeedField);

  Array.prototype.forEach.call(document.querySelectorAll(".refinement-btn"), function (btn) {
    btn.addEventListener("click", function () {
      var value = btn.getAttribute("data-refinement");
      if (!value || state.busy) return;
      if (state.refinements.has(value)) {
        state.refinements.delete(value);
        btn.setAttribute("aria-pressed", "false");
      } else {
        state.refinements.add(value);
        btn.setAttribute("aria-pressed", "true");
      }
      if (state.lastPlan || currentSeeds().length) requestPlan();
    });
  });

  els.compareBtn.addEventListener("click", function () {
    if (!state.busy) requestCompare();
  });

  els.backToPlanBtn.addEventListener("click", backToPlan);

  els.retryBtn.addEventListener("click", function () {
    if (state.busy) return;
    els.errorState.hidden = true;
    if (state.lastAction && state.lastAction.type === "compare") requestCompare();
    else requestPlan();
  });

  /* ---------- Init ---------- */
  loadHealth();
  loadPersonas();
  updateAddSeedState();
})();
