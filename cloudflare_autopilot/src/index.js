const ISRAEL_TZ = "Asia/Jerusalem";
const DAILY_MAX = 3;

function corsHeaders(extra = {}) {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    ...extra,
  };
}

function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: corsHeaders({
      "Content-Type": "application/json; charset=utf-8",
      ...extraHeaders,
    }),
  });
}

function getTzParts(date = new Date(), timeZone = ISRAEL_TZ) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  const map = {};
  for (const part of formatter.formatToParts(date)) {
    if (part.type !== "literal") {
      map[part.type] = part.value;
    }
  }
  return map;
}

function localDay(date = new Date(), timeZone = ISRAEL_TZ) {
  const p = getTzParts(date, timeZone);
  return `${p.year}-${p.month}-${p.day}`;
}

function computeIsraelDropCountdown({
  now = new Date(),
  publishedDay = "",
  dueDay = "",
  timeZone = ISRAEL_TZ,
  hour = 21,
} = {}) {
  const current = new Date(now);
  let targetDay = dueDay;
  if (publishedDay && /^\d{4}-\d{2}-\d{2}$/.test(publishedDay)) {
    const next = new Date(`${publishedDay}T12:00:00Z`);
    next.setUTCDate(next.getUTCDate() + 1);
    targetDay = next.toISOString().slice(0, 10);
  }
  targetDay = targetDay || localDay(current, timeZone);

  const [year, month, day] = targetDay.split("-").map(Number);
  const wallClock = Date.UTC(year, month - 1, day, Number(hour), 0, 0);
  let target = wallClock;
  for (let pass = 0; pass < 2; pass++) {
    const p = getTzParts(new Date(target), timeZone);
    target +=
      wallClock -
      Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  }

  const seconds = Math.max(0, Math.ceil((target - current.getTime()) / 1000));
  const hh = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  const israelParts = getTzParts(current, timeZone);

  return {
    status: seconds > 0 ? "countdown" : "awaiting",
    seconds,
    formatted: `${hh}:${mm}:${ss}`,
    due_day: targetDay,
    target_utc: new Date(target).toISOString(),
    israel_day: `${israelParts.year}-${israelParts.month}-${israelParts.day}`,
    israel_time: `${israelParts.hour}:${israelParts.minute}:${israelParts.second}`,
    timezone: timeZone,
    drop_hour: hour,
  };
}

