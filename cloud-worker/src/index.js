/**
 * 🍅 番茄音乐云端编排器 — Cloudflare Worker
 *
 * 接收 Make.com 的请求 → 并行调 MiniMax（MP3）+ BizyAir（封面）→ 返回两个 URL
 * 全程在 Cloudflare 边缘节点运行，零本地依赖。
 *
 * POST /generate
 * Body: { title, lyrics, prompt, genre, mood }
 * Returns: { mp3_url, cover_url, title }
 */

const MINIMAX_ENDPOINT = "https://api.minimax.io/v1/music_generation";
const BIZYAIR_BASE = "https://api.bizyair.cn/x/v1";

// ─── MiniMax 音乐生成 ───
async function generateMusic(env, title, lyrics, prompt) {
  const body = JSON.stringify({
    model: "music-3.0",
    prompt: prompt || "Pop",
    lyrics: lyrics || "La la la",
    output_format: "url",
  });

  const resp = await fetch(MINIMAX_ENDPOINT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.MINIMAX_KEY}`,
      "Content-Type": "application/json",
    },
    body,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`MiniMax ${resp.status}: ${text.slice(0, 200)}`);
  }

  const data = await resp.json();
  const audioUrl = data?.data?.audio;
  if (!audioUrl) {
    throw new Error(`MiniMax 无 audio URL: ${JSON.stringify(data).slice(0, 200)}`);
  }
  return audioUrl;
}

// ─── BizyAir 封面（submit → 轮询） ───
async function generateCover(env, title, genre, mood) {
  const promptText = `Album cover for song ${title}, ${genre || "pop"} music, ${mood || "dreamy"} mood, artistic, high quality`;
  const submitBody = JSON.stringify({
    prompt: promptText,
    image_size: "1024x1024",
  });

  // Step 1: Submit
  console.log("BizyAir submit starting...");
  const submitResp = await fetch(
    `${BIZYAIR_BASE}/modelzoo/tasks/openapi/bza-image-o2-base/text-to-image`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.BIZYAIR_KEY}`,
        "Content-Type": "application/json",
        lang: "zh",
      },
      body: submitBody,
    }
  );

  console.log(`BizyAir submit status: ${submitResp.status}`);

  if (!submitResp.ok) {
    const errText = await submitResp.text();
    console.log(`BizyAir submit error body: ${errText.slice(0, 300)}`);
    throw new Error(`BizyAir submit ${submitResp.status}: ${errText.slice(0, 100)}`);
  }

  const submitData = await submitResp.json();
  const requestId = submitData?.data?.request_id;
  if (!requestId) {
    throw new Error(`BizyAir 无 request_id: ${JSON.stringify(submitData).slice(0, 200)}`);
  }

  // Step 2: Poll (最多 5 分钟)
  for (let i = 0; i < 30; i++) {
    await sleep(10000); // 每 10 秒查一次

    const pollResp = await fetch(
      `${BIZYAIR_BASE}/modelzoo/tasks/openapi/${requestId}`,
      {
        headers: {
          Authorization: `Bearer ${env.BIZYAIR_KEY}`,
          lang: "zh",
        },
      }
    );

    if (!pollResp.ok) continue;

    const pollData = await pollResp.json();
    const taskData = pollData?.data || {};
    const status = taskData.status;

    if (status === "Success") {
      const outputs = taskData.outputs || {};
      const images = outputs.images || [];
      if (images.length > 0) {
        // images 是字符串数组 ["https://..."]
        return typeof images[0] === "string" ? images[0] : images[0]?.url;
      }
    } else if (status === "Failed") {
      throw new Error(`BizyAir 生成失败: ${taskData.message || "unknown"}`);
    }
    // status === "Running" → 继续轮询
  }

  throw new Error("BizyAir 轮询超时 (5 分钟)");
}

// ─── 工具函数 ───
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...corsHeaders(),
    },
  });
}

// ─── 主入口 ───
export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    // 健康检查
    if (request.method === "GET") {
      return jsonResponse({
        status: "ok",
        service: "tomato-music-worker",
        time: new Date().toISOString(),
      });
    }

    // POST /generate
    if (request.method === "POST") {
      const url = new URL(request.url);
      if (!url.pathname.startsWith("/generate")) {
        return jsonResponse({ error: "Not found" }, 404);
      }

      let body;
      try {
        body = await request.json();
      } catch {
        return jsonResponse({ error: "Invalid JSON" }, 400);
      }

      const { title, lyrics, prompt, genre, mood } = body;
      if (!title) {
        return jsonResponse({ error: "Missing title" }, 400);
      }

      console.log(`🎵 生成请求: ${title}`);

      // 并行：MiniMax + BizyAir
      const results = { mp3_url: null, cover_url: null, title, errors: [] };

      const [mp3Result, coverResult] = await Promise.allSettled([
        generateMusic(env, title, lyrics, prompt),
        generateCover(env, title, genre, mood),
      ]);

      if (mp3Result.status === "fulfilled") {
        results.mp3_url = mp3Result.value;
      } else {
        results.errors.push(`MP3: ${mp3Result.reason?.message || mp3Result.reason}`);
      }

      if (coverResult.status === "fulfilled") {
        results.cover_url = coverResult.value;
      } else {
        results.errors.push(`Cover: ${coverResult.reason?.message || coverResult.reason}`);
      }

      return jsonResponse(results);
    }

    return jsonResponse({ error: "Method not allowed" }, 405);
  },
};
