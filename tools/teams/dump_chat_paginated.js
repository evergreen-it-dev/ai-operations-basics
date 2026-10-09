#!/usr/bin/env node
/**
 * Пагінований dump одного Teams-чату через Graph API (без browser).
 * Top max = 50 → ходимо по @odata.nextLink.
 *
 *   node dump_chat_paginated.js --chat-id "19:…@thread.v2" --limit 400 --days 120
 *   node dump_chat_paginated.js --alias "Implementation Engineer вакансия" --limit 400
 *
 * stdout: JSON { chatId, messages: [...] }
 */
import { GraphService } from './dist/services/graph.js';
import { formatMessageContent } from './dist/utils/html-to-markdown.js';
import { resolveChat } from './load_chat_registry.js';

const args = process.argv.slice(2);
function getArg(flag) {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : null;
}

const LIMIT = Math.min(parseInt(getArg('--limit') || '400', 10) || 400, 2000);
const DAYS = parseInt(getArg('--days') || '120', 10) || 120;
const ALIAS = getArg('--alias');
let chatId = getArg('--chat-id');
const NAME = getArg('--name') || ALIAS || chatId;

if (ALIAS && !chatId) {
  const hit = resolveChat(ALIAS);
  if (!hit?.id) {
    console.error(JSON.stringify({ error: `chat not found: ${ALIAS}` }));
    process.exit(1);
  }
  chatId = hit.id;
}

if (!chatId) {
  console.error('Usage: node dump_chat_paginated.js --chat-id ID|--alias NAME [--limit 400] [--days 120]');
  process.exit(1);
}

function sinceDate(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(0, 0, 0, 0);
  return d;
}

async function main() {
  const service = GraphService.getInstance();
  let client;
  try {
    client = await service.getClient();
  } catch {
    console.error(JSON.stringify({ error: 'Not authenticated. Run teams authenticate.' }));
    process.exit(1);
  }

  const since = sinceDate(DAYS);
  const pageSize = 50;
  let url = `/me/chats/${chatId}/messages?$top=${pageSize}&$orderby=createdDateTime desc`;
  const collected = [];

  while (url && collected.length < LIMIT) {
    const res = await client.api(url).get();
    const batch = res?.value ?? [];
    for (const m of batch) {
      if (m.messageType !== 'message' || !m.body?.content?.trim()) continue;
      if (!m.createdDateTime || new Date(m.createdDateTime) <= since) continue;
      collected.push({
        id: m.id,
        from: m.from?.user?.displayName ?? '?',
        createdDateTime: m.createdDateTime,
        content: formatMessageContent(m.body?.content, 'markdown', m.mentions) ?? '',
        attachments: (m.attachments ?? []).map((a) => ({
          id: a.id,
          name: a.name,
          contentType: a.contentType,
          contentUrl: a.contentUrl,
        })),
      });
      if (collected.length >= LIMIT) break;
    }
    // stop if oldest in page is before since
    const oldest = batch.length ? batch[batch.length - 1]?.createdDateTime : null;
    if (oldest && new Date(oldest) <= since) break;
    const next = res?.['@odata.nextLink'];
    if (!next) break;
    // nextLink is absolute; graph client accepts path after /v1.0
    const idx = next.indexOf('/chats/');
    url = idx >= 0 ? next.slice(idx) : null;
    if (next.includes('/me/')) {
      url = next.slice(next.indexOf('/me/'));
    }
  }

  process.stdout.write(
    JSON.stringify(
      {
        name: NAME,
        chatId,
        limit: LIMIT,
        days: DAYS,
        messages_fetched: collected.length,
        messages: collected,
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error(JSON.stringify({ error: err.message || String(err) }));
  process.exit(1);
});
