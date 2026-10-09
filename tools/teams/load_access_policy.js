#!/usr/bin/env node
/**
 * Load Teams access policy from workspace/teams-access.yaml (optional).
 * Falls back to permissive defaults if file missing.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const ACCESS_POLICY_PATH = join(__dirname, '../../workspace/teams-access.yaml');

const DEFAULT_POLICY = {
  mode: 'registry_only',
  exclude_groups: [],
  forbid_mcp_tools: [],
  mentions: { allow: true, allowlist_only: false },
  allowed_chat_keys: [],
};

let _cache = null;

export function loadAccessPolicy(force = false) {
  if (_cache && !force) return _cache;
  if (!existsSync(ACCESS_POLICY_PATH)) {
    _cache = { meta: null, policy: { ...DEFAULT_POLICY } };
    return _cache;
  }
  const raw = readFileSync(ACCESS_POLICY_PATH, 'utf8');
  const parsed = parseYaml(raw) ?? {};
  _cache = {
    meta: parsed.meta ?? null,
    policy: { ...DEFAULT_POLICY, ...(parsed.policy ?? {}) },
  };
  return _cache;
}

/** @param {{ group?: string, key?: string }} chat */
export function isChatAllowed(chat, policy = loadAccessPolicy().policy) {
  if (!chat?.group) return false;
  if (policy.exclude_groups?.includes(chat.group)) return false;
  const keys = policy.allowed_chat_keys;
  if (Array.isArray(keys) && keys.length > 0) {
    return keys.includes(chat.key);
  }
  return true;
}

export function getAllowedChatIds(registryEntries) {
  const { policy } = loadAccessPolicy();
  return new Set(
    registryEntries.filter(c => isChatAllowed(c, policy)).map(c => c.id).filter(Boolean)
  );
}
