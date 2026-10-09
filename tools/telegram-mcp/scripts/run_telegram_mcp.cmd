@echo off
setlocal
cd /d "%~dp0.."
bun run src/index.ts
