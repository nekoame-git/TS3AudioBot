A list of notable (breaking) changes.

### `f913536594129656f9758b4332555a207d9dc09c` - 2020-03-24
- `!bot info client` now returns a `Client` object instead of `ClientInfo`  
  Check the openapi doc if you need to adjust your json fields

### `eba64d4c040a88a4502e47a03d62fadbac54b70f` - 2019-11-18
- The `TS3Client` folder and namespace has been moved to `TSLib`. This should affect plugins which reference the ts client library directly.

### `f88757442e1674cab9bfe7a6fd2d943daa7c1324` - 2019-10-06
- `!song` json response fields are now capitalized to be more consistent with the rest
- `!queue` has been removed. All information of it were covered in `!info`
- `select <num>` has been removed.
  Check out the faq for [an up to date example](https://github.com/Splamy/TS3AudioBot/wiki/FAQ#search-and-play-youtube-songs)  
The new replacing commands are:
   - `!search play <num>`
   - `!search add <num>`

### `5974c1aa1c943d5a74a847a521c020967efc14b3` - 2019-09-06
- `!list get <url>` has been moved to -> `!list import <listId> <url>`
- `!list load/save` have been removed. All lists are now persistent and have to be specified with the `<listId>`
- All `!list *` commands take a <listId> as the first parameter to specify which playlist to interact with.

### `5fff90a87969ad54558da98997b9016ecc021cb9` - 2019-06-19
The volume value is now scaled logarithmically to better reflect the 'perceived' volume.
It's recommended to update the following config values for reasonable default and reset volumes.
```toml
[bot.audio]
# values 70-100 are reasonable. 100 as the max value effectively disables this feature.
max_user_volume = 80.0
# 50 Is the middle, making it an good default volume with the new scaling.
# Volume 50 in the new scale is equal to 10 in the old scale.
volume = { default = 50.0, min = 25.0, max = 75.0 }
```

### `914a61994f72d718d719f85f525891ce47b1800c` - 2019-05-24
- ! Updated required frameworks
  - net46 -> net472
  - dotnet core 2.0 -> dotnet core 2.2

  This means you will need at least `mono 5.18` or `dotnet core 2.2` to run.  
  Building manually will now build to `./Release/net472` and `./Release/netcoreapp2.2` instead of `./Release/net46` and `./Release/netcoreapp2.0` respectively.
- The `rights.toml` has `ip == localhost` as a default matcher for admin privileges. This should prevent a lot of hassle when just trying to access it locally.  
  If your server is behind a proxy, either make sure to make it transparent, or use `X-Real-IP` header, or remove this matcher.

### `4b371b95421f816f3142fe4e80d5dc86bad1f409` - 2018-11-25
- Merged `!song position` into `!song`.
- Added a `.paused` field in the `!song` response

### `fe2520fa08670d161f676fc45eccf861716deb08` - 2018-11-22
- Reworked playlist and queue
- Added `!info` for a small current playlist and queue summary
- Added `!queue` to show the current queue

### `08e948f681a37de5a6644ba6739458b390d0ed95` - 2018-10-30
- Added `!settings copy` to clone bot templates

### `a78070df6a2d85814e1284d00d7cde6dd0e0da3f` - 2018-10-18
- Added `!settings create` and `!settings delete` to create and delete bot templates

### `bc04e961367bb29a752e55fc7b1d7549a4cdb1aa` - 2018-10-04
- Moved `!quit` to `!system quit`

### `512aa2ae364c3c5975aceacc50be3ab8616cbc61` - 2018-09-23
- `!bot info` now has a `Status` field when called via api
- The `"botname" = { run = true/false }` fumbeling has been removed from the `ts3audiobot.toml` file. Instead each bot config now has `run = true/false` field in the root section.

### `cc2263dd4aa488e523d389cfc8e24eeb9b609f80` - 2018-09-16
- The command `!link` was removed since `!song` already shows the song title and adds the link as a hyperref to it.  
  To compensate this in the api the `!song` command now returns an object of `{ title:"...", source:"..."}`
- ! Don't forget to remove "cmd.link" from your rights file to prevent warnings in the log about it.

### `2ca7028a73e0ffd4f68be65e766b8f0a6caf9dfd` - 2018-09-15
- Changed `!bot avatar` to `!bot avatar set <link>` and `!bot avatar delete`

### `d45044984877fa07fa3675371349c52bda632560` - 2018-08-30
- The command `!loop <on|off>` was removed and instead merged functionality into
- `!repeat (off|one|all)` (this also means `!repeat (on|off)` also doesn't work anymore)
- ! Don't forget to remove "cmd.loop" from your rights file to prevent warnings in the log about it.