async function sha256Hex(text) {
  const encoded = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function decodeXmlEntities(text) {
  return text
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'");
}

function parseSitemapEntries(xmlText, siteOrigin) {
  const entries = [];
  const seen = new Set();
  const urlBlockRe = /<url\b[^>]*>([\s\S]*?)<\/url>/gi;
  let match;
  while ((match = urlBlockRe.exec(xmlText)) !== null) {
    const block = match[1];
    const locMatch = /<loc\b[^>]*>([\s\S]*?)<\/loc>/i.exec(block);
    if (!locMatch) continue;
    const url = decodeXmlEntities(locMatch[1].trim());
    if (!url.startsWith(`${siteOrigin}/`)) continue;
    try {
      const parsed = new URL(url);
      if (parsed.origin !== siteOrigin || parsed.search || parsed.hash) continue;
    } catch {
      continue;
    }
    if (seen.has(url)) continue;
    seen.add(url);
    const lastmodMatch = /<lastmod\b[^>]*>([\s\S]*?)<\/lastmod>/i.exec(block);
    entries.push({
      url,
      lastmod: lastmodMatch ? lastmodMatch[1].trim() : "",
    });
  }

  if (entries.length === 0) {
    const locOnlyRe = /<loc\b[^>]*>([\s\S]*?)<\/loc>/gi;
    while ((match = locOnlyRe.exec(xmlText)) !== null) {
      const url = decodeXmlEntities(match[1].trim());
      if (!url.startsWith(`${siteOrigin}/`) || seen.has(url)) continue;
      try {
        const parsed = new URL(url);
        if (parsed.origin !== siteOrigin || parsed.search || parsed.hash) continue;
      } catch {
        continue;
      }
      seen.add(url);
      entries.push({ url, lastmod: "" });
    }
  }
  return entries;
}

async function queryStatusPayload(env) {
  const now = new Date();
  const [
    publishStatesRes,
    latestPublishedRes,
    ledgerRecentRes,
    ledgerCountRes,
    seoRecentRes,
    seoCountRes,
    redirectsCountRes,
    studioRecentRes,
    studioCountRes,
    cronRecentRes,
    cronCountRes,
    publishStateCountRes,
  ] = await env.DB.batch([
    env.DB.prepare(
      "SELECT day, status, reserved_count, baseline_count, utc_day, published_day, updated_at FROM daily_publish_state ORDER BY day DESC LIMIT 14"
    ),
    env.DB.prepare(
      "SELECT COALESCE(published_day, day) AS published_day FROM daily_publish_state WHERE status = 'published' ORDER BY day DESC LIMIT 1"
    ),
    env.DB.prepare(
      "SELECT id, day, catalog_id, product_id, source, created_at FROM daily_ledger ORDER BY id DESC LIMIT 20"
    ),
    env.DB.prepare("SELECT COUNT(*) AS count FROM daily_ledger"),
    env.DB.prepare(
      "SELECT id, run_at, engine, indexed_count, submitted_count, status, payload_json FROM seo_telemetry ORDER BY id DESC LIMIT 10"
    ),
    env.DB.prepare("SELECT COUNT(*) AS count FROM seo_telemetry"),
    env.DB.prepare("SELECT COUNT(*) AS count FROM redirects"),
    env.DB.prepare(
      "SELECT id, product_id, view_name, model, status, width, height, created_at FROM studio_generations ORDER BY id DESC LIMIT 10"
    ),
    env.DB.prepare("SELECT COUNT(*) AS count FROM studio_generations"),
    env.DB.prepare(
      "SELECT id, cron, action, status, details_json, ran_at FROM cron_runs ORDER BY id DESC LIMIT 10"
    ),
    env.DB.prepare("SELECT COUNT(*) AS count FROM cron_runs"),
    env.DB.prepare("SELECT COUNT(*) AS count FROM daily_publish_state"),
  ]);

  const publishedDay = latestPublishedRes.results?.[0]?.published_day || "";
  const countdown = computeIsraelDropCountdown({ now, publishedDay });

  return {
    ok: true,
    service: "fluxixo-autopilot",
    site_origin: env.SITE_ORIGIN || "https://www.fluxixo.shop",
    ai_provider: env.AI_PROVIDER || "google-ai-studio",
    transport_only: true,
    github_repo: env.GITHUB_REPO || "sayros2601-hub/aliradar-pro",
    default_gemini_image_model: env.DEFAULT_GEMINI_IMAGE_MODEL || "gemini-3-pro-image",
    default_gemini_text_model: env.DEFAULT_GEMINI_TEXT_MODEL || "gemini-4-argon",
    gemini_thinking_level: env.GEMINI_THINKING_LEVEL || "HIGH",
    gemini_image_size: env.GEMINI_IMAGE_SIZE || "1K",
    now_utc: now.toISOString(),
    published_day: publishedDay || null,
    countdown,
    d1_counts: {
      daily_publish_state: Number(publishStateCountRes.results?.[0]?.count || 0),
      daily_ledger: Number(ledgerCountRes.results?.[0]?.count || 0),
      seo_telemetry: Number(seoCountRes.results?.[0]?.count || 0),
      studio_generations: Number(studioCountRes.results?.[0]?.count || 0),
      redirects: Number(redirectsCountRes.results?.[0]?.count || 0),
      cron_runs: Number(cronCountRes.results?.[0]?.count || 0),
    },
    publish_state: publishStatesRes.results || [],
    ledger_recent: ledgerRecentRes.results || [],
    seo_recent: (seoRecentRes.results || []).map((row) => {
      let payload = null;
      try {
        payload = JSON.parse(row.payload_json);
      } catch {
        payload = row.payload_json;
      }
      return {
        id: row.id,
        run_at: row.run_at,
        engine: row.engine,
        indexed_count: row.indexed_count,
        submitted_count: row.submitted_count,
        status: row.status,
        payload,
      };
    }),
    studio_recent: studioRecentRes.results || [],
    cron_recent: (cronRecentRes.results || []).map((row) => {
      let details = null;
      try {
        details = JSON.parse(row.details_json);
      } catch {
        details = row.details_json;
      }
      return {
        id: row.id,
        cron: row.cron,
        action: row.action,
        status: row.status,
        details,
        ran_at: row.ran_at,
      };
    }),
    configured_secrets: {
      gemini_api_key: Boolean(env.GEMINI_API_KEY),
      gemini_image_api_key: Boolean(env.GEMINI_IMAGE_API_KEY),
      gemini_text_api_key: Boolean(env.GEMINI_TEXT_API_KEY),
      github_dispatch_token: Boolean(env.GITHUB_DISPATCH_TOKEN),
      autopilot_sync_token: Boolean(env.AUTOPILOT_SYNC_TOKEN),
      bing_webmaster: Boolean(env.BING_WEBMASTER_API_KEY),
      yandex_webmaster: Boolean(env.YANDEX_WEBMASTER_TOKEN),
      gsc_service_account: Boolean(env.GSC_SERVICE_ACCOUNT_JSON),
      cloudflare_token: Boolean(env.CLOUDFLARE_API_TOKEN),
    },
  };
}

function normalizeInputPath(rawPath) {
  let clean = (rawPath || "").trim();
  if (!clean) return "";
  if (/^https?:\/\//i.test(clean)) {
    try {
      clean = new URL(clean).pathname;
    } catch {
      return "";
    }
  }
  const qIdx = clean.indexOf("?");
  if (qIdx !== -1) clean = clean.slice(0, qIdx);
  const hIdx = clean.indexOf("#");
  if (hIdx !== -1) clean = clean.slice(0, hIdx);
  if (!clean.startsWith("/")) clean = `/${clean}`;
  return clean;
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function matchPatternRule(sourcePath, targetPath, inputPath) {
  const paramNames = [];
  let regexStr = "^";
  let idx = 0;

  while (idx < sourcePath.length) {
    const ch = sourcePath[idx];
    if (ch === "*") {
      paramNames.push("splat");
      regexStr += "(.*)";
      idx += 1;
    } else if (ch === ":") {
      let end = idx + 1;
      while (end < sourcePath.length && /[A-Za-z0-9_]/.test(sourcePath[end])) {
        end += 1;
      }
      const name = sourcePath.slice(idx + 1, end);
      paramNames.push(name);
      regexStr += "([^/]+)";
      idx = end;
    } else {
      regexStr += escapeRegex(ch);
      idx += 1;
    }
  }
  regexStr += "$";

  const re = new RegExp(regexStr);
  const match = re.exec(inputPath);
  if (!match) return null;

  let resolved = targetPath;
  paramNames.forEach((name, i) => {
    const val = match[i + 1] ?? "";
    if (name === "splat") {
      resolved = resolved.replaceAll(":splat", val);
    } else {
      resolved = resolved.replaceAll(`:${name}`, val);
    }
  });
  return resolved;
}

function ruleSpecificity(sourcePath) {
  const hasWildcard = sourcePath.includes("*") ? 1 : 0;
  const paramCount = (sourcePath.match(/:[A-Za-z0-9_]+/g) || []).length;
  const staticPrefixLen = sourcePath.split(/[:*]/)[0].length;
  return { hasWildcard, paramCount, staticPrefixLen };
}

async function resolveRedirect(env, inputPath) {
  const exact = await env.DB.prepare(
    "SELECT source_path, target_path, status_code FROM redirects WHERE source_path = ? LIMIT 1"
  )
    .bind(inputPath)
    .first();

  if (exact) {
    return {
      source_path: exact.source_path,
      target_path: exact.target_path,
      resolved_target: exact.target_path,
      status_code: exact.status_code || 301,
      match_type: "exact",
    };
  }

  const patternsRes = await env.DB.prepare(
    "SELECT source_path, target_path, status_code FROM redirects WHERE source_path LIKE '%:%' OR source_path LIKE '%*%'"
  ).all();

  const rules = (patternsRes.results || []).slice().sort((a, b) => {
    const sa = ruleSpecificity(a.source_path);
    const sb = ruleSpecificity(b.source_path);
    if (sa.hasWildcard !== sb.hasWildcard) return sa.hasWildcard - sb.hasWildcard;
    if (sb.staticPrefixLen !== sa.staticPrefixLen) {
      return sb.staticPrefixLen - sa.staticPrefixLen;
    }
    if (sa.paramCount !== sb.paramCount) return sa.paramCount - sb.paramCount;
    return b.source_path.length - a.source_path.length;
  });

  for (const rule of rules) {
    const resolved = matchPatternRule(rule.source_path, rule.target_path, inputPath);
    if (resolved !== null) {
      return {
        source_path: rule.source_path,
        target_path: rule.target_path,
        resolved_target: resolved,
        status_code: rule.status_code || 301,
        match_type: "pattern",
      };
    }
  }
  return null;
}

async function handleRedirects(request, env, url) {
  const rawPath = url.searchParams.get("path") || url.searchParams.get("source") || url.searchParams.get("url");
  const siteOrigin = env.SITE_ORIGIN || "https://www.fluxixo.shop";

  if (rawPath) {
    const normPath = normalizeInputPath(rawPath);
    if (!normPath) {
      return jsonResponse({ ok: false, error: "Invalid path parameter" }, 400);
    }
    const matched = await resolveRedirect(env, normPath);
    const shouldRedirect =
      url.searchParams.get("resolve") === "1" || url.searchParams.get("redirect") === "1";

    if (matched && shouldRedirect) {
      const targetUrl = new URL(matched.resolved_target, siteOrigin).toString();
      return Response.redirect(targetUrl, matched.status_code || 301);
    }

    return jsonResponse({
      ok: true,
      matched: Boolean(matched),
      input_path: normPath,
      rule: matched,
      location: matched ? new URL(matched.resolved_target, siteOrigin).toString() : null,
    });
  }

  const limitParam = Number.parseInt(url.searchParams.get("limit") || "1000", 10);
  const offsetParam = Number.parseInt(url.searchParams.get("offset") || "0", 10);
  const limit = Number.isFinite(limitParam) ? Math.min(Math.max(limitParam, 1), 5000) : 1000;
  const offset = Number.isFinite(offsetParam) ? Math.max(offsetParam, 0) : 0;

  const [countRes, rowsRes] = await env.DB.batch([
    env.DB.prepare("SELECT COUNT(*) AS total FROM redirects"),
    env.DB.prepare(
      "SELECT source_path, target_path, status_code FROM redirects ORDER BY source_path ASC LIMIT ? OFFSET ?"
    ).bind(limit, offset),
  ]);

  const total = Number(countRes.results?.[0]?.total || 0);
  const rules = rowsRes.results || [];
  return jsonResponse({
    ok: true,
    total,
    count: rules.length,
    limit,
    offset,
    rules,
  });
}

function base64ToUint8Array(base64Str) {
  const clean = base64Str.includes(",") ? base64Str.split(",").pop() : base64Str;
  const binary = atob(clean.trim());
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function detectImageMime(bytes) {
  if (bytes.length >= 4 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
    return "image/png";
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return "image/jpeg";
  }
  if (
    bytes.length >= 12 &&
    bytes[0] === 0x52 &&
    bytes[1] === 0x49 &&
    bytes[2] === 0x46 &&
    bytes[3] === 0x46 &&
    bytes[8] === 0x57 &&
    bytes[9] === 0x45 &&
    bytes[10] === 0x42 &&
    bytes[11] === 0x50
  ) {
    return "image/webp";
  }
  return "image/png";
}

const WORLD_BACKGROUNDS = {
  Техника: "#DFE5FB",
  Дом: "#F1E3CF",
  Кухня: "#D9EEDE",
  "В дороге": "#FBE7A6",
  Инструменты: "#FDD8C4",
  Уход: "#F8D9E6",
  Спорт: "#D3EDF5",
  "На природе": "#DFEAC4",
  Питомцы: "#E9DCF8",
};

const GEMINI_IMAGE_MODELS = [
  "gemini-3-pro-image",
  "gemini-nano-banana-2.1",
  "gemini-3.1-flash-image",
  "gemini-3.1-flash-lite-image",
  "gemini-3.1-flash-image-preview",
  "gemini-2.5-flash-image",
];

const GEMINI_VISION_MODELS = [
  "gemini-4-hydrogen",
  "gemini-3.8-flash",
  "gemini-3.7-flash",
  "gemini-3.5-flash",
  "gemini-3.5-flash-lite",
  "gemini-2.5-flash",
];

const GEMINI_COPY_MODELS = [
  "gemini-4-argon",
  "gemini-4-carbon",
  "gemini-4-hydrogen",
  "gemini-3.8-flash",
  "gemini-3.7-flash",
  "gemini-3.6-flash",
  "gemini-3.5-flash",
  "gemini-3.5-flash-lite",
  "gemini-3.1-flash-lite",
  "gemini-2.5-pro",
  "gemini-2.5-flash",
];

const RETRYABLE_GEMINI_STATUSES = new Set([400, 403, 404, 429, 500, 502, 503, 504]);

function normalizeHexColor(rawHex) {
  const cleaned = String(rawHex || "").trim();
  const match = /^#?([0-9a-fA-F]{6})$/.exec(cleaned);
  return match ? `#${match[1].toUpperCase()}` : "";
}

function resolveTargetBackgroundHex(rawHex, category) {
  const normalized = normalizeHexColor(rawHex);
  if (normalized) return normalized;
  const cat = String(category || "").trim();
  return WORLD_BACKGROUNDS[cat] || "";
}

function uint8ArrayToBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function isGeminiThinkingModel(modelName) {
  return (
    (modelName.includes("gemini-4") || modelName.includes("gemini-3")) &&
    !modelName.includes("lite")
  );
}

function resolveGeminiModelChain(preferredModels, fallbackModels) {
  const preferred = (Array.isArray(preferredModels) ? preferredModels : [preferredModels])
    .map((m) => (typeof m === "string" ? m.trim() : ""))
    .filter((m) => m.startsWith("gemini-"));
  return Array.from(new Set([...preferred, ...fallbackModels].filter(Boolean)));
}

function extractGeminiText(data) {
  const cParts = data?.candidates?.[0]?.content?.parts || [];
  return cParts
    .filter((p) => p && typeof p.text === "string" && !p.thought)
    .map((p) => p.text)
    .join("");
}

async function callGeminiModelChain({
  geminiKey,
  models,
  buildBody,
  extractResult,
  label,
  timeoutMs = 45000,
}) {
  let lastErr = null;
  for (const modelName of models) {
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
      modelName
    )}:generateContent`;
    let res;
    try {
      res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "x-goog-api-key": geminiKey,
        },
        body: JSON.stringify(buildBody(modelName)),
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch (err) {
      lastErr = new Error(
        `${label} network/timeout (${modelName}): ${err instanceof Error ? err.message : String(err)}`
      );
      continue;
    }
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      lastErr = new Error(`${label} HTTP ${res.status} (${modelName}): ${detail.slice(0, 240)}`);
      if (RETRYABLE_GEMINI_STATUSES.has(res.status)) continue;
      throw lastErr;
    }
    let data;
    try {
      data = await res.json();
    } catch (err) {
      lastErr = new Error(
        `${label} invalid JSON (${modelName}): ${err instanceof Error ? err.message : String(err)}`
      );
      continue;
    }
    const result = extractResult(data, modelName);
    if (result !== null && result !== undefined) {
      return result;
    }
    lastErr = new Error(`${label} returned empty response (${modelName})`);
  }
  throw lastErr || new Error(`${label} failed`);
}

async function parseStudioImagePayload(request) {
  const contentType = (request.headers.get("content-type") || "").toLowerCase();
  if (contentType.includes("multipart/form-data")) {
    const form = await request.formData();
    const maybeFile =
      form.get("input_image_0") ||
      form.get("reference_image") ||
      form.get("image") ||
      form.get("file");
    const refBlob =
      maybeFile && typeof maybeFile !== "string" && typeof maybeFile.arrayBuffer === "function"
        ? maybeFile
        : null;
    const fields = {};
    for (const [k, v] of form.entries()) {
      if (typeof v === "string") fields[k] = v;
    }
    return { fields, refBlob };
  }
  let body = {};
  try {
    const text = await request.text();
    if (text.trim()) body = JSON.parse(text);
  } catch {
    return { error: "Invalid JSON body", status: 400 };
  }
  let refBlob = null;
  if (typeof body.image_base64 === "string" && body.image_base64.trim()) {
    const bytes = base64ToUint8Array(body.image_base64);
    refBlob = new Blob([bytes], { type: detectImageMime(bytes) });
  }
  return { fields: body && typeof body === "object" ? body : {}, refBlob };
}

function buildStudioPrompt(rawPrompt, { backgroundHex = "", visualSpec = "" } = {}) {
  const trimmed = (rawPrompt || "").trim();
  const base = trimmed || "modern minimalist consumer electronics product";
  const targetHex = normalizeHexColor(backgroundHex);
  const spec = String(visualSpec || "").replace(/\s+/g, " ").trim();

  if (!targetHex && !spec && /#ffffff/i.test(base) && /studio/i.test(base)) {
    return base;
  }
  if (/Ultra-clean commercial industrial design studio product photograph/i.test(base) && /zero floor plane/i.test(base)) {
    return base;
  }

  const subject = spec ? `${base} (${spec})` : base;
  const bgHex = targetHex || "#FFFFFF";
  const bgDesc = targetHex
    ? `completely flat uniform seamless solid color void matching hex ${bgHex}`
    : "pure flat #FFFFFF solid white background with generous white margin on all sides";

  return (
    `Ultra-clean commercial industrial design studio product photograph of ONLY the exact single standalone ${subject} from the reference photo, ` +
    `floating weightless in mid-air centered in full uncropped view against a ${bgDesc}, faithfully keeping its true real silhouette, carry strap/handle, knobs, and proportions without distortion, ` +
    `zero floor plane, zero tabletop, zero floor shadow, zero drop shadow, zero ground reflection, zero surface, zero pedestal, zero vignette, no frame borders, no edge lines, even shadowless lighting, crisp edge separation, ` +
    `strictly remove all external collage boxes, inset cards, promotional banners, seller badges, overlaid marketing text, Chinese characters, watermarks, hands, people, and pets.`
  );
}

async function describeProductFromImage(
  geminiKey,
  refBlob,
  productHint = "",
  { preferredModel = "" } = {}
) {
  const rawBytes = new Uint8Array(await refBlob.arrayBuffer());
  if (!rawBytes.byteLength || rawBytes.byteLength > 6_000_000) {
    throw new Error("Reference image is empty or exceeds 6MB limit");
  }
  const hint = String(productHint || "").replace(/\s+/g, " ").trim().slice(0, 160);
  const promptText =
    `Describe ONLY the standalone physical product in this e-commerce image${hint ? ` ("${hint}")` : ""} ` +
    `in 2-3 concise visual sentences for a studio product photographer: overall silhouette, carry handle/strap or antenna if present, casing materials, colors, screen, knobs, and controls. ` +
    `CRITICAL: Describe ONLY the object floating alone; NEVER mention rocks, tables, surfaces, backgrounds, collage insets, promotional badges, overlaid text, digits, price tags, or hands.`;
  const parts = [
    { text: promptText },
    {
      inlineData: {
        mimeType: detectImageMime(rawBytes),
        data: uint8ArrayToBase64(rawBytes),
      },
    },
  ];
  const models = resolveGeminiModelChain(preferredModel, GEMINI_VISION_MODELS);
  return callGeminiModelChain({
    geminiKey,
    models,
    label: "Gemini vision",
    timeoutMs: 30000,
    buildBody: (modelName) => {
      const thinking = isGeminiThinkingModel(modelName);
      const generationConfig = {
        temperature: 0.15,
        maxOutputTokens: thinking ? 2048 : 350,
      };
      if (thinking) {
        generationConfig.thinkingConfig = { thinkingLevel: "LOW" };
      }
      return {
        contents: [{ role: "user", parts }],
        generationConfig,
      };
    },
    extractResult: (data, modelName) => {
      const visualSpec = extractGeminiText(data).replace(/\s+/g, " ").trim().slice(0, 550);
      return visualSpec ? { visualSpec, model: `gemini:${modelName}` } : null;
    },
  });
}

async function generateNanoBananaImage(
  geminiKey,
  studioPrompt,
  refBlob,
  { preferredModel = "gemini-3-pro-image", imageSize = "1K", aspectRatio = "1:1" } = {}
) {
  const parts = [{ text: studioPrompt }];
  if (refBlob) {
    const rawBytes = new Uint8Array(await refBlob.arrayBuffer());
    if (rawBytes.byteLength > 0 && rawBytes.byteLength <= 6_000_000) {
      parts.push({
        inlineData: {
          mimeType: detectImageMime(rawBytes),
          data: uint8ArrayToBase64(rawBytes),
        },
      });
    }
  }
  const models = resolveGeminiModelChain(preferredModel, GEMINI_IMAGE_MODELS);
  return callGeminiModelChain({
    geminiKey,
    models,
    label: "Nano Banana",
    timeoutMs: 55000,
    buildBody: () => ({
      contents: [{ role: "user", parts }],
      generationConfig: {
        responseModalities: ["IMAGE"],
        imageConfig: { aspectRatio, imageSize },
      },
    }),
    extractResult: (data, modelName) => {
      const cands = Array.isArray(data?.candidates) ? data.candidates : [];
      for (const cand of cands) {
        const cParts = Array.isArray(cand?.content?.parts) ? cand.content.parts : [];
        for (const p of cParts) {
          const inline = p?.inlineData || p?.inline_data;
          if (inline?.data) {
            return { bytes: base64ToUint8Array(inline.data), model: modelName };
          }
        }
      }
      return null;
    },
  });
}

function extractMessageText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => (typeof part === "string" ? part : part?.text || ""))
      .join("\n")
      .trim();
  }
  return "";
}

async function generateGeminiCopy(
  geminiKey,
  messages,
  {
    preferredModels = [],
    thinkingLevel = "HIGH",
    temperature = 0.25,
    maxTokens = 1800,
    jsonOutput = true,
  } = {}
) {
  const sysParts = [];
  const contents = [];
  for (const m of messages) {
    const text = m ? extractMessageText(m.content) : "";
    if (!text) continue;
    if (m.role === "system") {
      sysParts.push({ text });
    } else {
      contents.push({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text }],
      });
    }
  }
  const models = resolveGeminiModelChain(preferredModels, GEMINI_COPY_MODELS);
  const resolvedThinking = ["LOW", "MEDIUM", "HIGH"].includes(
    String(thinkingLevel || "HIGH").toUpperCase()
  )
    ? String(thinkingLevel || "HIGH").toUpperCase()
    : "HIGH";

  return callGeminiModelChain({
    geminiKey,
    models,
    label: "Gemini copy",
    timeoutMs: 45000,
    buildBody: (modelName) => {
      const isThinking = isGeminiThinkingModel(modelName);
      const generationConfig = {
        temperature,
        maxOutputTokens: isThinking ? 8192 : maxTokens,
      };
      if (jsonOutput) {
        generationConfig.responseMimeType = "application/json";
      }
      if (isThinking) {
        generationConfig.thinkingConfig = { thinkingLevel: resolvedThinking };
      }
      const body = {
        contents: contents.length ? contents : [{ role: "user", parts: [{ text: "" }] }],
        generationConfig,
      };
      if (sysParts.length) {
        body.systemInstruction = { parts: sysParts };
      }
      return body;
    },
    extractResult: (data, modelName) => {
      const content = extractGeminiText(data);
      return content.trim() ? { content, model: `gemini:${modelName}`, raw: data } : null;
    },
  });
}

function clampDim(val, fallback = 1024) {
  const parsed = Number.parseInt(String(val ?? fallback), 10);
  return Number.isFinite(parsed) ? Math.min(Math.max(parsed, 256), 2048) : fallback;
}

async function handleGenerateCutout(request, env, url) {
  const geminiKey = String(env.GEMINI_IMAGE_API_KEY || env.GEMINI_API_KEY || "").trim();
  if (!geminiKey) {
    return jsonResponse(
      { ok: false, error: "GEMINI_API_KEY not configured for Nano Banana image generation" },
      503
    );
  }

  const parsed = await parseStudioImagePayload(request);
  if (parsed.error) {
    return jsonResponse({ ok: false, error: parsed.error }, parsed.status || 400);
  }

  const { fields, refBlob } = parsed;
  const wantMeta =
    url.searchParams.get("meta") === "1" || url.searchParams.get("format") === "json";
  const rawPrompt = String(fields.prompt || "");
  const productId = String(fields.product_id || "studio-sample").trim() || "studio-sample";
  const viewName = String(fields.view_name || "main").trim() || "main";
  const rawBackgroundHex = String(fields.background_hex || fields.backgroundHex || "");
  const category = String(fields.category || "");
  let visualSpec = String(fields.visual_spec || fields.visualSpec || "");
  const width = clampDim(fields.width, 1024);
  const height = clampDim(fields.height, 1024);
  const aspectRatio = String(fields.aspect_ratio || fields.aspectRatio || "1:1").trim() || "1:1";
  const imageSize =
    String(fields.image_size || fields.imageSize || env.GEMINI_IMAGE_SIZE || "1K").trim() || "1K";
  const preferredModel =
    resolveGeminiModelChain(
      [fields.model, url.searchParams.get("model"), env.DEFAULT_GEMINI_IMAGE_MODEL],
      GEMINI_IMAGE_MODELS
    )[0] || "gemini-3-pro-image";

  if (!rawPrompt.trim() && !refBlob) {
    return jsonResponse(
      { ok: false, error: "Provide a prompt or reference image for studio generation" },
      400
    );
  }

  const targetHex = resolveTargetBackgroundHex(rawBackgroundHex, category);
  if (refBlob && !visualSpec.trim() && url.searchParams.get("use_vision") === "1") {
    try {
      const desc = await describeProductFromImage(geminiKey, refBlob, rawPrompt);
      visualSpec = desc.visualSpec;
    } catch {
      visualSpec = "";
    }
  }

  const studioPrompt = buildStudioPrompt(rawPrompt, { backgroundHex: targetHex, visualSpec });
  const createdAt = new Date().toISOString();
  let effectiveModel = preferredModel;

  try {
    const nanoRes = await generateNanoBananaImage(geminiKey, studioPrompt, refBlob, {
      preferredModel,
      imageSize,
      aspectRatio,
    });
    const imageBytes = nanoRes.bytes;
    effectiveModel = nanoRes.model;
    const mimeType = detectImageMime(imageBytes);

    const insertRes = await env.DB.prepare(
      "INSERT INTO studio_generations (product_id, view_name, model, status, width, height, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(productId, viewName, effectiveModel, "completed", width, height, createdAt)
      .run();

    const generationId = insertRes.meta?.last_row_id || null;

    if (wantMeta) {
      return jsonResponse({
        ok: true,
        id: generationId,
        product_id: productId,
        view_name: viewName,
        model: effectiveModel,
        provider: "google-ai-studio",
        status: "completed",
        width,
        height,
        bytes: imageBytes.byteLength,
        mime_type: mimeType,
        has_reference_image: Boolean(refBlob),
        background_hex: targetHex || "#FFFFFF",
        visual_spec: visualSpec,
        prompt_used: studioPrompt,
        created_at: createdAt,
      });
    }

    return new Response(imageBytes, {
      status: 200,
      headers: corsHeaders({
        "Content-Type": mimeType,
        "Cache-Control": "no-store",
        "X-Studio-Background-Hex": targetHex || "#FFFFFF",
        "X-Studio-Generation-Id": String(generationId || ""),
        "X-Studio-Product-Id": productId,
        "X-Studio-View-Name": viewName,
        "X-Studio-Model": effectiveModel,
        "X-Studio-Provider": "google-ai-studio",
      }),
    });
  } catch (err) {
    await env.DB.prepare(
      "INSERT INTO studio_generations (product_id, view_name, model, status, width, height, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(productId, viewName, effectiveModel, "error", width, height, createdAt)
      .run()
      .catch(() => {});

    return jsonResponse(
      {
        ok: false,
        product_id: productId,
        view_name: viewName,
        model: effectiveModel,
        provider: "google-ai-studio",
        status: "error",
        error: err instanceof Error ? err.message : String(err),
      },
      502
    );
  }
}

async function handleDescribeProduct(request, env) {
  const geminiKey = String(
    env.GEMINI_IMAGE_API_KEY || env.GEMINI_TEXT_API_KEY || env.GEMINI_API_KEY || ""
  ).trim();
  if (!geminiKey) {
    return jsonResponse(
      { ok: false, error: "GEMINI_API_KEY not configured for Google AI Studio product inspection" },
      503
    );
  }

  const parsed = await parseStudioImagePayload(request);
  if (parsed.error) {
    return jsonResponse({ ok: false, error: parsed.error }, parsed.status || 400);
  }

  const { fields, refBlob } = parsed;
  if (!refBlob) {
    return jsonResponse({ ok: false, error: "Provide an image for product inspection" }, 400);
  }

  const productHint = String(fields.prompt || fields.title || "");
  const preferredModel = typeof fields.model === "string" ? fields.model : "";
  try {
    const descRes = await describeProductFromImage(geminiKey, refBlob, productHint, {
      preferredModel,
    });
    return jsonResponse({
      ok: true,
      model: descRes.model,
      provider: "google-ai-studio",
      visual_spec: descRes.visualSpec,
    });
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        provider: "google-ai-studio",
        error: err instanceof Error ? err.message : String(err),
      },
      502
    );
  }
}

async function handleGenerateCopy(request, env) {
  const geminiCopyKey = String(env.GEMINI_TEXT_API_KEY || env.GEMINI_API_KEY || "").trim();
  if (!geminiCopyKey) {
    return jsonResponse(
      { ok: false, error: "GEMINI_API_KEY not configured for Google AI Studio copy generation" },
      503
    );
  }

  let body = {};
  try {
    const text = await request.text();
    if (text.trim()) body = JSON.parse(text);
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }

  const messages = Array.isArray(body.messages) ? body.messages : [];
  if (!messages.length) {
    return jsonResponse({ ok: false, error: "messages array is required" }, 400);
  }

  const temperature = Number.isFinite(Number(body.temperature)) ? Number(body.temperature) : 0.25;
  const maxTokens = Number.isFinite(Number(body.max_tokens))
    ? Math.min(Math.max(Number(body.max_tokens), 256), 8192)
    : 1800;

  try {
    const gemRes = await generateGeminiCopy(geminiCopyKey, messages, {
      preferredModels: [body.model, env.DEFAULT_GEMINI_TEXT_MODEL],
      thinkingLevel: String(
        body.thinking_level || env.GEMINI_THINKING_LEVEL || "HIGH"
      ).toUpperCase(),
      temperature,
      maxTokens,
      jsonOutput: (body.response_format?.type || "json_object") === "json_object",
    });
    return jsonResponse({
      ok: true,
      model: gemRes.model,
      provider: "google-ai-studio",
      choices: [{ message: { role: "assistant", content: gemRes.content } }],
      raw: gemRes.raw,
    });
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        provider: "google-ai-studio",
        error: err instanceof Error ? err.message : String(err),
      },
      502
    );
  }
}

async function fetchText(url, headers = {}) {
  const resp = await fetch(url, {
    headers: { "User-Agent": "FLUXIXO-Autopilot/1.0", ...headers },
    signal: AbortSignal.timeout(15000),
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status} fetching ${url}`);
  }
  return resp.text();
}

