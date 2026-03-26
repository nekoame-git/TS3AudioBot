# TS3AudioBot WebUI Parity Checklist (Official -> Scheme 2)

目标：在 `recordings_server.py + recordings-ui` 中 100% 继承官方 `WebInterface` 控制能力（不减少功能）。

## 1. Route/Page Parity

- [x] `/` Home（登录、token 保存、登录态判断）
- [x] `/overview` 概览（version、system info、cpu/mem 图）
- [x] `/bots` Bot 列表与生命周期管理
- [x] `/bot/:id/server` 服务器树与订阅控制
- [x] `/bot/:id/settings` 在线 bot 配置
- [x] `/bot_offline/:name/settings` 离线模板配置
- [x] `/bot/:id/playlists/:playlist` 歌单列表/编辑器
- [x] OpenAPI 入口（可跳转到 TS3AB 自带 openapi）

## 2. Command/API Coverage (from official frontend)

### System/Auth
- [x] `json merge`（空调用用于鉴权测试）
- [x] `version`
- [x] `system info`

### Bot list / lifecycle
- [x] `bot list`
- [x] `bot connect to`
- [x] `bot connect template`
- [x] `bot disconnect`
- [x] `settings create`
- [x] `settings delete`
- [x] `settings bot set <template> connect.address`

### Bot detail / playback
- [x] `bot use <id> (bot info)`
- [x] `bot use <id> (info @-1 5)`
- [x] `bot use <id> (song)`
- [x] `bot use <id> (repeat)`
- [x] `bot use <id> (random)`
- [x] `bot use <id> (volume)`
- [x] `bot use <id> (play <url>)`
- [x] `bot use <id> (add <url>)`
- [x] `bot use <id> (pause)`
- [x] `bot use <id> (next)`
- [x] `bot use <id> (previous)`
- [x] `bot use <id> (seek <sec>)`
- [x] `bot use <id> (data song cover get)`（封面 URL）

### Server tree / whisper / subscribe
- [x] `bot use <id> (server tree)`
- [x] `bot use <id> (whisper list)`
- [x] `bot use <id> (bot move <channelId> [password])`
- [x] `bot use <id> (whisper subscription)`
- [x] `bot use <id> (subscribe channel <channelId>)`
- [x] `bot use <id> (unsubscribe channel <channelId>)`
- [x] `bot use <id> (whisper off)`
- [x] `bot use <id> (bot name <newName>)`

### Settings
- [x] `bot use <id> (settings get)`（在线）
- [x] `bot use <id> (settings set <path> <value>)`（在线）
- [x] `settings bot get <template>`（离线）
- [x] `settings bot set <template> <path> <value>`（离线）
- [x] 远程版本列表（原版从 `ReSpeak/tsdeclarations` 取 `Versions.csv`）

### Playlists
- [x] `bot use <id> (list list)`
- [x] `bot use <id> (list create <id> <title>)`
- [x] `bot use <id> (list delete <id>)`
- [x] `bot use <id> (list play <id> [index])`
- [x] `bot use <id> (list get <id>)`
- [x] `bot use <id> (list name <id> <title>)`
- [x] `bot use <id> (list add <id> <link>)`
- [x] `bot use <id> (list item delete <id> <index>)`
- [x] `bot use <id> (list item name <id> <index> <title>)`
- [x] `bot use <id> (list item move <id> <from> <to>)`
- [x] `bot use <id> (list item get <id> <index>)`
- [x] `bot use <id> (list import <id> <url>)`

## 3. UX / Behavior Parity

- [x] 本地存储 token 并自动复用
- [x] 统一错误提示（HTTP/Command error）
- [x] 状态轮询（connecting bot、overview 图）
- [x] 在线/离线 bot 设置双模式
- [x] 不改变原命令语义与权限要求

## 4. Done Criteria

- [x] 上述 Route/API/UX 项全部打勾
- [x] 与官方 WebInterface 功能对照回归通过
- [x] 任何官方可完成操作在方案2中可完成（无功能缺口）

## 5. Verification Record

- [x] 2026-03-27：`Tools/webui_parity_smoke.ps1` 执行通过（`14/14 passed`）
