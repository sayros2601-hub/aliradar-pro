// Daily schedule (owner, 2026-11-20): prepare from 13:30 and publish at 15:30 Israel time (Asia/Jerusalem).
const DROP_TZ = "Asia/Jerusalem";
const DAILY_MAX = 1;
const SERVICE_HEALTH = { ok: true, service: "fluxixo-autopilot" };
const NO_STORE = { "Cache-Control": "no-store" };
const LATEST_PUBLISHED_DAY_SQL =
  "SELECT COALESCE(published_day, day) AS published_day FROM daily_publish_state WHERE status = 'published' ORDER BY day DESC LIMIT 1";

function corsHeaders(extra = {}) {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Fluxixo-Sha256",
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

function getTzParts(date = new Date(), timeZone = DROP_TZ) {
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

function localDay(date = new Date(), timeZone = DROP_TZ) {
  const p = getTzParts(date, timeZone);
  return `${p.year}-${p.month}-${p.day}`;
}

function computeIsraelDropCountdown({
  now = new Date(),
  publishedDay = "",
  dueDay = "",
  timeZone = DROP_TZ,
  hour = 15,
  minute = 30,
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
  const wallClock = Date.UTC(year, month - 1, day, Number(hour), Number(minute), 0);
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
    // israel_day / israel_time keep their old names for existing readers; the values are in `timezone`.
    israel_day: `${israelParts.year}-${israelParts.month}-${israelParts.day}`,
    israel_time: `${israelParts.hour}:${israelParts.minute}:${israelParts.second}`,
    timezone: timeZone,
    drop_hour: Number(hour),
    drop_minute: Number(minute),
    drop_time: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
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

async function queryPublicStatusPayload(env, now = new Date()) {
  const row = await env.DB.prepare(LATEST_PUBLISHED_DAY_SQL).first();
  const publishedDay = row?.published_day || null;
  return {
    ...SERVICE_HEALTH,
    published_day: publishedDay,
    countdown: computeIsraelDropCountdown({ now, publishedDay }),
  };
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
    env.DB.prepare(LATEST_PUBLISHED_DAY_SQL),
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
    ...SERVICE_HEALTH,
    site_origin: env.SITE_ORIGIN || "https://www.fluxixo.shop",
    media_origin: env.MEDIA_ORIGIN || "https://media.fluxixo.shop",
    r2_media_bound: Boolean(env.MEDIA_BUCKET),
    r2_media_bucket: "fluxixo",
    ai_provider: env.AI_PROVIDER || "cloudflare-workers-ai",
    workers_ai_bound: Boolean(env.AI),
    github_repo: env.GITHUB_REPO || "sayros2601-hub/aliradar-pro",
    default_image_model: env.DEFAULT_IMAGE_MODEL || "@cf/black-forest-labs/flux-2-klein-9b",
    fallback_image_model: env.FALLBACK_IMAGE_MODEL || "@cf/black-forest-labs/flux-2-klein-4b",
    default_text_model: env.DEFAULT_TEXT_MODEL || "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    default_vision_model: env.DEFAULT_VISION_MODEL || "@cf/meta/llama-4-scout-17b-16e-instruct",
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
      workers_ai: Boolean(env.AI),
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

const CF_IMAGE_MODELS = [
  "@cf/black-forest-labs/flux-2-klein-9b",
  "@cf/black-forest-labs/flux-2-klein-4b",
];

const CF_VISION_MODELS = [
  "@cf/meta/llama-4-scout-17b-16e-instruct",
  "@cf/mistralai/mistral-small-3.1-24b-instruct",
  "@cf/qwen/qwen3.8-27b",
];

const CF_COPY_MODELS = [
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  "@cf/qwen/qwen3.8-27b",
  "@cf/zai-org/glm-4.7-flash",
  "@cf/openai/gpt-oss-120b",
];

function normalizeHexColor(rawHex) {
  const cleaned = String(rawHex || "").trim();
  const match = /^#?([0-9a-fA-F]{6})$/.exec(cleaned);
  return match ? `#${match[1].toUpperCase()}` : "";
}

function resolveTargetBackgroundHex(rawHex, category, { allowWorldBg = false } = {}) {
  const normalized = normalizeHexColor(rawHex);
  if (normalized) return normalized;
  if (allowWorldBg) {
    const cat = String(category || "").trim();
    return WORLD_BACKGROUNDS[cat] || "#FFFFFF";
  }
  // Default to pure neutral studio white (#FFFFFF) so downstream transparent RGBA cutout extraction
  // never suffers bright category-backdrop color cast or mismatched colored squares on the storefront.
  return "#FFFFFF";
}

function uint8ArrayToBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function resolveCfModelChain(preferredModels, fallbackModels) {
  const preferred = (Array.isArray(preferredModels) ? preferredModels : [preferredModels])
    .map((m) => (typeof m === "string" ? m.trim().replace(/^\/+/, "") : ""))
    .filter((m) => m.startsWith("@cf/"));
  return Array.from(new Set([...preferred, ...fallbackModels].filter(Boolean)));
}

async function extractAiImageBytes(aiResult) {
  if (!aiResult) {
    throw new Error("Workers AI returned empty response");
  }
  if (aiResult instanceof ReadableStream) {
    return new Uint8Array(await new Response(aiResult).arrayBuffer());
  }
  if (aiResult instanceof Response) {
    return new Uint8Array(await aiResult.arrayBuffer());
  }
  if (aiResult instanceof ArrayBuffer) {
    return new Uint8Array(aiResult);
  }
  if (ArrayBuffer.isView(aiResult)) {
    return new Uint8Array(aiResult.buffer, aiResult.byteOffset, aiResult.byteLength);
  }
  if (typeof aiResult === "object" && typeof aiResult.image === "string") {
    return base64ToUint8Array(aiResult.image);
  }
  if (typeof aiResult === "object" && aiResult.result && typeof aiResult.result.image === "string") {
    return base64ToUint8Array(aiResult.result.image);
  }
  if (typeof aiResult === "string") {
    return base64ToUint8Array(aiResult);
  }
  throw new Error("Unsupported Workers AI image output shape");
}

function stripReasoningTags(text) {
  return String(text || "")
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .trim();
}

function extractAiChatText(aiRes) {
  if (!aiRes) return "";
  if (typeof aiRes === "string") return stripReasoningTags(aiRes);
  if (typeof aiRes?.response === "string") return stripReasoningTags(aiRes.response);
  if (typeof aiRes?.response === "object" && aiRes.response !== null) {
    return JSON.stringify(aiRes.response);
  }
  const choiceMsg = aiRes?.choices?.[0]?.message?.content;
  if (typeof choiceMsg === "string") return stripReasoningTags(choiceMsg);
  if (typeof choiceMsg === "object" && choiceMsg !== null) return JSON.stringify(choiceMsg);
  const nestedMsg = aiRes?.result?.choices?.[0]?.message?.content;
  if (typeof nestedMsg === "string") return stripReasoningTags(nestedMsg);
  if (typeof aiRes?.result?.response === "string") return stripReasoningTags(aiRes.result.response);
  return "";
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
  const isNeutralWhite = !targetHex || bgHex === "#FFFFFF";
  const bgDesc = isNeutralWhite
    ? "pure flat #FFFFFF solid white background with generous white margin on all sides"
    : `completely flat uniform seamless solid color void matching hex ${bgHex}`;
  const lightingDesc = isNeutralWhite
    ? "neutral color-accurate even shadowless studio lighting with zero colored backdrop cast on silver, metal, or white surfaces"
    : "even shadowless lighting";

  return (
    `Ultra-clean commercial industrial design studio product photograph of ONLY the exact single standalone ${subject} from the reference photo, ` +
    `floating weightless in mid-air centered in full uncropped view against a ${bgDesc}, faithfully keeping its true real silhouette, parts, colors, and proportions without distortion, ` +
    `zero floor plane, zero tabletop, zero floor shadow, zero drop shadow, zero ground reflection, zero surface, zero pedestal, zero vignette, no frame borders, no edge lines, ${lightingDesc}, crisp edge separation, ` +
    `unbranded label-free clean surfaces that keep only the real button symbols, ` +
    `strictly remove all external collage boxes, inset cards, promotional banners, seller badges, overlaid marketing captions, watermarks, hands, people, and pets.`
  );
}

async function describeProductFromImage(
  env,
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
    `in 2-3 concise visual sentences for a studio product photographer: overall silhouette, casing materials, colors, ` +
    `and any handle, strap, antenna, screen, or controls it really has. ` +
    `Mention a switched-on effect (built-in light, laser beam, lit screen, or mist) ONLY if this exact product clearly has that light source, screen, or mist outlet; ` +
    `never invent lights, glow, or effects, and leave out features it does not have. ` +
    `CRITICAL: Describe ONLY the object floating alone; NEVER mention rocks, tables, surfaces, backgrounds, collage insets, promotional badges, overlaid text, digits, price tags, or hands.`;
  const dataUri = `data:${detectImageMime(rawBytes)};base64,${uint8ArrayToBase64(rawBytes)}`;
  const models = resolveCfModelChain([preferredModel, env.DEFAULT_VISION_MODEL], CF_VISION_MODELS);
  let lastErr = null;
  for (const modelName of models) {
    try {
      const aiRes = await env.AI.run(modelName, {
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: promptText },
              { type: "image_url", image_url: { url: dataUri } },
            ],
          },
        ],
        temperature: 0.15,
        max_tokens: 400,
      });
      const visualSpec = extractAiChatText(aiRes).replace(/\s+/g, " ").trim().slice(0, 550);
      if (visualSpec) {
        return { visualSpec, model: modelName };
      }
      lastErr = new Error(`Cloudflare vision returned empty text (${modelName})`);
    } catch (err) {
      lastErr = new Error(
        `Cloudflare vision error (${modelName}): ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }
  throw lastErr || new Error("Cloudflare vision failed");
}

async function generateCloudflareFluxImage(
  env,
  studioPrompt,
  refBlob,
  { preferredModels = [], width = 1024, height = 1024 } = {}
) {
  const models = resolveCfModelChain(
    [...preferredModels, env.DEFAULT_IMAGE_MODEL, env.FALLBACK_IMAGE_MODEL],
    CF_IMAGE_MODELS
  );
  const refBytes = refBlob ? new Uint8Array(await refBlob.arrayBuffer()) : null;
  const refMime = refBlob?.type || (refBytes ? detectImageMime(refBytes) : "image/png");
  let lastErr = null;
  for (const modelName of models) {
    try {
      const aiForm = new FormData();
      aiForm.append("prompt", studioPrompt);
      aiForm.append("width", String(width));
      aiForm.append("height", String(height));
      if (refBytes && refBytes.byteLength > 0 && refBytes.byteLength <= 6_000_000) {
        aiForm.append("input_image_0", new Blob([refBytes], { type: refMime }), "reference.png");
      }
      const formResponse = new Response(aiForm);
      const aiResult = await env.AI.run(modelName, {
        multipart: {
          body: formResponse.body,
          contentType: formResponse.headers.get("content-type"),
        },
      });
      const bytes = await extractAiImageBytes(aiResult);
      if (bytes && bytes.byteLength > 100) {
        return { bytes, model: modelName };
      }
      lastErr = new Error(`Cloudflare image returned empty bytes (${modelName})`);
    } catch (err) {
      lastErr = new Error(
        `Cloudflare image error (${modelName}): ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }
  throw lastErr || new Error("Cloudflare image generation failed");
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

const COPY_GUARDRAIL_NOTE =
  "SEO & Language Integrity Policy: preserve exact factual product meaning across every language without inventing specs or altering intent; write broad, unique multi-sentence descriptions with native orthography and zero alphabet mixing; NEVER emit faq, Quick buyer questions, or FAQPage boilerplate.";

function parseCopyJsonObject(rawText) {
  let text = String(rawText || "")
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .trim();
  if (text.startsWith("```")) {
    text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  }
  try {
    const direct = JSON.parse(text);
    if (direct && typeof direct === "object" && !Array.isArray(direct)) return direct;
  } catch {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start !== -1 && end > start) {
      const sliced = JSON.parse(text.slice(start, end + 1));
      if (sliced && typeof sliced === "object" && !Array.isArray(sliced)) return sliced;
    }
  }
  return null;
}

function validateAndSanitizeWorkerCopy(rawText, jsonOutput) {
  if (!jsonOutput) return { ok: true, content: rawText };
  const parsed = parseCopyJsonObject(rawText);
  if (!parsed) return { ok: false, error: "Invalid JSON object" };

  let mutated = false;
  if ("faq" in parsed) {
    delete parsed.faq;
    mutated = true;
  }

  const localeKeys = ["ru", "en", "pt", "es", "fr", "he"];
  if (localeKeys.every((k) => parsed[k] && typeof parsed[k] === "object")) {
    const cyrRe = /[А-Яа-яЁё]/;
    const hebRe = /[א-ת]/;
    const mixedRe = /(?:[A-Za-zÀ-ÿ\u0100-\u024F\u1E00-\u1EFF][А-Яа-яЁё])|(?:[А-Яа-яЁё][A-Za-zÀ-ÿ\u0100-\u024F\u1E00-\u1EFF])/;
    const foreignDiacRe = /[\u0110\u0111\u1E00-\u1EFF]/;
    for (const lang of localeKeys) {
      const entry = parsed[lang];
      const name = String(entry.name || "").trim();
      const headline = Array.isArray(entry.headline)
        ? entry.headline.map((x) => String(x || "").trim()).join(" ")
        : String(entry.headline || "").trim();
      const desc = String(entry.description || "").trim();
      const full = `${name} ${headline} ${desc}`.trim();
      if (!name || !desc) {
        return { ok: false, error: `${lang}: empty name or description` };
      }
      if (/Quick buyer questions|Частые вопросы перед покупкой|product-faq/i.test(full)) {
        return { ok: false, error: `${lang}: forbidden FAQ boilerplate` };
      }
      if (mixedRe.test(full) || foreignDiacRe.test(full)) {
        return { ok: false, error: `${lang}: mixed-script or foreign diacritic artifact` };
      }
      if (lang === "ru") {
        if (!cyrRe.test(full) || hebRe.test(full)) {
          return { ok: false, error: "ru: script integrity failed" };
        }
      } else if (lang === "he") {
        if (!hebRe.test(full) || cyrRe.test(full)) {
          return { ok: false, error: "he: script integrity failed" };
        }
      } else if (cyrRe.test(full) || hebRe.test(full)) {
        return { ok: false, error: `${lang}: cross-alphabet leak detected` };
      }
      if (lang === "es") {
        const qOpen = (full.match(/¿/g) || []).length;
        const qClose = (full.match(/\?/g) || []).length;
        const eOpen = (full.match(/¡/g) || []).length;
        const eClose = (full.match(/!/g) || []).length;
        if (qOpen !== qClose || eOpen !== eClose) {
          return { ok: false, error: "es: unbalanced ¿ or ¡ punctuation" };
        }
      }
    }
  }

  return { ok: true, content: mutated ? JSON.stringify(parsed) : rawText };
}

async function generateCloudflareCopy(
  env,
  messages,
  {
    preferredModels = [],
    temperature = 0.25,
    maxTokens = 4096,
    jsonOutput = true,
  } = {}
) {
  const cleanMessages = messages
    .map((m) => ({ role: m?.role || "user", content: extractMessageText(m?.content) }))
    .filter((m) => Boolean(m.content));
  if (jsonOutput && cleanMessages.length && !cleanMessages.some((m) => m.content.includes("Quick buyer questions"))) {
    if (cleanMessages[0].role === "system") {
      cleanMessages[0] = { role: "system", content: `${cleanMessages[0].content}\n${COPY_GUARDRAIL_NOTE}` };
    } else {
      cleanMessages.unshift({ role: "system", content: COPY_GUARDRAIL_NOTE });
    }
  }
  const models = resolveCfModelChain(
    [...preferredModels, env.DEFAULT_TEXT_MODEL],
    CF_COPY_MODELS
  );
  let lastErr = null;
  for (const modelName of models) {
    try {
      const params = {
        messages: cleanMessages.length ? cleanMessages : [{ role: "user", content: "" }],
        temperature,
        max_tokens: maxTokens,
      };
      if (jsonOutput) {
        params.response_format = { type: "json_object" };
      }
      const aiRes = await env.AI.run(modelName, params);
      const rawContent = extractAiChatText(aiRes);
      if (rawContent.trim()) {
        const checked = validateAndSanitizeWorkerCopy(rawContent, jsonOutput);
        if (checked.ok) {
          return { content: checked.content, model: modelName, raw: aiRes };
        }
        lastErr = new Error(`Cloudflare copy rejected (${modelName}): ${checked.error}`);
        continue;
      }
      lastErr = new Error(`Cloudflare copy returned empty content (${modelName})`);
    } catch (err) {
      lastErr = new Error(
        `Cloudflare copy error (${modelName}): ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }
  throw lastErr || new Error("Cloudflare copy failed");
}

function clampDim(val, fallback = 1024) {
  const parsed = Number.parseInt(String(val ?? fallback), 10);
  return Number.isFinite(parsed) ? Math.min(Math.max(parsed, 256), 2048) : fallback;
}

async function handleGenerateCutout(request, env, url) {
  if (!env.AI) {
    return jsonResponse(
      { ok: false, error: "Cloudflare Workers AI binding (env.AI) not configured" },
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
  const preferredModels = resolveCfModelChain(
    [fields.model, url.searchParams.get("model"), env.DEFAULT_IMAGE_MODEL, env.FALLBACK_IMAGE_MODEL],
    CF_IMAGE_MODELS
  );

  if (!rawPrompt.trim() && !refBlob) {
    return jsonResponse(
      { ok: false, error: "Provide a prompt or reference image for studio generation" },
      400
    );
  }

  const allowWorldBg =
    String(fields.use_world_bg || url.searchParams.get("use_world_bg") || "").trim() === "1";
  const targetHex = resolveTargetBackgroundHex(rawBackgroundHex, category, { allowWorldBg });
  const outputMode = !targetHex || targetHex === "#FFFFFF" ? "transparent-cutout-source" : "custom-bg";
  if (refBlob && !visualSpec.trim() && url.searchParams.get("use_vision") === "1") {
    try {
      const desc = await describeProductFromImage(env, refBlob, rawPrompt);
      visualSpec = desc.visualSpec;
    } catch {
      visualSpec = "";
    }
  }

  const studioPrompt = buildStudioPrompt(rawPrompt, { backgroundHex: targetHex, visualSpec });
  const createdAt = new Date().toISOString();
  let effectiveModel = preferredModels[0] || "@cf/black-forest-labs/flux-2-klein-9b";

  try {
    const fluxRes = await generateCloudflareFluxImage(env, studioPrompt, refBlob, {
      preferredModels,
      width,
      height,
    });
    const imageBytes = fluxRes.bytes;
    effectiveModel = fluxRes.model;
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
        provider: "cloudflare-workers-ai",
        status: "completed",
        width,
        height,
        bytes: imageBytes.byteLength,
        mime_type: mimeType,
        has_reference_image: Boolean(refBlob),
        background_hex: targetHex || "#FFFFFF",
        output_mode: outputMode,
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
        "X-Studio-Output-Mode": outputMode,
        "X-Studio-Generation-Id": String(generationId || ""),
        "X-Studio-Product-Id": productId,
        "X-Studio-View-Name": viewName,
        "X-Studio-Model": effectiveModel,
        "X-Studio-Provider": "cloudflare-workers-ai",
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
        provider: "cloudflare-workers-ai",
        status: "error",
        error: err instanceof Error ? err.message : String(err),
      },
      502
    );
  }
}

async function handleDescribeProduct(request, env) {
  if (!env.AI) {
    return jsonResponse(
      { ok: false, error: "Cloudflare Workers AI binding (env.AI) not configured" },
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
    const descRes = await describeProductFromImage(env, refBlob, productHint, {
      preferredModel,
    });
    return jsonResponse({
      ok: true,
      model: descRes.model,
      provider: "cloudflare-workers-ai",
      visual_spec: descRes.visualSpec,
    });
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        provider: "cloudflare-workers-ai",
        error: err instanceof Error ? err.message : String(err),
      },
      502
    );
  }
}

async function handleGenerateCopy(request, env) {
  if (!env.AI) {
    return jsonResponse(
      { ok: false, error: "Cloudflare Workers AI binding (env.AI) not configured" },
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
    : 4096;

  try {
    const cfRes = await generateCloudflareCopy(env, messages, {
      preferredModels: [body.model, ...(Array.isArray(body.models) ? body.models : []), env.DEFAULT_TEXT_MODEL],
      temperature,
      maxTokens,
      jsonOutput: (body.response_format?.type || "json_object") === "json_object",
    });
    return jsonResponse({
      ok: true,
      model: cfRes.model,
      provider: "cloudflare-workers-ai",
      choices: [{ message: { role: "assistant", content: cfRes.content } }],
      raw: cfRes.raw,
    });
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        provider: "cloudflare-workers-ai",
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
    if (!resp.ok) {
      const errText = await resp.text().catch(() => "");
      return { ok: false, status: resp.status, error_preview: errText.slice(0, 200) };
    }
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

async function getPreviousSyncMeta(env, engine) {
  const [okRow, rateRow] = await Promise.all([
    env.DB.prepare(
      "SELECT payload_json, status, run_at FROM seo_telemetry WHERE engine = ? AND status IN ('accepted', 'key_validation_pending', 'unchanged') ORDER BY id DESC LIMIT 1"
    )
      .bind(engine)
      .first(),
    env.DB.prepare(
      "SELECT run_at FROM seo_telemetry WHERE engine = ? AND status = 'rate_limited' ORDER BY id DESC LIMIT 1"
    )
      .bind(engine)
      .first(),
  ]);
  let fingerprint = null;
  let lastAcceptedAt = null;
  if (okRow) {
    lastAcceptedAt = okRow.run_at || null;
    try {
      const parsed = JSON.parse(okRow.payload_json);
      fingerprint = parsed?.fingerprint || null;
    } catch {
      fingerprint = null;
    }
  }
  return {
    fingerprint,
    lastAcceptedAt,
    lastRateLimitedAt: rateRow?.run_at || null,
  };
}

function selectChangedIndexNowUrls(entries, { lastAcceptedAt = null, maxUrls = 50 } = {}) {
  const nowMs = Date.now();
  const fallbackCutoffMs = nowMs - 48 * 3600 * 1000;
  const parsedLastMs = lastAcceptedAt ? Date.parse(lastAcceptedAt) : NaN;
  const cutoffMs = Number.isFinite(parsedLastMs) ? Math.max(parsedLastMs - 10 * 60 * 1000, nowMs - 7 * 86400 * 1000) : fallbackCutoffMs;

  const scored = [];
  for (const entry of entries) {
    const modMs = entry.lastmod ? Date.parse(entry.lastmod) : NaN;
    if (Number.isFinite(modMs) && modMs >= cutoffMs) {
      scored.push({ url: entry.url, modMs });
    }
  }
  scored.sort((a, b) => b.modMs - a.modMs);
  if (scored.length > 0) {
    return scored.slice(0, maxUrls).map((x) => x.url);
  }
  // If no explicit recent lastmod matched (e.g. first run), send only the top freshly updated subset.
  const byMod = entries
    .map((e) => ({ url: e.url, modMs: e.lastmod ? Date.parse(e.lastmod) || 0 : 0 }))
    .sort((a, b) => b.modMs - a.modMs);
  return byMod.slice(0, Math.min(25, maxUrls)).map((x) => x.url);
}

async function fetchExternalIndexedCounts(env, siteOrigin, { skipBingApi = false } = {}) {
  const result = {
    bing_quota: null,
    bing_status: null,
    bing_error: null,
    bing_in_index: 0,
    bing_crawled_latest: null,
    yandex_searchable: null,
    yandex_status: null,
  };
  const bingKey = String(env.BING_WEBMASTER_API_KEY || "").trim();
  if (bingKey && !skipBingApi) {
    const siteParam = encodeURIComponent(`${siteOrigin}/`);
    const keyParam = encodeURIComponent(bingKey);
    // Call Bing Webmaster API sequentially (never in parallel) to respect Bing's strict ThrottleUser rate limit.
    const bingRes = await fetchJsonSafe(
      `https://ssl.bing.com/webmaster/api.svc/json/GetUrlSubmissionQuota?apikey=${keyParam}&siteUrl=${siteParam}`
    );
    result.bing_status = bingRes.status || (bingRes.ok ? 200 : "fetch_error");
    if (!bingRes.ok && bingRes.error_preview) {
      result.bing_error = bingRes.error_preview;
    }
    if (bingRes.ok && bingRes.data?.d) {
      result.bing_quota = {
        daily_quota: bingRes.data.d.DailyQuota ?? null,
        monthly_quota: bingRes.data.d.MonthlyQuota ?? null,
      };
      // Only fetch crawl stats after quota succeeds and after a polite pause so Bing never triggers ThrottleUser.
      await new Promise((r) => setTimeout(r, 1200));
      const crawlRes = await fetchJsonSafe(
        `https://ssl.bing.com/webmaster/api.svc/json/GetCrawlStats?apikey=${keyParam}&siteUrl=${siteParam}`
      );
      if (crawlRes.ok && Array.isArray(crawlRes.data?.d) && crawlRes.data.d.length) {
        const latest = crawlRes.data.d[crawlRes.data.d.length - 1];
        result.bing_in_index = Number(latest?.InIndex || 0);
        result.bing_crawled_latest = Number(latest?.CrawledPages || 0);
      }
    }
  } else if (skipBingApi) {
    result.bing_status = "delegated_to_seo_daily";
  }
  result.yandex_searchable = null;
  result.yandex_status = "disabled";
  return result;
}

async function runSeoSync(env, { source = "api", force = false, skipIndexNow = true } = {}) {
  const siteOrigin = env.SITE_ORIGIN || "https://www.fluxixo.shop";
  const host = new URL(siteOrigin).host;
  const key = env.INDEXNOW_KEY || "";
  if (!key) {
    throw new Error("INDEXNOW_KEY is not configured");
  }
  const keyLocation = `${siteOrigin}/${key}.txt`;
  const runAt = new Date().toISOString();

  const [globalXml, keyCheckText, externalStats] = await Promise.all([
    fetchText(`${siteOrigin}/sitemap.xml`),
    fetchText(keyLocation).catch(() => ""),
    fetchExternalIndexedCounts(env, siteOrigin, { skipBingApi: skipIndexNow }),
  ]);

  const keyVerified = keyCheckText.trim() === key;
  const globalEntries = parseSitemapEntries(globalXml, siteOrigin);
  const globalUrls = globalEntries.map((e) => e.url);

  const globalFingerprint = await sha256Hex(
    globalEntries.map((e) => `${e.url}|${e.lastmod}`).join("\n")
  );

  const prevGlobal = await getPreviousSyncMeta(env, "indexnow_global");

  const cooldownMs = 6 * 3600 * 1000;
  const nowMs = Date.now();
  const globalRateLimitedRecently =
    !force &&
    prevGlobal.lastRateLimitedAt &&
    nowMs - Date.parse(prevGlobal.lastRateLimitedAt) < cooldownMs;

  let globalResult;
  if (skipIndexNow || (!force && prevGlobal.fingerprint && prevGlobal.fingerprint === globalFingerprint)) {
    globalResult = {
      engine: "indexnow_global",
      endpoint: "https://api.indexnow.org/indexnow",
      status: skipIndexNow ? "telemetry_only" : "unchanged",
      total_urls: globalUrls.length,
      submitted_count: 0,
      indexed_count: Number(externalStats.bing_in_index || 0),
      fingerprint: globalFingerprint,
      key_verified: keyVerified,
      source,
      bing_status: externalStats.bing_status,
      bing_error: externalStats.bing_error || null,
      bing_quota: externalStats.bing_quota,
      bing_crawled_latest: externalStats.bing_crawled_latest,
    };
  } else if (globalRateLimitedRecently) {
    globalResult = {
      engine: "indexnow_global",
      endpoint: "https://api.indexnow.org/indexnow",
      status: "cooldown_skip",
      total_urls: globalUrls.length,
      submitted_count: 0,
      indexed_count: Number(externalStats.bing_in_index || 0),
      fingerprint: globalFingerprint,
      key_verified: keyVerified,
      source,
      bing_status: externalStats.bing_status,
      bing_error: externalStats.bing_error || null,
      bing_quota: externalStats.bing_quota,
      bing_crawled_latest: externalStats.bing_crawled_latest,
    };
  } else {
    const changedGlobalUrls = selectChangedIndexNowUrls(globalEntries, {
      lastAcceptedAt: prevGlobal.lastAcceptedAt,
      maxUrls: 50,
    });
    const res = await submitIndexNowBatch(
      "https://api.indexnow.org/indexnow",
      host,
      key,
      keyLocation,
      changedGlobalUrls
    );
    globalResult = {
      engine: "indexnow_global",
      endpoint: "https://api.indexnow.org/indexnow",
      status: res.status,
      total_urls: globalUrls.length,
      submitted_count: res.submitted_count,
      indexed_count: Number(externalStats.bing_in_index || 0),
      batches: res.batches,
      fingerprint: globalFingerprint,
      key_verified: keyVerified,
      source,
      bing_status: externalStats.bing_status,
      bing_error: externalStats.bing_error || null,
      bing_quota: externalStats.bing_quota,
      bing_crawled_latest: externalStats.bing_crawled_latest,
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
  ]);

  return {
    ok: globalResult.status !== "error",
    run_at: runAt,
    site_origin: siteOrigin,
    key_verified: keyVerified,
    force,
    source,
    engines: {
      indexnow_global: globalResult,
    },
  };
}

async function handleSeoSync(request, env, url) {
  let force = url.searchParams.get("force") === "1";
  let skipIndexNow =
    url.searchParams.get("run_indexnow") !== "1" &&
    url.searchParams.get("skip_indexnow") !== "0";
  try {
    const text = await request.text();
    if (text.trim()) {
      const body = JSON.parse(text);
      if (body && body.force === true) force = true;
      if (body && (body.run_indexnow === true || body.skip_indexnow === false)) {
        skipIndexNow = false;
      } else if (body && body.skip_indexnow === true) {
        skipIndexNow = true;
      }
    }
  } catch {
    // Empty or non-JSON body falls back to query param.
  }

  try {
    const report = await runSeoSync(env, { source: "api", force, skipIndexNow });
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
  if (!expectedToken) return false;
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

async function handleCatalogSync(request, env) {
  let body = {};
  try {
    const text = await request.text();
    if (text.trim()) body = JSON.parse(text);
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }
  const event = String(body.event || "catalog_sync").slice(0, 120);
  const ranAt = new Date().toISOString();
  const dbOps = [
    env.DB.prepare(
      "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
    ).bind("external-sync", event, "ok", JSON.stringify(body), ranAt),
  ];
  if (body.publish_state && typeof body.publish_state === "object") {
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
  if (body.ledger_days && typeof body.ledger_days === "object") {
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

async function runScheduledAction(controller, env) {
  const cron = controller.cron || "manual";
  const ranAt = new Date().toISOString();
  const now = new Date();
  const israelToday = localDay(now, DROP_TZ);
  const utcToday = now.toISOString().slice(0, 10);

  if (cron === "17 5 * * *") {
    let seoReport = null;
    let seoError = null;
    try {
      seoReport = await runSeoSync(env, { source: "cron", force: false, skipIndexNow: true });
    } catch (err) {
      seoError = err instanceof Error ? err.message : String(err);
    }

    const seoOk = Boolean(seoReport?.ok);
    const status = seoError ? "error" : seoOk ? "ok" : "partial_error";

    const details = {
      ...(seoReport || { ok: false, error: seoError }),
      github_dispatch: { skipped: true, reason: "scheduled natively at 25 5 * * *" },
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
  const dropParts = getTzParts(now, DROP_TZ);
  const dropMinutes = Number(dropParts.hour || 0) * 60 + Number(dropParts.minute || 0);
  const alreadyPublishedToday =
    stateRow?.status === "published" || publishedDay === israelToday;
  const beforePrepareWindow = dropMinutes < 13 * 60 + 30;
  const afterDailyWindow = dropMinutes >= 23 * 60;

  let dispatchRes;
  if (alreadyPublishedToday) {
    dispatchRes = {
      ok: true,
      skipped: true,
      http_status: null,
      workflow: "fluxixo_daily_rotate.yml",
      reason: "already_published_today",
    };
  } else if (beforePrepareWindow || afterDailyWindow) {
    dispatchRes = {
      ok: true,
      skipped: true,
      http_status: null,
      workflow: "fluxixo_daily_rotate.yml",
      reason: beforePrepareWindow ? "before_prepare_window" : "after_daily_window",
    };
  } else if (env.GITHUB_DISPATCH_TOKEN) {
    dispatchRes = await dispatchGitHubWorkflow(env, "fluxixo_daily_rotate.yml", { add_count: "auto" });
  } else {
    dispatchRes = {
      ok: false,
      skipped: true,
      http_status: null,
      workflow: "fluxixo_daily_rotate.yml",
      inputs: { add_count: "auto" },
      reason: "GITHUB_DISPATCH_TOKEN not configured",
    };
  }

  const action =
    dropMinutes >= 13 * 60 + 30 && dropMinutes < 15 * 60 + 30
      ? "prepare_window_check"
      : "drop_1530_check";
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

const PROTECTED_POST_HANDLERS = new Map([
  ["/api/generate-cutout", handleGenerateCutout],
  ["/api/describe-product", handleDescribeProduct],
  ["/api/generate-copy", handleGenerateCopy],
  ["/api/dispatch", handleDispatch],
  ["/api/seo-sync", handleSeoSync],
  ["/api/catalog-sync", handleCatalogSync],
]);

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "GET" && path === "/healthz") {
      return jsonResponse(SERVICE_HEALTH, 200, NO_STORE);
    }

    const syncToken = String(env.AUTOPILOT_SYNC_TOKEN || "").trim();
    if (request.method === "GET" && (path === "/" || path === "/api/status")) {
      const payload = hasValidSyncAuth(request, syncToken)
        ? await queryStatusPayload(env)
        : await queryPublicStatusPayload(env);
      return jsonResponse(payload, 200, { ...NO_STORE, Vary: "Authorization" });
    }

    if (request.method === "GET" && path === "/drop-status.json") {
      const now = new Date();
      const payload = await queryPublicStatusPayload(env, now);
      return jsonResponse(
        {
          published_day: payload.published_day,
          due_day: payload.countdown.due_day,
          status: payload.countdown.status,
          seconds_remaining: payload.countdown.seconds,
          countdown: payload.countdown,
          israel_day: payload.countdown.israel_day,
          utc_day: now.toISOString().slice(0, 10),
        },
        200,
        NO_STORE
      );
    }

    if (request.method === "GET" && path === "/api/redirects") {
      return handleRedirects(request, env, url);
    }

    const handler = request.method === "POST" && PROTECTED_POST_HANDLERS.get(path);
    if (handler) {
      if (!hasValidSyncAuth(request, syncToken)) {
        return jsonResponse({ ok: false, error: "Unauthorized" }, 401, {
          ...NO_STORE,
          "WWW-Authenticate": "Bearer",
        });
      }
      return handler(request, env, url);
    }

    return jsonResponse({ ok: false, error: "Not Found" }, 404);
  },

  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runScheduledAction(controller, env));
  },
};
