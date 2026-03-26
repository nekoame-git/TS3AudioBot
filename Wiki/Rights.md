The rights system is your way to permit (or deny) users calling botcommands and much more.

# The Rights File
The rights file is stored in a format called TOML. You can look up the syntax specifications at the [official TOML Repository](https://github.com/toml-lang/toml)

# Rules
Each rule declares what a user can and cannot do.  
A user can match to multiple rules when making a request.

Each rule is build up like that:
```toml
[[rule]]
    # stuff for first rule

[[rule]]
    # stuff for second rule

# ... further rules
```
You can have as many seperate rules as you want this way.

## Declarations
A rule can add and revoke permissions like that:
```toml
[[rule]]
    # permissions added to the "+" attribute are granted
    "+" = ["A", "B"]

    # permissions added to the "-" attribute are revoked when merged with other rules
    "-" = [ "C" ]
```
Note that permissions which are in both, `"+"` and `"-"`, are immediatly overwritten by the `"-"` and therefore revoked.  

You can also have the `"+"` and `"-"` declrarations before the first rule. They are added to the 'top level rule'. This rule will applied to everyone (as long as you dont add a matcher).

## Matcher
A matcher decides when a rule applies to a user.
A rule without any matcher will always apply to each user.
So be careful when creating important rules not to forget to add at least one matcher.  
We recommend you to add declarations you want to give everyone to the top level rule.  
Adding matcher to the top level rule is possible but discouraged as it is the only rule you will not be warned when leaving without matcher.  
You will be warned when you create other rules without matcher.  
Warnings can be ignored, but at your own risk.

Matcher can be declared like `"+"` and `"-"` anywhere in a rule, but preferably at the top.
```toml
[[rule]]
    # example matcher
    groupid = [ 42, 44 ]
    useruid = [ "VG90YWxseU5vdEZha2U=" ]

    "+" = ["A", "B"]
```

All matcher within one rule work like a big OR-Statement. A user can also meet multiple matcher (so it's not exlusive).  
In this example this rule applies when a user is in the server group 42, 44 or has the specified uid.

Currently available matcher are
- `groupid`: matches a server group id
- `useruid`: matches a users uid
- `host`: matches when the requested bot is connected to the specified host address. (Note that this compares the address in the *config*; *not* the final resolved ip.)
- `channelgroupid`: matches a channel group id
- `perm`: matches when user has a certain ts3 permission. This is an expression, so for e.g. you can write "i_client_talk_power>10" when the reqired right has to be higher than 10. Vaild comparators are `>`, `>=`, `<`, `<=`, `=`, `!=`. Boolean permissions can be compared with `true`/`false` or `1`/`0` as you like.
- `visibility`: Matches when a user writes with a given visibility. Possible options are: 
  - `Private` = Direct message with the bot
  - `Channel` = Channel tab message
  - `Server` = Server tab message
- `isapi`: `true` when the call is from the web-api, `false` otherwise.
- `apitoken` matches a specific api token from a user. This only matches when the call is from the web-api.
- `bot` matches when the request goes to a Bot instance with the given template name.

## Nesting Rules
You have seen that multiple matcher in the same rule work like OR, with nested rules you will now get AND-statements

```toml
# first level rule
[[rule]]
    # stuff for first level rule...
    groupid = [ 42, 44 ]
    "+" = ["A", "B"]

    # second level rule
    [[rule.rule]]
        useruid = [ "VG90YWxseU5vdEZha2U=" ]
        "+" = ["C"]
        "-" = ["B"]
```

Ok, there a multiple things happening here.
1. _The new matching order_: The first rule will match when a user is in group 42 or 44.
The second group will additionally match _only_ when the user also has the specified uid.  
1. _Nested permission calculation_: When only the first rule matches permissions are granted just as we already know.
When the second group additionally matches, all its `"-"` declarations will revoke `"+"` declarations of all parent rules in this hierachy.  
In this example the user would be left with "A" and "C".
You can nest rules as deep as you want.

## Merging rules
When a user gets matched two or more rules at a call all those rules will be merged.
This process is pretty straight forward. After all nesting calculations have been done all remaining `"+"` declarations are simply added up.

Example:
```toml
[[rule]]
    "+" = [ "A", "B" ]
    # "-" declarations without parent declaratons are useless

    [[rule.rule]]
        "+" = [ "C", "D" ]
        "-" = [ "A" ]

[[rule]]
    "+" = [ "E" ]

    [[rule.rule]]
        "-" = [ "B" ]
```
Let's assume all rules including their nested rules match.  
The first rule together with its nested rule will result in [ "B", "C", "D" ].  
The second rule will result in [ "E" ]. Note that the `-B` has no effect since there are no `+B` declarations on its parent path.  
Finally all rules will be added and the result is [ "B", "C", "D", "E" ].

# Groups
Groups are a convenient way to group a set of permissions together.

Group names have to start with an `$`. They are declared like this
```toml
["$name"]
    "+" = [ "A" ]
```
Same as rules, groups can also be nested with the same permission calculations as rules.  
Groups must always have a unique name within their scope. The scope is always defined as the current rule the group is defined on or nested deeper.

You can then include groups in other rules or even in other groups with an `include` statement;
```toml
[[rule]]
    include = [ "$name" ]

    "+" = [ "B" ]
```
The calculation order is as following:  
At first the group is calculated completely.  
Then the groups `"+"` is added to the rule.
Then the groups `"-"` is applied over the resulting `"+"`.  
(Same goes for group in group include)

# Rights and the Commandsystem
By default all commands from the bot have their own matching permission automatically generated. This also applies to loaded plugins.
The required permission for each call is `cmd` + `calling path` with dots instead of spaces.
So for e.g. `!rights reload` will require `cmd.rights.reload`

When you want to grant a permission with all its subpermission you can use a `.*`
So for e.g `cmd.api.*` whould match on `cmd.api`, `cmd.api.token`, `cmd.api.nonce`, ...

## Special rights
Additional permissions currently are:
- `ts3ab.admin.volume`: Required to set the volume above the `AudioFramework::maxUserVolume` config value.
- `ts3ab.admin.list`: Required to delete or modify playlist from other users

# Tips 'n Tricks
## Short declaration form
All matcher, includes, "+", "-" have a short form for when you only have one value on the right.
```toml
# So instead of
"+" = [ "A" ]
# you can simply write
"+" = "A"
```

## Reload the File
When you made changes to the rights setup you can reload the configuration with `!rights reload`. No restart needed!

# Examples
*Note*: As everywhere in toml, indentation is completely optional and only added for clarification.

## Example 1
Lets say you want to give a certain user *all* permissions for two specific bot templates (instances)
```toml
# This rule matches when we use the bots with themplate name "default" or "mycoolbot1"
[[rule]]
bot = [ "default", "mycoolbot1" ]

    # This childrule only gets reached when the parent matches.
    [[rule.rule]]
    # This rule self only matches when the requesting user has the given uid
    useruid = "uA0U7t4PBxdJ5TLnarsOHQh4/tY="
    # give him everything!
    "+" = "*"
```

## Example 2
Lets say you want to give all users playing permissions which are in a special servergroup on your server
```toml
# This rule matches when we use any bot which is connected to 'splamy.de'
[[rule]]
host = "splamy.de"

    [[rule.rule]]
    # Match for all users in the server group '6'
    groupid = 6
    # we could also write:
    # groupid = [ 6 ]
    # That way you can add more groups like [ 6, 7, 10, 42, ... ]

    # The permissions for !play and !add
    "+" = [ "cmd.play", "cmd.add" ]
```

## Example 3
Lets say you want to deny all users to use playing commands in private chat so no one can secretly tell the bot to stop.
```toml
[[rule]]
    # This rule matches whenever the chat where the command was recieved is a private chat
    visibility = "Private"
    "-" = [
        "cmd.play", "cmd.pause", "cmd.stop", "cmd.seek",
        "cmd.volume",
        "cmd.history.play", "cmd.history.last", "cmd.list.play",
        "cmd.kickme", # We also don't want the user to kick himself while he is not in the same channel
    ]
```