async function fetchJsonSafe(url, headers = {}) {
  try {
    const resp = await fetch(url, {
      headers: {
        "User-Agent": "FLUXIXO-Autopilot/1.0",
        Accept: "application/json",
        ...headers,
      },
      signal: AbortSignal.timeout(8000),
    });
    if (!resp.ok) return { ok: false, status: resp.status };
    return { ok: true, status: resp.status, data: await resp.json() };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

async function submitIndexNowBatch(endpoint, host, key, keyLocation, urls) {
  const batches = [];
  for (let i = 0; i < urls.length; i += 10000) {
    const urlList = urls.slice(i, i + 10000);
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "FLUXIXO-Autopilot/1.0",
      },
      body: JSON.stringify({ host, key, keyLocation, urlList }),
      signal: AbortSignal.timeout(15000),
    });
    const text = await resp.text().catch(() => "");
    batches.push({
      http_status: resp.status,
      urls: urlList.length,
      body_preview: text.slice(0, 120),
    });
  }
  const allAccepted =
    batches.length > 0 && batches.every((b) => b.http_status === 200 || b.http_status === 202);
  const all200 = batches.length > 0 && batches.every((b) => b.http_status === 200);
  const any429 = batches.some((b) => b.http_status === 429);
  return {
    status: all200
      ? "accepted"
      : allAccepted
      ? "key_validation_pending"
      : any429
      ? "rate_limited"
      : "error",
    submitted_count: allAccepted ? urls.length : 0,
    batches,
  };
}

