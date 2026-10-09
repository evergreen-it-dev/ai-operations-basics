#!/usr/bin/env node
/**
 * Load Teams chat registry from workspace/teams-chats.yaml
 *
 * Usage (CLI):
 *   node load_chat_registry.js team-chat
 *   node load_chat_registry.js "4 кита"
 *   node load_chat_registry.js --list ops
 *   node load_chat_registry.js --list all
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';
import { isChatAllowed, loadAccessPolicy } from './load_access_policy.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const REGISTRY_PATH = join(__dirname, '../../workspace/teams-chats.yaml');
export const LOCAL_REGISTRY_PATH = join(__dirname, '../../workspace/teams-chats.local.yaml');

let _cache = null;

function mergeRegistries(base, local) {
  if (!local) return base;

  const chats = { ...(base.chats ?? {}) };

  for (const key of local.exclude_keys ?? []) {
    delete chats[key];
  }

  for (const group of local.exclude_groups ?? []) {
    for (const [key, chat] of Object.entries(chats)) {
      if (chat.group === group) delete chats[key];
    }
  }

  for (const [key, chat] of Object.entries(local.chats ?? {})) {
    chats[key] = chat;
  }

  return {
    ...base,
    meta: { ...(base.meta ?? {}), ...(local.meta ?? {}) },
    chats,
  };
}

export function loadRegistry(force = false) {
  if (_cache && !force) return _cache;
  const base = parseYaml(readFileSync(REGISTRY_PATH, 'utf8'));
  const local = existsSync(LOCAL_REGISTRY_PATH)
    ? parseYaml(readFileSync(LOCAL_REGISTRY_PATH, 'utf8'))
    : null;
  _cache = mergeRegistries(base, local);
  return _cache;
}

/** @returns {{ id, name, group, key, aliases?, notes? } | null} */
export function resolveChat(query) {
  const registry = loadRegistry();
  const q = String(query).toLowerCase().trim();
  if (!q) return null;

  const chats = Object.entries(registry.chats ?? {});
  const entry = (key, chat) => ({ ...chat, key });

  // 1) Точний матч: key, name, alias
  for (const [key, chat] of chats) {
    if (key === q) return entry(key, chat);
    if (chat.name?.toLowerCase() === q) return entry(key, chat);
    if (chat.aliases?.some(a => String(a).toLowerCase() === q)) return entry(key, chat);
  }

  // 2) Частковий матч (≥3 символи) — name або alias містить запит
  if (q.length >= 3) {
    for (const [key, chat] of chats) {
      const name = chat.name?.toLowerCase() ?? '';
      if (name.includes(q)) return entry(key, chat);
      if (chat.aliases?.some(a => String(a).toLowerCase().includes(q))) return entry(key, chat);
    }
  }

  return null;
}

/** Flat list for dump_review.js: { id, name, group, key }[] — з урахуванням teams-access.yaml */
export function getChatRegistry() {
  const { policy } = loadAccessPolicy();
  return Object.entries(loadRegistry().chats ?? {})
    .filter(([, c]) => c.id)
    .map(([key, c]) => ({ id: c.id, name: c.name, group: c.group, key }))
    .filter(c => isChatAllowed(c, policy));
}

/** Ops chats for dump_ops_chat.js */
export function getOpsRegistry() {
  return getChatRegistry().filter(c => c.group === 'p2_ops');
}

// ─── CLI ─────────────────────────────────────────────────────────────────────
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];

if (isMain) {
  const args = process.argv.slice(2);

  if (args[0] === '--list') {
    const mode = args[1] ?? 'all';
    const list = mode === 'ops' ? getOpsRegistry() : getChatRegistry();
    for (const c of list) {
      console.log(`${c.name}\t${c.id}\t${c.group}`);
    }
    process.exit(0);
  }

  if (!args[0]) {
    console.error('Usage: node load_chat_registry.js <alias|name> | --list [all|ops]');
    process.exit(1);
  }

  const hit = resolveChat(args.join(' '));
  if (!hit) {
    console.error(`Not found: ${args.join(' ')}`);
    process.exit(1);
  }
  if (!isChatAllowed(hit)) {
    console.error(`Blocked by teams-access.yaml (group: ${hit.group ?? 'unknown'})`);
    process.exit(3);
  }
  if (!hit.id) {
    console.error(`Found "${hit.name}" but chatId is null (TBD)`);
    process.exit(2);
  }
  console.log(hit.id);
}
