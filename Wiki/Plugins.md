# Getting started
To get started create a folder like `Plugins` and set the path in your config accordingly.
```toml
[plugins]
#The path to the plugins folder. Can be relative or absolute
path = "Plugins"
```

## Available Extension Options
There are two different kinds of classes you can extend the bot with:
- `IBotPlugin`/`ICorePlugin` The extension tools for commands and new functionality
- `IFactory` A provider to resolve links for the commands `!play` and `!list` (playlists)
 (Resource-Factories are used to extract a playable link from, for example, a youtube link or twitch link, etc.)

## Storing Plugins
There are two ways to add your plugin to the bot.
1. For quick testing or development you can simply add a `*.cs` file into the plugin folder and the bot will automatically compile it for you when requested.
*Note* that that this method will use a lot more memory, especially when reloading multiple times!
2. The usual way is to place the compiled .NET `*.dll` with all its dependencies into the plugins folder.

## Listing plugins
To list all your plugins send `!plugin list` to the bot.
```
#0|OFF|MyFile1.cs
#1|RDY|Plugin: MyPlugin2
#2|+ON|Factory: youtube
#3|UNL|Plugin: <unknown>
#4|ERR|MyFile2.cs 
```
There are different states a plugin can be in
- `OFF` A file has been found but not yet checked
- `RDY` The file was loaded without error and can be enabled
- `+ON` The plugin (or factory) was successfully enabled and is now integrated into the bot
- `UNL` The plugin was manually disabled and will not be loaded
- `ERR` There was an error loading the file (See in the console/log for detailed information)

Each id is unique and will be kept for a file even if the file gets changed or reloaded.
When a file gets deleted or renamed the id will be freed (and a new one associated).

You can load and unload your plugins with `!plugin load <plugin>` and `!plugin unload <plugin>`.
Both can take for the `<plugin>` parameter either the currently assigned id or the complete file name.

## Plugin types
There are 2 types of command-plugins you can declare depending on what you want:
- CorePlugin: Creates a plugin instance for the core. (This can access all core modules but not single bots.)
- BotPlugin: Creates a plugin instance for each bot. (This can access all core modules _and_ all modules of the bot the plugin is in.)

If you don't know which one to choose, simply pick the `BotPlugin`. This is the most versatile and will allow you to do everything.  
You can still switch later to the others if you see that you don't want to use all features and optimize the plugin a bit for resource usage.

# Command Plugins
To start with a simple plugin create an empty file and call it `MyPlugin.cs` and place it in the `Plugins` folder (this folder can be changed in the config).  

Here is a basic overview of the Plugin lifecycle and usage.

```csharp
using System;
using System.Threading.Tasks;
using TS3AudioBot;
using TS3AudioBot.Audio;
using TS3AudioBot.CommandSystem;
using TS3AudioBot.Plugins;
using TSLib.Full.Book;

public class NowPlaying : IBotPlugin /* or ICorePlugin */
{
    private PlayManager playManager;
    private Ts3Client ts3Client;
    private Connection serverView;

    // Your dependencies will be injected into the constructor of your class.
    public NowPlaying(PlayManager playManager, Ts3Client ts3Client, Connection serverView)
    {
        this.playManager = playManager;
        this.ts3Client = ts3Client;
        this.serverView = serverView;
    }

    const string NowPlayingTag = " [Now Playing]";
    string lastName = null;

    // The Initialize method will be called when all modules were successfully injected.
    public void Initialize()
    {
        playManager.AfterResourceStarted += Start;
        playManager.PlaybackStopped += Stop;
    }

    private async Task Start(object sender, EventArgs e)
    {
        var self = serverView.OwnClient;
        if (self == null) return;
        lastName = self.Name;
        await ts3Client.ChangeName(lastName.EndsWith(NowPlayingTag) ? lastName : lastName + NowPlayingTag);
    }

    private async Task Stop(object sender, EventArgs e)
    {
        if (lastName != null) await ts3Client.ChangeName(lastName);
    }

    // You should prefer static methods which get the modules injected via parameter unless
    // you actually need objects from your plugin in your method.
    [Command("hello")]
    public static string CommandHello(PlayManager playManager, string name)
    {
        if (playManager.CurrentPlayData != null)
            return "hello " + name + ". We are currently playing: " + playManager.CurrentPlayData.ResourceData.ResourceTitle;
        else
            return "hello " + name + ". We are currently not playing.";
    }

    public void Dispose()
    {
        // Don't forget to unregister everything you have subscribed to,
        // otherwise your plugin will remain in a zombie state
        playManager.AfterResourceStarted -= Start;
        playManager.PlaybackStopped -= Stop;
    }
}
```

### Initialize
The `Initialize` method gets called when your plugin gets stated (`!plugin load`) and all properties have been initialized for you.

### Dispose
When you allocate external resources, other `IDisposable` objects or make other changes to the bot, make sure to deallocate, dispose and undo all those changes in this method.

## Commands
To create a new command which can be called from the commandsystem with `!...`, simply create a method and add the `CommandAttribute` to it.  
For example:
```csharp
[Command("greet everyone")]
public static string CommandGreet(string name, int number, string optional = null)
{
    if (optional != null)
        Console.WriteLine("User opted: " + optional);
    return "Hi " + name + ", you choose " + number;
}
```
The first `CommandAttribute` constructor parameter specifies the command path which must be lower case letters and spaces only.  
In this example `"greet everyone"` will be `!greet everyone <name> <number> (optional)`.  
This path together with all parameters must be unique.  