async function getPreviousFingerprint(env, engine) {
  const row = await env.DB.prepare(
    "SELECT payload_json, status, run_at FROM seo_telemetry WHERE engine = ? AND status IN ('accepted', 'key_validation_pending', 'unchanged') ORDER BY id DESC LIMIT 1"
  )
    .bind(engine)
    .first();
  if (!row) return null;
  try {
    const parsed = JSON.parse(row.payload_json);
    return parsed?.fingerprint || null;
  } catch {
    return null;
  }
}

async function fetchExternalIndexedCounts(env, siteOrigin) {
  const result = {
    bing_quota: null,
    bing_status: null,
    yandex_searchable: null,
    yandex_status: null,
  };
  if (env.BING_WEBMASTER_API_KEY) {
    const siteParam = encodeURIComponent(`${siteOrigin}/`);
    const keyParam = encodeURIComponent(env.BING_WEBMASTER_API_KEY);
    const bingRes = await fetchJsonSafe(
      `https://ssl.bing.com/webmaster/api.svc/json/GetUrlSubmissionQuota?apikey=${keyParam}&siteUrl=${siteParam}`
    );
    result.bing_status = bingRes.status || (bingRes.ok ? 200 : "fetch_error");
    if (bingRes.ok && bingRes.data?.d) {
      result.bing_quota = {
        daily_quota: bingRes.data.d.DailyQuota ?? null,
        monthly_quota: bingRes.data.d.MonthlyQuota ?? null,
      };
    }
  }
  if (env.YANDEX_WEBMASTER_TOKEN) {
    const auth = { Authorization: `OAuth ${env.YANDEX_WEBMASTER_TOKEN}` };
    const userRes = await fetchJsonSafe("https://api.webmaster.yandex.net/v4/user", auth);
    result.yandex_status = userRes.status || (userRes.ok ? 200 : "fetch_error");
    const userId = userRes.ok ? userRes.data?.user_id : null;
    if (userId) {
      const hostsRes = await fetchJsonSafe(
        `https://api.webmaster.yandex.net/v4/user/${userId}/hosts`,
        auth
      );
      result.yandex_status = hostsRes.status || result.yandex_status;
      const hostObj = hostsRes.ok
        ? (hostsRes.data?.hosts || []).find((h) =>
            String(h.host_id || "").includes(new URL(siteOrigin).host)
          )
        : null;
      if (hostObj?.host_id) {
        const sumRes = await fetchJsonSafe(
          `https://api.webmaster.yandex.net/v4/user/${userId}/hosts/${encodeURIComponent(
            hostObj.host_id
          )}/summary`,
          auth
        );
        result.yandex_status = sumRes.status || result.yandex_status;
        if (sumRes.ok && sumRes.data) {
          result.yandex_searchable = sumRes.data.searchable_pages_count ?? null;
        }
      }
    }
  }
  return result;
}

