# Basics

## Creating templates
- Use `!bot connect to <ip/address/nickname>` to connect to a new server
- Write `!bot save <template name>` to the new instance if you want to store it and the identity with it as a new bot template.
- Use `!bot connect template <template name>` to connect a saved template again.
- Use `!bot disconnect` to disconnect a bot again.

- Use `!settings create <name>` to create a empty bot template.
- Use `!settings delete <name>` to delete a bot template again.

# Root and bot config

## Accessing
- `!settings get/set` uses the `<name>/bot.toml` file of the bot you are *currently* writing with
- `!settings bot get/set <name>` uses the `<name>/bot.toml` file of the bot you *specified in the command*
- `!settings global get/set` uses the `ts3audiobot.toml`

## Overwriting

The `ts3audiobot.toml` contains all global settings as well as the defaults for all bots.  
You might also notice that new bots come with a very empty `bot.toml` file.  
This is because when a value is not specified in the file the default from the `ts3audiobot.toml` will be used.

To make it clear which values can be overridden per bot, those values are groupd into `[bot]`.

Lets look at an example:

This is in the ts3audiobot.toml file (other fields are left out for brevity):
```toml
[bot]
language = "en"

[bot.connect]
name = "MusicBot"

[bot.events]
onconnect = "!pm channel 'Hey, I'm back'"
```

This is in the bot.toml file:
```toml
# Since [bot] has no other subgroup, those fields are put at the top
# This bot will now use the language "de" instead of "en"
language = "de"

# Note that if we don't specify connect.name the bot will use the default from
# the root config which is "MusicBot"
# [connect]
# name = "Special Bot"

[events]
# This overwrites the events.onconnect from the root config.
onconnect = "!pm channel 'My custom greeting'"
```

Note that in the `bot.toml` that the `bot.` prefix for all paths is simply removed.


# Bot folder

You can add folders to the bot folders for special features.  
The special bot folder structure looks like this:
```ex
./bots          # this is your normal 'bots' folder where all bots are
  /super_bot    # In our example we use the bot 'super_bot'
    bot.toml    # This is the normal bot config file
    /music
    /playlists
    /avatars
```

- `music`: You can add music files into this folder and the bot will look in this folder first before in the global music search path.
- `playlists`: The bot will automatically manage playlists which you create in this folder. But you can add or remove them manually too.
- `avatars`: The bot will look for avatars in this folder.
  - `play*`: Whenever a song is played without icon the bot will choose a random file starting with `play`. For example `play1.png` or `play_totoro.jpg`
  - `sleep*`: When playback stops the bot will pick a random file starting with `sleep`. For example `sleep.png` or `sleepCat.svg`

Note that by default the folders are not created. The bot might create them automatically when necessary, but you can create and use them just as well.