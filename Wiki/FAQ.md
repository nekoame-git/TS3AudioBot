### Bot is Banned
**Q**: I get this in my log: `connect_failed_banned: the command failed to execute: connection failed, you are banned`

**A**: You can choose which option fits you better:
- Either set the `b_client_ignore_bans` permission flag for any group where the bot is in.
- Or clear the `QueryConnection::identity` config entry to generate a new identity.  
  **Warning**: if your bot is on a server where he got special permissions or was added in a special group, you will loose those.
<hr>

### API Missing Context
**Q**: On request I get something like this result:
```json
{
    "ErrorCode": 17,
    "ErrorName": "MissingContext",
    "ErrorMessage": "Command 'CommandPlay' missing execution context 'IPlayerConnection'"
}
```

**A**: This message can have multiple causes.
- The most common problem will be that you need to switch to a bot before you can use a bot specific command.  
For example: `http://localhost:8180/api/bot/use/0/(/play/music.mp3`  
where `0` is the bot id.  
You can list all bots with `!bot list`.

- If the missing module is called `InvokerData` see the next FAQ entry.

- It might also be that the module which you are trying to use is disabled.
This is for e.g. possible with the `HistoryManager`
<hr>

### API Missing Context InvokerData
**Q**: On request I get this result:
```json
{
"ErrorCode": 17,
"ErrorName": "MissingContext",
"ErrorMessage": "Command 'CommandPlay' missing execution context 'InvokerData'"
}
```

