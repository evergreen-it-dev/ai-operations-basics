#!/usr/bin/env node
/** Shortcut: resolve chat alias → chatId (stdout) */
import { resolveChat } from './load_chat_registry.js';

const query = process.argv.slice(2).join(' ');
if (!query) {
  console.error('Usage: node resolve_chat.js <alias|name>\nExample: node resolve_chat.js team-chat');
  process.exit(1);
}

const hit = resolveChat(query);
if (!hit?.id) {
  console.error(hit ? `TBD (no id): ${hit.name}` : `Not found: ${query}`);
  process.exit(hit ? 2 : 1);
}

console.log(JSON.stringify({ key: hit.key, name: hit.name, id: hit.id, group: hit.group }, null, 2));
