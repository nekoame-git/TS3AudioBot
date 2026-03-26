# Managing Playlists
All playlist related commands start with `!list`, if you need help for a command, you can just execute `!help command list` or `!help command list add`, ...  
All playlists are persistently stored per bot. They are accessed with the `<listId>` for each action/modification. The `<listId>` can be any alphanumeric string.

## Working with a playlists

### Modifying items
* `!list add <listId> <url>` Adds a song to the playlist.
* `!list insert <listId> <index> <url>` Inserts a song to the playlist at the given index.
* `!list item move <listId> <from> <to>` Move an item to another position.
* `!list item delete <listId> <index>` Delete an item from the playlist.

### Managing playlists
* `!list create <listId>` Creates a new empty playlist.
* `!list delete <listId>` Deletes a playlist.
* `!list import <listId> <url>` Imports a playlist from a local folder, YouTube or other supported platforms.
* `!list show <listId> (<startOffset>) (<count>)` Show the songs in the current playlist.
* `!list name <listId> <name>` Changes the title of the playlist.
* `!list list (<filter>)` Lists (or filters for) all saved playlists. Search can contain wildcards (`*`)

### Actions
* `!list play <listId>` Replaces the current playback with this playlist and starts it.
* `!list queue <listId>` Appends the playlist to playback and starts it.
* `!repeat off/one/all`
  - `off`: Does not repeat. The playback stops when the last song was played.
  - `one` Repeats a single element.
  - `all` Repeats the entire playlist.