**A**: You need to authenticate the call. See [here in the wiki](https://github.com/Splamy/TS3AudioBot/wiki/WebAPI#authentication) for more information.
<hr>

### License
**Q**: Is there any tl;dr on the license?

**A**:
This site gives you a quick overview what you can and must do: https://tldrlegal.com/license/open-software-licence-3.0  
If you want a better explanation to a particular section of the license, the author of the license has created a site to explain the reasoning and ideas behind the legal text: https://rosenlaw.com/OSL3.0-explained.htm
<hr>

### Set the client version
**Q**: How do I set the client version of the bot to (insert version here)?

**A**:
Go to this site and pick the version of your desire: https://github.com/ReSpeak/tsdeclarations/blob/master/Versions.csv  
Go to your bots/\<name>/bot.toml config. (Where \<name> is the bot template name you are connecting.)  
Now set the triplet you chose:  
```toml
[connect]
client_version = { build = "3.1.10 [Build: 1528537615]", platform = "Windows", sign = "+/BWvueikGg4YkO1v2uuZB5vtJJgUZ5bL8cRfxAstfnCVdro2ja+4a+8rGUzDx8/vvTZOUVD6U95hnWb638MCQ==" }
```
you can also write it the long table notation if you prefer. (The bot might still convert it if he wants to.)
```toml
[connect.client_version]
build = "3.1.10 [Build: 1528537615]"
platform = "Windows"
sign = "+/BWvueikGg4YkO1v2uuZB5vtJJgUZ5bL8cRfxAstfnCVdro2ja+4a+8rGUzDx8/vvTZOUVD6U95hnWb638MCQ=="
```
<hr>

### Bot is not playing music
**Q**: I type `!play ./musicFile.mp3`, the image and description change, but I cannot hear anything.

**A**: By default, the bot's AudioMode is `whisper`. If you want the bot to play the sound in the room it is in, you have these options:
- Give the bot group a high enough `i_client_whisper_power`.
- Type command `!whisper off` every time after typing `!play` command. 
- Change `audio.send_mode` in your `bot_<name>.toml` to `voice`

If the 'speaking' light is showing up, check that the volume is not 0 by settings it to a reasonable volume: `!volume 50`
<hr>

### Missing rights
**Q**: I'm getting `You can not execute "play". You are missing the "cmd.play" right.!` when I try to execute a command.

**A**: The bot is very strict what each user can call. In this example we want to call `!play` but this applies for any other command too.  
Create or modify a rule which matches to you. The simplest matcher is by `useruid` so we will use it in this example.  
```toml
[[rule]]
# Add your uid to the matcher.
# You can add multiple uids which this rule should match on.
useruid = [ "VG90YWxseU5vdEZha2U=", "AnotherOnesUid" ]

# The "+" permissions will be added when this rule matches.
"+" = [
    # This is a list of all permissions we want to grant.
    "cmd.play",
    "cmd.some.other.command",
    "cmd.bot.commander.on",
    # You can use wildcards to add an entire command group
    "cmd.whisper.*",
    # Or even root wildcards to add all permissions (be careful with this)
    "*"
]
```
There are a lot of more matcher, you can read about them in our wiki [here](https://github.com/Splamy/TS3AudioBot/wiki/Rights#matcher).
Or take a look at the [rights documentations](https://github.com/Splamy/TS3AudioBot/wiki/Rights) in general.
<hr>

### Text responses
**Q**: Where do I find string xzy?

**A**: All strings are in the [TS3AudioBot/Localization/strings.resx](https://github.com/Splamy/TS3AudioBot/blob/master/TS3AudioBot/Localization/strings.resx) file. You need to recompile the project for changes to take effect.
<hr>

### Search and play YouTube songs
**Q**: Is there a way to search for YouTube songs (`!yt`) or search and play by title (`!ytp`)?

**A**: If you just want a `!yt` and `!ytp`/`!yta` command, simply add those two aliases:  
`!alias add yt "!search from youtube (!param 0)"`  
`!alias add ytp "!xecute (!search from youtube (!param 0)) (!search play 0)"`  
`!alias add yta "!xecute (!search from youtube (!param 0)) (!search add 0)"`  

then you can use:  

`!yt rammstein sonne` will display the found results  
```
Found the following songs. Use "!select <number>" to play.
0: Rammstein - Sonne (Official Video)
1: Rammstein - Sonne (lyrics) HD
2: Rammstein - Sonne / PROSHOT(Download Festival 2016) HD [GER/ENG/RU/ES/FR]
   ...
```

`!ytp rammstein sonne` will search and play the first result.
`!yta rammstein sonne` will search and queue the first result.
<hr>

### Login to Webinterface
**Q**: How can I log into the webinterface?

**A**: Send `!api token` to the audiobot in a private chat and copy the answer into the login field on the webinterface.
<hr>

### 429 Too Many Requests
**Q**: I'm getting something like `HTTP Error 429: Too Many Requests`

**A**: `HTTP Error 429: Too Many Requests` means you are hitting the rate limiting of YouTube.  
There is nothing we can do about this.  
- Try waiting a few hours before starting the next request.
- Try delete your youtube-dl cache folder ([see our issue](https://github.com/Splamy/TS3AudioBot/issues/772#issuecomment-616799057), [or youtube-dl issue](https://github.com/ytdl-org/youtube-dl/issues/23638))
- [youtube-dl also has an FAQ Entry for this](https://github.com/ytdl-org/youtube-dl#http-error-429-too-many-requests-or-402-payment-required)
- Use a [proxy for youtube-dl](https://github.com/ytdl-org/youtube-dl/blob/master/README.md#configuration), some free services are listed in [this issue comment](https://github.com/Splamy/TS3AudioBot/issues/819#issuecomment-651351082)
<hr>

### Streams stop
**Q**: Radiostreams randomly stop or are interrupted.

**A**: Radiostreams alyways may have hiccups or the stream might reset.
You can mitigate this in multiple ways:
- Set `!repeat one`: This will simply try to restart the stream multiple times when it stops.
- Create a playlist and put one (or more fallback streams) in it. Then start it with `!list play <name>` and set `!repeat all`
<hr>

### GitVersionTask
**Q**: I'm getting errors in my build with `GetAssemblyVersion` or `GitVersionTask`.

**A**: You can choose **any of these** steps to fix the build:
- Download the project with `git clone https://github.com/Splamy/TS3AudioBot` instead of the normal 'Zip-Download'
- Remove the `GitVersionTask` NuGet package from the Ts3AudioBot project ([How to in VS](https://docs.microsoft.com/en-us/nuget/tools/package-manager-ui#uninstalling-a-package))  
  You also can easily do that from the console with `dotnet remove TS3AudioBot package GitVersionTask`
- Remove [these lines](https://github.com/Splamy/TS3AudioBot/blob/eed3b683118207168f421048bb30b67d39f0f221/TS3AudioBot/TS3AudioBot.csproj#L37-L40) from the `TS3AudioBot/TS3AudioBot.csproj` file. This is the same as the previous option but without UI or VS.
<hr>

### Autostart
**Q**: How can I autostart the bot when my server starts?

**A**: You can choose **any of these**:
- Start the bot inside `screen` or `tmux`
- Create a systemd service:

1. Create a new user called teamspeak: `useradd -m teamspeak`
1. Download the native bot build into `/home/teamspeak/TS3AudioBot/` so that the binary is in `/home/teamspeak/TS3AudioBot/TS3AudioBot`
1. Create the file `/etc/systemd/system/ts3audiobot.service`:
    ```ini
    [Unit]
    Description=TS3AudioBot
    After=teamspeak.service

    [Service]
    Type=simple
    User=teamspeak
    Group=teamspeak
    KillSignal=SIGINT
    Restart=on-failure
    RestartSec=10
    WorkingDirectory=/home/teamspeak/TS3AudioBot/
    ExecStart=/home/teamspeak/TS3AudioBot/TS3AudioBot

    [Install]
    WantedBy=multi-user.target
    ```
1. Run `systemctl daemon-reload`
1. Enable and start the service: `systemctl enable --now ts3audiobot`

&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
&nbsp;  
[padding]