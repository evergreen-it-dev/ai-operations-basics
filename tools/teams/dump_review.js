#!/usr/bin/env node
/**
 * Teams Chat Review Dump
 * Fetches all P0/P1/P2 chats in parallel and saves to output/teams/teams_review_<ts>.json + .md
 *
 * Usage:
 *   node dump_review.js               # P0/P1: last 1 day, P2: last 4 days
 *   node dump_review.js --days 2      # P0/P1: last 2 days
 *   node dump_review.js --ops-days 7  # P2: last 7 days
 */

import { GraphService } from './dist/services/graph.js';
import { formatMessageContent } from './dist/utils/html-to-markdown.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { getChatRegistry } from './load_chat_registry.js';
import { getAllowedChatIds, loadAccessPolicy } from './load_access_policy.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, '../../output/teams');

// Джерело: workspace/teams-chats.yaml
const CHAT_REGISTRY = getChatRegistry();


// Які групи входять у P0/P1-вікно (DAYS), решта — OPS_DAYS
const P0P1_GROUPS = new Set(['p0_group', 'p0_1on1', 'p1_team', 'p1_standup', 'p1_onboarding', 'p1_internal']);

// ─── CLI ARGS ─────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const DAYS = parseInt(args[args.indexOf('--days') + 1]) || 1;
const OPS_DAYS = parseInt(args[args.indexOf('--ops-days') + 1]) || 4;

// ─── HELPERS ──────────────────────────────────────────────────────────────────
function sinceDate(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatTs(date = new Date()) {
  const p = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${p(date.getMonth()+1)}-${p(date.getDate())}_${p(date.getHours())}${p(date.getMinutes())}`;
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Kyiv' });
}

// ─── FETCH HELPERS ────────────────────────────────────────────────────────────
async function fetchChatMessages(client, chat, since) {
  try {
    const res = await client
      .api(`/me/chats/${chat.id}/messages?$top=50&$orderby=createdDateTime desc`)
      .get();

    const messages = (res?.value ?? [])
      .filter(m =>
        m.messageType === 'message' &&
        m.body?.content &&
        m.body.content.trim() !== '' &&
        m.createdDateTime &&
        new Date(m.createdDateTime) > since
      )
      .map(m => ({
        id: m.id,
        from: m.from?.user?.displayName ?? '?',
        createdDateTime: m.createdDateTime,
        content: formatMessageContent(m.body?.content, 'markdown', m.mentions) ?? '',
        mentions: (m.mentions ?? [])
          .map(mn => mn.mentioned?.user?.displayName)
          .filter(Boolean),
      }));

    return { ...chat, messages, error: null };
  } catch (err) {
    return { ...chat, messages: [], error: err.message };
  }
}

async function fetchMentions(client, days, allowedChatIds) {
  const { policy } = loadAccessPolicy();
  if (policy.mentions?.allow === false) return [];

  const since = sinceDate(days);
  try {
    const body = {
      requests: [{
        entityTypes: ['chatMessage'],
        query: { queryString: 'IsMentioned:true' },
        from: 0,
        size: 50,
      }],
    };
    const res = await client.api('/search/query').post(body);
    const hits = res?.value?.[0]?.hitsContainers?.[0]?.hits ?? [];
    return hits
      .filter(h => h.resource.createdDateTime && new Date(h.resource.createdDateTime) > since)
      .filter(h => {
        if (!policy.mentions?.allowlist_only) return true;
        const chatId = h.resource.chatId ?? null;
        // Канальні mentions (без chatId) — дозволити; chat — лише з allowlist
        if (!chatId) return true;
        return allowedChatIds.has(chatId);
      })
      .map(h => ({
        id: h.resource.id,
        summary: h.summary ?? '',
        from: h.resource.from?.user?.displayName ?? '?',
        createdDateTime: h.resource.createdDateTime,
        webLink: h.resource.webLink,
        chatId: h.resource.chatId ?? null,
        teamId: h.resource.channelIdentity?.teamId ?? null,
        channelId: h.resource.channelIdentity?.channelId ?? null,
      }));
  } catch {
    return [];
  }
}

// ─── MARKDOWN RENDERER ────────────────────────────────────────────────────────
const GROUP_LABELS = {
  p0_group:      'P0 Favorites (group)',
  p0_1on1:       'P0 Favorites (1:1)',
  p1_team:       'P1 [TEAM]',
  p1_standup:    'P1 Standup / Дейлик',
  p1_onboarding: 'P1 Onboarding',
  p1_internal:   'P1 [Internal]',
  p2_ops:        'P2 Operations',
};

function buildMarkdown(data) {
  const { generated_at_local, windows, mentions, chats, stats } = data;
  const lines = [
    `# Teams Review — ${generated_at_local}`,
    `> P0/P1: останні ${windows.p0_p1_days} дн · P2: останні ${windows.p2_days} дн`,
    `> Mentions: ${stats.mentions_count} · Чатів з повідомленнями: ${stats.chats_with_messages}/${stats.total_chats_fetched} · Повідомлень: ${stats.total_messages}`,
    '',
  ];

  // Mentions
  lines.push(`## 🔴 Mentions (${mentions.length})`);
  if (mentions.length === 0) {
    lines.push('_Немає_');
  } else {
    for (const m of mentions) {
      lines.push(`- [${formatTime(m.createdDateTime)}] **${m.from}**: ${m.summary}`);
      if (m.webLink) lines.push(`  → [відкрити](${m.webLink})`);
    }
  }
  lines.push('');

  // Chats by group
  for (const group of Object.keys(GROUP_LABELS)) {
    const groupChats = chats.filter(c => c.group === group);
    const withMsgs = groupChats.filter(c => c.messages.length > 0);
    const total = withMsgs.reduce((n, c) => n + c.messages.length, 0);

    lines.push(`## ${GROUP_LABELS[group]}${total > 0 ? ` (${total})` : ' — тихо'}`);

    // Empty chats — show as compact list
    const silent = groupChats.filter(c => c.messages.length === 0 && !c.error);
    if (silent.length > 0) {
      lines.push(`_Без нових: ${silent.map(c => c.name).join(', ')}_`);
    }

    // Errors
    for (const c of groupChats.filter(c => c.error)) {
      lines.push(`⚠️ **${c.name}**: ${c.error}`);
    }

    // Chats with messages
    for (const chat of withMsgs) {
      const hasMentions = chat.messages.some(m => m.mentions.length > 0);
      lines.push(`### ${hasMentions ? '🔴 ' : ''}${chat.name} (${chat.messages.length})`);
      for (const m of chat.messages) {
        const flag = m.mentions.length > 0 ? '🔴 ' : '';
        const text = m.content.replace(/\n+/g, ' ').slice(0, 300);
        lines.push(`- ${flag}[${formatTime(m.createdDateTime)}] **${m.from}**: ${text}`);
      }
      lines.push('');
    }
  }

  return lines.join('\n');
}

