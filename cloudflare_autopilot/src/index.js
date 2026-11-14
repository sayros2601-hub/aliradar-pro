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
  hour = 19,
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
    default_image_model: env.DEFAULT_IMAGE_MODEL || "@cf/black-forest-labs/flux-2-klein-4b",
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
  if (typeof aiResult === "string") {
    return base64ToUint8Array(aiResult);
  }
  throw new Error("Unsupported Workers AI image output shape");
}

function buildStudioPrompt(rawPrompt) {
  const trimmed = (rawPrompt || "").trim();
  const base = trimmed || "modern minimalist consumer electronics product";
  if (/#ffffff/i.test(base) && /studio/i.test(base)) {
    return base;
  }
  return (
    `Studio e-commerce product photography of ${base}, ` +
    `centered isolated product on a pure seamless #FFFFFF solid white background, ` +
    `soft natural contact shadow directly under the base, crisp edge separation, ` +
    `clean commercial catalog cutout, zero props, zero text, zero watermarks.`
  );
}

async function handleGenerateCutout(request, env, url) {
  const model = env.DEFAULT_IMAGE_MODEL || "@cf/black-forest-labs/flux-2-klein-4b";
  const contentType = (request.headers.get("content-type") || "").toLowerCase();
  const wantMeta =
    url.searchParams.get("meta") === "1" || url.searchParams.get("format") === "json";

  let rawPrompt = "";
  let productId = "studio-sample";
  let viewName = "main";
  let width = 1024;
  let height = 1024;
  let refBlob = null;
  let refName = "reference.png";

  if (contentType.includes("multipart/form-data")) {
    const form = await request.formData();
    rawPrompt = String(form.get("prompt") || "");
    productId = String(form.get("product_id") || productId).trim() || "studio-sample";
    viewName = String(form.get("view_name") || viewName).trim() || "main";
    const parsedW = Number.parseInt(String(form.get("width") || "1024"), 10);
    const parsedH = Number.parseInt(String(form.get("height") || "1024"), 10);
    if (Number.isFinite(parsedW)) width = Math.min(Math.max(parsedW, 256), 2048);
    if (Number.isFinite(parsedH)) height = Math.min(Math.max(parsedH, 256), 2048);
    const maybeFile =
      form.get("input_image_0") ||
      form.get("reference_image") ||
      form.get("image") ||
      form.get("file");
    if (maybeFile && typeof maybeFile !== "string" && typeof maybeFile.arrayBuffer === "function") {
      refBlob = maybeFile;
      refName = maybeFile.name || "reference.png";
    }
  } else {
    let body = {};
    try {
      const text = await request.text();
      if (text.trim()) body = JSON.parse(text);
    } catch {
      return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
    }
    rawPrompt = String(body.prompt || "");
    productId = String(body.product_id || productId).trim() || "studio-sample";
    viewName = String(body.view_name || viewName).trim() || "main";
    if (body.width !== undefined) {
      const parsedW = Number.parseInt(String(body.width), 10);
      if (Number.isFinite(parsedW)) width = Math.min(Math.max(parsedW, 256), 2048);
    }
    if (body.height !== undefined) {
      const parsedH = Number.parseInt(String(body.height), 10);
      if (Number.isFinite(parsedH)) height = Math.min(Math.max(parsedH, 256), 2048);
    }
    if (typeof body.image_base64 === "string" && body.image_base64.trim()) {
      const bytes = base64ToUint8Array(body.image_base64);
      refBlob = new Blob([bytes], { type: detectImageMime(bytes) });
    }
  }

  if (!rawPrompt.trim() && !refBlob) {
    return jsonResponse(
      { ok: false, error: "Provide a prompt or reference image for studio generation" },
      400
    );
  }

  const studioPrompt = buildStudioPrompt(rawPrompt);
  const createdAt = new Date().toISOString();

  try {
    let aiResult;
    if (model.includes("flux-2")) {
      const aiForm = new FormData();
      aiForm.append("prompt", studioPrompt);
      aiForm.append("width", String(width));
      aiForm.append("height", String(height));
      if (refBlob) {
        aiForm.append("input_image_0", refBlob, refName);
      }
      const formResponse = new Response(aiForm);
      aiResult = await env.AI.run(model, {
        multipart: {
          body: formResponse.body,
          contentType: formResponse.headers.get("content-type"),
        },
      });
    } else {
      const inputs = { prompt: studioPrompt, width, height };
      if (refBlob) {
        inputs.image = Array.from(new Uint8Array(await refBlob.arrayBuffer()));
      }
      aiResult = await env.AI.run(model, inputs);
    }

    const imageBytes = await extractAiImageBytes(aiResult);
    const mimeType = detectImageMime(imageBytes);

    const insertRes = await env.DB.prepare(
      "INSERT INTO studio_generations (product_id, view_name, model, status, width, height, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(productId, viewName, model, "completed", width, height, createdAt)
      .run();

    const generationId = insertRes.meta?.last_row_id || null;

    if (wantMeta) {
      return jsonResponse({
        ok: true,
        id: generationId,
        product_id: productId,
        view_name: viewName,
        model,
        status: "completed",
        width,
        height,
        bytes: imageBytes.byteLength,
        mime_type: mimeType,
        has_reference_image: Boolean(refBlob),
        prompt_used: studioPrompt,
        created_at: createdAt,
      });
    }

    return new Response(imageBytes, {
      status: 200,
      headers: corsHeaders({
        "Content-Type": mimeType,
        "Cache-Control": "no-store",
        "X-Studio-Generation-Id": String(generationId || ""),
        "X-Studio-Product-Id": productId,
        "X-Studio-View-Name": viewName,
        "X-Studio-Model": model,
      }),
    });
  } catch (err) {
    await env.DB.prepare(
      "INSERT INTO studio_generations (product_id, view_name, model, status, width, height, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(productId, viewName, model, "error", width, height, createdAt)
      .run()
      .catch(() => {});

    return jsonResponse(
      {
        ok: false,
        product_id: productId,
        view_name: viewName,
        model,
        status: "error",
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

async function runScheduledAction(controller, env) {
  const cron = controller.cron || "manual";
  const ranAt = new Date().toISOString();
  const now = new Date();
  const israelToday = localDay(now, ISRAEL_TZ);
  const utcToday = now.toISOString().slice(0, 10);

  if (cron === "17 5 * * *") {
    try {
      const report = await runSeoSync(env, { source: "cron", force: false });
      const status = report.ok ? "ok" : "partial_error";
      await env.DB.prepare(
        "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
      )
        .bind(cron, "seo_sync", status, JSON.stringify(report), ranAt)
        .run();
      return;
    } catch (err) {
      await env.DB.prepare(
        "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
      )
        .bind(
          cron,
          "seo_sync",
          "error",
          JSON.stringify({ error: err instanceof Error ? err.message : String(err) }),
          ranAt
        )
        .run();
      return;
    }
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

  const action = cron === "30 15 * * *" ? "prepare_window_check" : "drop_1900_check";
  const details = {
    israel_today: israelToday,
    utc_today: utcToday,
    utc_ledger_done: doneToday,
    remaining_allowance: remainingAllowance,
    today_publish_state: stateRow,
    published_day: publishedDay || null,
    countdown,
  };

  await env.DB.prepare(
    "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
  )
    .bind(cron, action, "ok", JSON.stringify(details), ranAt)
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
      await env.DB.prepare(
        "INSERT INTO cron_runs (cron, action, status, details_json, ran_at) VALUES (?, ?, ?, ?, ?)"
      )
        .bind("external-sync", event, "ok", JSON.stringify(body), ranAt)
        .run();
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
          "POST /api/generate-cutout",
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