async function runSeoSync(env, { source = "api", force = false } = {}) {
  const siteOrigin = env.SITE_ORIGIN || "https://www.fluxixo.shop";
  const host = new URL(siteOrigin).host;
  const key = env.INDEXNOW_KEY || "";
  if (!key) {
    throw new Error("INDEXNOW_KEY is not configured");
  }
  const keyLocation = `${siteOrigin}/${key}.txt`;
  const runAt = new Date().toISOString();

  const [globalXml, ruXml, keyCheckText, externalStats] = await Promise.all([
    fetchText(`${siteOrigin}/sitemap.xml`),
    fetchText(`${siteOrigin}/sitemap-ru.xml`),
    fetchText(keyLocation).catch(() => ""),
    fetchExternalIndexedCounts(env, siteOrigin),
  ]);

  const keyVerified = keyCheckText.trim() === key;
  const globalEntries = parseSitemapEntries(globalXml, siteOrigin);
  const ruEntries = parseSitemapEntries(ruXml, siteOrigin);
  const globalUrls = globalEntries.map((e) => e.url);
  const ruUrls = ruEntries.map((e) => e.url);

  const globalFingerprint = await sha256Hex(
    globalEntries.map((e) => `${e.url}|${e.lastmod}`).join("\n")
  );
  const ruFingerprint = await sha256Hex(
    ruEntries.map((e) => `${e.url}|${e.lastmod}`).join("\n")
  );

  const [prevGlobalFp, prevRuFp] = await Promise.all([
    getPreviousFingerprint(env, "indexnow_global"),
    getPreviousFingerprint(env, "indexnow_yandex"),
  ]);

  let globalResult;
  if (!force && prevGlobalFp && prevGlobalFp === globalFingerprint) {
    globalResult = {
      engine: "indexnow_global",
      endpoint: "https://api.indexnow.org/indexnow",
      status: "unchanged",
      total_urls: globalUrls.length,
      submitted_count: 0,
      indexed_count: 0,
      fingerprint: globalFingerprint,
      key_verified: keyVerified,
      source,
      bing_status: externalStats.bing_status,
      bing_quota: externalStats.bing_quota,
    };
  } else {
    const res = await submitIndexNowBatch(
      "https://api.indexnow.org/indexnow",
      host,
      key,
      keyLocation,
      globalUrls
    );
    globalResult = {
      engine: "indexnow_global",
      endpoint: "https://api.indexnow.org/indexnow",
      status: res.status,
      total_urls: globalUrls.length,
      submitted_count: res.submitted_count,
      indexed_count: 0,
      batches: res.batches,
      fingerprint: globalFingerprint,
      key_verified: keyVerified,
      source,
      bing_status: externalStats.bing_status,
      bing_quota: externalStats.bing_quota,
    };
  }

  let yandexResult;
  if (!force && prevRuFp && prevRuFp === ruFingerprint) {
    yandexResult = {
      engine: "indexnow_yandex",
      endpoint: "https://yandex.com/indexnow",
      status: "unchanged",
      total_urls: ruUrls.length,
      submitted_count: 0,
      indexed_count: Number(externalStats.yandex_searchable || 0),
      fingerprint: ruFingerprint,
      key_verified: keyVerified,
      source,
      yandex_status: externalStats.yandex_status,
    };
  } else {
    const res = await submitIndexNowBatch(
      "https://yandex.com/indexnow",
      host,
      key,
      keyLocation,
      ruUrls
    );
    yandexResult = {
      engine: "indexnow_yandex",
      endpoint: "https://yandex.com/indexnow",
      status: res.status,
      total_urls: ruUrls.length,
      submitted_count: res.submitted_count,
      indexed_count: Number(externalStats.yandex_searchable || 0),
      batches: res.batches,
      fingerprint: ruFingerprint,
      key_verified: keyVerified,
      source,
      yandex_status: externalStats.yandex_status,
    };
  }

  await env.DB.batch([
    env.DB.prepare(
      "INSERT INTO seo_telemetry (run_at, engine, indexed_count, submitted_count, status, payload_json) VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(
      runAt,
      globalResult.engine,
      globalResult.indexed_count,
      globalResult.submitted_count,
      globalResult.status,
      JSON.stringify(globalResult)
    ),
    env.DB.prepare(
      "INSERT INTO seo_telemetry (run_at, engine, indexed_count, submitted_count, status, payload_json) VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(
      runAt,
      yandexResult.engine,
      yandexResult.indexed_count,
      yandexResult.submitted_count,
      yandexResult.status,
      JSON.stringify(yandexResult)
    ),
  ]);

  return {
    ok: globalResult.status !== "error" && yandexResult.status !== "error",
    run_at: runAt,
    site_origin: siteOrigin,
    key_verified: keyVerified,
    force,
    source,
    engines: {
      indexnow_global: globalResult,
      indexnow_yandex: yandexResult,
    },
  };
}