### Input parameters

#### Basic Types
The CommandSystem will automatically serialize and deserialize all primitve types (`bool`, `byte`, `string`, ...), their nullable variant (`bool?`, `byte?`, ...), and enums when passing values to your function.

```csharp
[Command("com")]
/*..*/ Command(int num, string other, bool? optional = null)
```

#### Module Dependency Injection
The CommandSystem will also inject all Module Types.
Modules are the way the Ts3AudioBot structues its logic and functionality.  
For example `Ts3Client`, `HistoryManager`, `PlayManager`,... are modules.  
To get one injected declare it somewhere your parameter list (usually for readability at the beginning):
```csharp
[Command("com")]
/*..*/ Command(HistoryManager hm, PlayManager plm, int num, PlaylistManager optionalPm = null)
```
You can still add normal parameters just as before.  
You can also make a module optional by adding ` = null` as a default. Your command can then still be called even if the module is not present for any reason.

#### Call Dependency Injection
To get some meta information from a botcommand call you can request special types which are only present during a call.
```csharp
[Command("com")]
/*..*/ Command(InvokerData invoker, UserSession session)
```
- `InvokerData`: TS3 data about the caller of this botcommand. *Note* that many properties might be null when they couldn't get retrieved by the bot.
- `UserSession`: A temporal storage for each ts3 user which is interacting with the bot. (Cleared when user leaves the server)
- `CallerInfo` Some metainformation about the current call, contains for e.g.:
  - `TextMessage` the original complete textmessage that initiated this call
  - `SkipRightsChecks` use this to disable all further rights checks in this call. *Note* to use this with caution as this may be a dangerous security hole.
- `ExecutionInformation`: Raw access to the dependency injection of the current call.

### Output
A function can return `void`, `string` or `JsonObject`.
- `void` Nothing will be returned.
- `string` A string or `null` for a `void` equivalent can be returned to the user or a calling parent function.
- `JsonObject` This is the preferred variant for best compatibility with the chat and api. The commandsystem can decide whether the caller wants the readable string for the chat or a json-serialized object for the api.
  - `JsonEmpty` is the `void` equivalent.
  - `JsonSingleValue` will generate `{ "Value" : "yourValue" }`, use preferably for primitive types which have no structure.
  - `JsonSingleObject` will generate `{ ... }`, use this if you want to serialize an entire object.
  - `JsonArray` can be used for an array of values or objects
  - `JsonError` should not be used. The commandsystem will generate this type for you when you throw a `CommandException`.

### Aborting execution
If you encounter a problem in your command or want to indicate an error result, throw a `CommandException`.
This will exit from all botcommands stop the call execution. The user will get the error response in the chat or in the api with a 4XX status code.

Example:
```csharp
throw new CommandException("Something went wrong", CommandExceptionReason.CommandError);
// or if you want to pass through an exception
try {
    // some code that throws
} catch (Exception ex) {
    throw new CommandException("Something went wrong", ex, CommandExceptionReason.CommandError);
}
```

## Teamspeak Functions and Events

### High Level
Some functions and events of teamspeak are wrapped for easy access and use.
You can use them with the `TsFullClient` module. Example:
```csharp
using TS3AudioBot;
using TS3AudioBot.Plugins;
using TSLib.Full;
using TSLib.Messages;

namespace Example
{
    public class Example2 : IBotPlugin {
        private TsFullClient tsClient;
        public Example2(TsFullClient tsClient) {
            this.tsClient = tsClient;
        }

        public void Initialize() {
            tsClient.OnEachClientEnterView += ClientEnter;
        }
        private void ClientEnter(object sender, ClientEnterView e) {
            if (e.InvokerId != null)
                tsClient.SendPrivateMessage("Hello, you just connected to this server", e.InvokerId.Value);
        }
        public void Dispose() {
            tsClient.OnEachClientEnterView -= ClientEnter;
        }
    }
}
```

### Low Level
You can use the generic `Send` one the `TsFullClient` module to send your own commands. Example:
```csharp
using TS3AudioBot;
using TS3AudioBot.Plugins;
using TSLib;
using TSLib.Commands;
using TSLib.Full;
using TSLib.Messages;

namespace Example
{
    public class Example3 : IBotPlugin {
        private TsFullClient tsClient;
        public Example3(TsFullClient tsClient) {
            this.tsClient = tsClient;
        }

        public void Initialize() {
            tsClient.OnEachClientMoved += OnEachClientMoved;
        }
        private void OnEachClientMoved(object sender, ClientMoved client) {
            tsClient.SendPrivateMessage("Hello, you just moved to another channel", client.ClientId);

            tsClient.Send<ResponseVoid>(new TsCommand("clientkick") {
                { "reasonid", 4 },
                { "clid", client.ClientId },
                { "reasonmsg", "Oh no, what are you doing?" },
            });
            // This 'Send' example call would be the same as the already defined:
            // Client.KickClientFromChannel(client.ClientId, "Oh no, what are you doing?");
        }
        public void Dispose() {
            tsClient.OnEachClientMoved -= OnEachClientMoved;
        }
    }
}
```

# Resource Factories
[TODO]
## General

## IResourceFactory

## IPlaylistFactory

## IThumbnailFactory

# Technical stuff
Due to technical limitations each time you load/unload a plugin, a new assembly will be loaded into the application.
This means should you notice a high memory usage after a plugin developing session with many reloads. You will need to restart the bot to get to normal memory usage again.