// ─── MAIN ─────────────────────────────────────────────────────────────────────
async function main() {
  const service = GraphService.getInstance();
  let client;
  try {
    client = await service.getClient();
  } catch (err) {
    console.error('❌ Not authenticated. Run: node dist/index.js authenticate');
    process.exit(1);
  }

  const since = sinceDate(DAYS);
  const sinceOps = sinceDate(OPS_DAYS);
  const allowedChatIds = getAllowedChatIds(CHAT_REGISTRY);

  console.log(`⏳ Fetching ${CHAT_REGISTRY.length} chats + mentions in parallel...`);
  console.log(`   P0/P1 window: ${DAYS} day(s) since ${since.toISOString().slice(0, 10)}`);
  console.log(`   P2 window:    ${OPS_DAYS} day(s) since ${sinceOps.toISOString().slice(0, 10)}`);

  const [mentions, ...chatResults] = await Promise.all([
    fetchMentions(client, DAYS, allowedChatIds),
    ...CHAT_REGISTRY.map(chat => {
      const window = P0P1_GROUPS.has(chat.group) ? since : sinceOps;
      return fetchChatMessages(client, chat, window);
    }),
  ]);

  const now = new Date();
  const ts = formatTs(now);

  const data = {
    generated_at_utc: now.toISOString(),
    generated_at_local: ts.replace(/_/, ' ').replace(/(\d{2})(\d{2})$/, '$1:$2'),
    windows: { p0_p1_days: DAYS, p2_days: OPS_DAYS },
    mentions,
    chats: chatResults,
    stats: {
      total_chats_fetched: chatResults.length,
      chats_with_messages: chatResults.filter(c => c.messages.length > 0).length,
      total_messages: chatResults.reduce((n, c) => n + c.messages.length, 0),
      mentions_count: mentions.length,
    },
  };

  mkdirSync(OUTPUT_DIR, { recursive: true });
  const base = join(OUTPUT_DIR, `teams_review_${ts}`);
  writeFileSync(`${base}.json`, JSON.stringify(data, null, 2), 'utf8');
  writeFileSync(`${base}.md`, buildMarkdown(data), 'utf8');

  console.log(`\n✅ ${base}.json`);
  console.log(`✅ ${base}.md`);
  console.log(`\n📊 Stats:`);
  console.log(`   Mentions: ${data.stats.mentions_count}`);
  console.log(`   Chats with messages: ${data.stats.chats_with_messages}/${data.stats.total_chats_fetched}`);
  console.log(`   Total messages: ${data.stats.total_messages}`);
}

main().catch(err => {
  console.error('❌', err.message);
  process.exit(1);
});