async function handleSeoSync(request, env, url) {
  let force = url.searchParams.get("force") === "1";
  try {
    const text = await request.text();
    if (text.trim()) {
      const body = JSON.parse(text);
      if (body && body.force === true) force = true;
    }
  } catch {
    // Empty or non-JSON body falls back to query param.
  }

  try {
    const report = await runSeoSync(env, { source: "api", force });
    return jsonResponse(report, report.ok ? 200 : 502);
  } catch (err) {
    const runAt = new Date().toISOString();
    const message = err instanceof Error ? err.message : String(err);
    await env.DB.prepare(
      "INSERT INTO seo_telemetry (run_at, engine, indexed_count, submitted_count, status, payload_json) VALUES (?, ?, ?, ?, ?, ?)"
    )
      .bind(runAt, "indexnow_sync", 0, 0, "error", JSON.stringify({ error: message, source: "api" }))
      .run()
      .catch(() => {});
    return jsonResponse({ ok: false, run_at: runAt, error: message }, 502);
  }
}

const ALLOWED_DISPATCH_WORKFLOWS = new Map([
  ["fluxixo_daily_rotate.yml", "fluxixo_daily_rotate.yml"],
  ["daily_rotate", "fluxixo_daily_rotate.yml"],
  ["rotate", "fluxixo_daily_rotate.yml"],
  ["fluxixo_seo_daily.yml", "fluxixo_seo_daily.yml"],
  ["seo_daily", "fluxixo_seo_daily.yml"],
  ["seo", "fluxixo_seo_daily.yml"],
]);

