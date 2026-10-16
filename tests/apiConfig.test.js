import test from 'node:test';
import assert from 'node:assert/strict';

import { resolveApiBaseUrl } from '../src/apiConfig.js';

test('development defaults to the same-origin API proxy', () => {
  assert.equal(resolveApiBaseUrl('', false), '/api');
});

test('production requires an explicitly configured backend URL', () => {
  assert.throws(
    () => resolveApiBaseUrl('', true),
    /production backend URL is not configured/i,
  );
});

test('production accepts a public HTTPS API base and removes a trailing slash', () => {
  assert.equal(
    resolveApiBaseUrl('https://api.example.com/campus/api/', true),
    'https://api.example.com/campus/api',
  );
});

test('production rejects localhost, insecure, relative, and non-API URLs', () => {
  for (const value of [
    'http://api.example.com/api',
    'https://localhost:8000/api',
    '/api',
    'https://api.example.com/v1',
  ]) {
    assert.throws(() => resolveApiBaseUrl(value, true), /VITE_API_BASE_URL/i);
  }
});
