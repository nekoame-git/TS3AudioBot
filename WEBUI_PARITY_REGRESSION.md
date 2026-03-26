# TS3AudioBot WebUI Parity Regression

用于执行方案2（`recordings_server.py + recordings-ui`）的功能回归并收尾 checklist。

## 1) 前置条件

- 已启动 TS3AudioBot WebAPI（默认 `http://127.0.0.1:58913`）
- 已启动本项目 WebUI 服务器（默认 `http://127.0.0.1:8765`）
- 已在 UI 保存 `authUser/authToken`

## 2) 自动冒烟（推荐先跑）

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\Tools\webui_parity_smoke.ps1 `
  -WebUiBase "http://127.0.0.1:8765" `
  -AuthUser "<uid>" `
  -AuthToken "<token>" `
  -TemplateName "<offline-template-name>" `
  -BotId <online-bot-id>
```

通过标准：

- 脚本输出 `Smoke summary: X/X passed`
- 退出码 `0`

## 3) 手工重点回归

1. `Home`
- `json merge` 鉴权测试通过
- OpenAPI 链接可打开

2. `Overview`
- `version/system info` 正常显示
- `Versions.csv` 列表可刷新并展示行数据

3. `Bots`
- 模板创建/删除
- 连接模板启动 / 断开在线 bot
- quick connect 可发起

4. `Bot`
- `play/add/pause/next/previous/seek/volume/repeat/random`
- 当前歌曲、队列、封面展示

5. `Server`
- 树结构读取
- move/rename/subscribe/unsubscribe/whisper subscription/off

6. `Settings`
- 在线 bot 设置 get/set
- 离线模板设置 get/set（模板输入/下拉）

7. `Playlists`
- list/create/delete/play/get/name/add/import
- item delete/name/move/get

8. `Recordings`
- 目录切换（受限范围）
- 会话详情、音频播放、单条/批量转录

## 4) Checklist 收口规则

以下三项仅在“自动冒烟 + 手工重点回归”都通过后勾选：

- `与官方 WebInterface 功能对照回归通过`
- `任何官方可完成操作在方案2中可完成（无功能缺口）`
- `上述 Route/API/UX 项全部打勾`