function hasValidSyncAuth(request, expectedToken) {
  const auth = String(request.headers.get("Authorization") || "").trim();
  if (!auth.toLowerCase().startsWith("bearer ")) return false;
  const provided = auth.slice(7).trim();
  if (provided.length !== expectedToken.length) return false;
  let diff = 0;
  for (let i = 0; i < expectedToken.length; i++) {
    diff |= provided.charCodeAt(i) ^ expectedToken.charCodeAt(i);
  }
  return diff === 0;
}

async function dispatchGitHubWorkflow(env, workflowFile, inputs = {}) {
  const token = String(env.GITHUB_DISPATCH_TOKEN || "").trim();
  const repo = String(env.GITHUB_REPO || "sayros2601-hub/aliradar-pro").trim();
  const ref = "main";
  const cleanInputs = {};
  if (inputs && typeof inputs === "object") {
    for (const [key, value] of Object.entries(inputs)) {
      if (value !== undefined && value !== null) {
        cleanInputs[key] = String(value);
      }
    }
  }
  if (!token) {
    return {
      ok: false,
      skipped: true,
      http_status: null,
      repo,
      workflow: workflowFile,
      ref,
      inputs: cleanInputs,
      error: "GITHUB_DISPATCH_TOKEN not configured",
    };
  }

  const endpoint = `https://api.github.com/repos/${repo}/actions/workflows/${encodeURIComponent(
    workflowFile
  )}/dispatches`;
  const payload = Object.keys(cleanInputs).length
    ? { ref, inputs: cleanInputs }
    : { ref };

  try {
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "FLUXIXO-Autopilot/2.0",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(15000),
    });
    const bodyText = await resp.text().catch(() => "");
    return {
      ok: resp.status === 204 || resp.ok,
      skipped: false,
      http_status: resp.status,
      repo,
      workflow: workflowFile,
      ref,
      inputs: cleanInputs,
      error: resp.ok ? null : bodyText.slice(0, 300) || `GitHub HTTP ${resp.status}`,
    };
  } catch (err) {
    return {
      ok: false,
      skipped: false,
      http_status: null,
      repo,
      workflow: workflowFile,
      ref,
      inputs: cleanInputs,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

async function handleDispatch(request, env, url) {
  const syncToken = String(env.AUTOPILOT_SYNC_TOKEN || "").trim();
  if (syncToken && !hasValidSyncAuth(request, syncToken)) {
    return jsonResponse({ ok: false, error: "Unauthorized" }, 401);
  }
  if (!String(env.GITHUB_DISPATCH_TOKEN || "").trim()) {
    return jsonResponse({ ok: false, error: "GITHUB_DISPATCH_TOKEN not configured" }, 503);
  }

  let body = {};
  try {
    const text = await request.text();
    if (text.trim()) body = JSON.parse(text);
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }

  const rawWorkflow = String(body?.workflow || url.searchParams.get("workflow") || "").trim();
  const workflowFile = ALLOWED_DISPATCH_WORKFLOWS.get(rawWorkflow);
  if (!workflowFile) {
    return jsonResponse(
      {
        ok: false,
        error:
          "Invalid or missing workflow; expected fluxixo_daily_rotate.yml or fluxixo_seo_daily.yml",
      },
      400
    );
  }

  const inputs =
    body?.inputs && typeof body.inputs === "object" && !Array.isArray(body.inputs)
      ? { ...body.inputs }
      : {};
  const addCountParam = body?.add_count ?? url.searchParams.get("add_count");
  if (workflowFile === "fluxixo_daily_rotate.yml") {
    if (addCountParam !== undefined && addCountParam !== null && String(addCountParam).trim() !== "") {
      inputs.add_count = String(addCountParam).trim();
    } else if (inputs.add_count === undefined) {
      inputs.add_count = "auto";
    }
  }

  const result = await dispatchGitHubWorkflow(env, workflowFile, inputs);
  const ranAt = new Date().toISOString();
  await env.DB.prepare(
    "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
  )
    .bind(
      "api-dispatch",
      workflowFile,
      result.ok ? "ok" : "error",
      JSON.stringify(result),
      ranAt
    )
    .run()
    .catch(() => {});

  return jsonResponse({ ...result, dispatched_at: ranAt }, result.ok ? 200 : 502);
}

async function runScheduledAction(controller, env) {
  const cron = controller.cron || "manual";
  const ranAt = new Date().toISOString();
  const now = new Date();
  const israelToday = localDay(now, ISRAEL_TZ);
  const utcToday = now.toISOString().slice(0, 10);

  if (cron === "17 5 * * *") {
    let seoReport = null;
    let seoError = null;
    try {
      seoReport = await runSeoSync(env, { source: "cron", force: false });
    } catch (err) {
      seoError = err instanceof Error ? err.message : String(err);
    }

    const dispatchRes = env.GITHUB_DISPATCH_TOKEN
      ? await dispatchGitHubWorkflow(env, "fluxixo_seo_daily.yml")
      : {
          ok: false,
          skipped: true,
          http_status: null,
          workflow: "fluxixo_seo_daily.yml",
          reason: "GITHUB_DISPATCH_TOKEN not configured",
        };

    const seoOk = Boolean(seoReport?.ok);
    const dispatchOk = !env.GITHUB_DISPATCH_TOKEN || dispatchRes.ok;
    const status =
      seoError && !dispatchRes.ok
        ? "error"
        : seoOk && dispatchOk
        ? "ok"
        : "partial_error";

    const details = {
      ...(seoReport || { ok: false, error: seoError }),
      dispatch_http_status: dispatchRes.http_status,
      github_dispatch: dispatchRes,
    };

    await env.DB.prepare(
      "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
    )
      .bind(cron, "seo_sync", status, JSON.stringify(details), ranAt)
      .run();
    return;
  }

  const [todayState, utcLedgerCount, latestPublished] = await env.DB.batch([
    env.DB.prepare(
      "SELECT day, status, reserved_count, baseline_count, utc_day, published_day FROM daily_publish_state WHERE day = ? LIMIT 1"
    ).bind(israelToday),
    env.DB.prepare("SELECT COUNT(*) AS count FROM daily_ledger WHERE day = ?").bind(utcToday),
    env.DB.prepare(
      "SELECT COALESCE(published_day, day) AS published_day FROM daily_publish_state WHERE status = 'published' ORDER BY day DESC LIMIT 1"
    ),
  ]);

  const publishedDay = latestPublished.results?.[0]?.published_day || "";
  const countdown = computeIsraelDropCountdown({ now, publishedDay });
  const doneToday = Number(utcLedgerCount.results?.[0]?.count || 0);
  const remainingAllowance = Math.max(0, DAILY_MAX - doneToday);
  const stateRow = todayState.results?.[0] || null;

  const dispatchRes = env.GITHUB_DISPATCH_TOKEN
    ? await dispatchGitHubWorkflow(env, "fluxixo_daily_rotate.yml", { add_count: "auto" })
    : {
        ok: false,
        skipped: true,
        http_status: null,
        workflow: "fluxixo_daily_rotate.yml",
        inputs: { add_count: "auto" },
        reason: "GITHUB_DISPATCH_TOKEN not configured",
      };

  const israelHour = Number(getTzParts(now, ISRAEL_TZ).hour || 0);
  const action =
    cron === "0 17 * * *" || (israelHour >= 18 && israelHour < 21)
      ? "prepare_window_check"
      : "drop_2100_check";
  const status = !env.GITHUB_DISPATCH_TOKEN || dispatchRes.ok ? "ok" : "dispatch_error";
  const details = {
    israel_today: israelToday,
    utc_today: utcToday,
    utc_ledger_done: doneToday,
    remaining_allowance: remainingAllowance,
    today_publish_state: stateRow,
    published_day: publishedDay || null,
    countdown,
    dispatch_http_status: dispatchRes.http_status,
    github_dispatch: dispatchRes,
  };

  await env.DB.prepare(
    "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
  )
    .bind(cron, action, status, JSON.stringify(details), ranAt)
    .run();
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "GET" && (path === "/" || path === "/api/status")) {
      const payload = await queryStatusPayload(env);
      return jsonResponse(payload);
    }

    if (request.method === "GET" && path === "/drop-status.json") {
      const payload = await queryStatusPayload(env);
      return jsonResponse(
        {
          published_day: payload.published_day,
          due_day: payload.countdown.due_day,
          status: payload.countdown.status,
          seconds_remaining: payload.countdown.seconds,
          countdown: payload.countdown,
          israel_day: payload.countdown.israel_day,
          utc_day: payload.now_utc.slice(0, 10),
          latest_state: payload.publish_state[0] || null,
        },
        200,
        { "Cache-Control": "no-store" }
      );
    }

    if (request.method === "GET" && path === "/api/redirects") {
      return handleRedirects(request, env, url);
    }

    if (request.method === "POST" && path === "/api/generate-cutout") {
      return handleGenerateCutout(request, env, url);
    }

    if (request.method === "POST" && path === "/api/describe-product") {
      return handleDescribeProduct(request, env);
    }

    if (request.method === "POST" && path === "/api/generate-copy") {
      return handleGenerateCopy(request, env);
    }

    if (request.method === "POST" && path === "/api/dispatch") {
      return handleDispatch(request, env, url);
    }

    if (request.method === "POST" && path === "/api/seo-sync") {
      return handleSeoSync(request, env, url);
    }

    if (request.method === "POST" && path === "/api/catalog-sync") {
      let body = {};
      try {
        const text = await request.text();
        if (text.trim()) body = JSON.parse(text);
      } catch {
        return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
      }
      const event = String(body.event || "catalog_sync").slice(0, 120);
      const ranAt = new Date().toISOString();
      const syncToken = String(env.AUTOPILOT_SYNC_TOKEN || "").trim();
      const isAuthed = !syncToken || hasValidSyncAuth(request, syncToken);
      const dbOps = [
        env.DB.prepare(
          "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
        ).bind("external-sync", event, "ok", JSON.stringify(body), ranAt),
      ];
      if (isAuthed && body.publish_state && typeof body.publish_state === "object") {
        const psDays = body.publish_state.days && typeof body.publish_state.days === "object"
          ? body.publish_state.days
          : body.publish_state;
        for (const [day, row] of Object.entries(psDays)) {
          if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !row || typeof row !== "object") continue;
          dbOps.push(
            env.DB.prepare(
              "INSERT OR REPLACE INTO daily_publish_state (day, status, reserved_count, baseline_count, utc_day, published_day, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
            ).bind(
              day,
              String(row.status || "published"),
              Number(row.reserved_count || 0),
              Number(row.baseline_count || 0),
              String(row.utc_day || day),
              row.published_day ? String(row.published_day) : null,
              ranAt
            )
          );
        }
      }
      if (isAuthed && body.ledger_days && typeof body.ledger_days === "object") {
        for (const [day, rows] of Object.entries(body.ledger_days)) {
          if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Array.isArray(rows)) continue;
          for (const row of rows) {
            if (!row || typeof row !== "object" || !row.catalog_id) continue;
            dbOps.push(
              env.DB.prepare(
                "INSERT OR IGNORE INTO daily_ledger (day, catalog_id, product_id, source, created_at) VALUES (?, ?, ?, ?, ?)"
              ).bind(
                day,
                String(row.catalog_id),
                row.product_id ? String(row.product_id) : null,
                String(row.source || "api"),
                ranAt
              )
            );
          }
        }
      }
      await env.DB.batch(dbOps);
      return jsonResponse({ ok: true, synced: true, event, recorded_at: ranAt });
    }

    return jsonResponse(
      {
        ok: false,
        error: "Not Found",
        routes: [
          "GET /",
          "GET /api/status",
          "GET /drop-status.json",
          "GET /api/redirects",
          "POST /api/describe-product",
          "POST /api/generate-cutout",
          "POST /api/generate-copy",
          "POST /api/dispatch",
          "POST /api/seo-sync",
          "POST /api/catalog-sync",
        ],
      },
      404
    );
  },

  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runScheduledAction(controller, env));
  },
};
