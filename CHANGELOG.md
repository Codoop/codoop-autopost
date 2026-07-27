# Changelog

All notable changes to Codoop-autopost will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1-alpha.1] - 2026-07-27

### Added

- 一个插件内置项目初始化、内容工单、热点发现、来源核验、润色和 X 发布入口。
- `codoop-autopost-init`：通过逐题访谈确认根目录 `PROJECT.md` 与 `VOICE.md`。
- `codoop-content-ticket`：以 `content-tickets/C-...` 保存一张内容工单的全流程产物。
- 仅在人工明确批准后，使用 X 官方 API 定时发布。

### Changed

- 工单状态与发布回执完全保存为本地文件，不使用数据库。
- 移除可选的 Skill UI 元数据和无用的 macOS/Python 本地文件。
