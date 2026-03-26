The bot is fully operable via chat and the http [web api](https://github.com/Splamy/TS3AudioBot/wiki/WebAPI).  
You can get a basic overview with `!help` or in the TSAudioBot integrated live api generator at `http://localhost:58913/openapi/index.html`  
If you don't have a TSAudioBot running you can also go to [our openapi geneartor](https://tab.splamy.de/openapi/index.html).


# Basic commands
All commands are invoked like `!command`.

## Command Syntax
Every command is build up by the following scheme  
```cs
!<commandname> <parameter1> <parameter2> ...
```

## The help command
Whenever you feel lost or don't know how a command works you can send
```swift
!help command <commandname>
```
to get more information about a certain command

## Subcommands
Some commands have so called 'subcommands', for example
```swift
!history play <num>
!history rename <old> <new>
!history last
!history clean removedefective
//etc.
```
We created them to keep commands logically together so you can find them better. As always when you dont know which subcommands are available simply write `!help command <commandname> (<subcommand> ...)`

## Command matching
The string matcher can still find the correct command for you even if you misspell it. This way
```swift
!historyy lastt 10
!his la 10
// or even
!higsndtor latuht 10
```

for example should all match to
```swift
!history last 10
```
This works by picking the command with the most matching characters.
So the last example would match on `hi_s__tor lat___` with 6 and 3 characters. Therefore the best match is `history` and `last`.

NOTE: `!ahistory last 10` will not match since the algorithm is greedy. The word `history` with no 'a' will be filtered out inbefore.  

(You can change the matching algorithm in the config, or in the webinterface per bot)

## Escaping
Since spaces seperate parameters you have to quote a string if it has to contain spaces, like this:
```js
!history rename 123 "New Song Name"
// or
!history rename 42 'New Song Name'
```

You can use either double quotes or single quotes to open a string, the other quote kind will not end the string when used within.

Note that a single double quote (without closing quote) will not be interpreted as a control sequence but instead as a normal text character.
```swift
!bot name Funky"Name
```
Will rename the bot to `Funky"Name`

On the other hand if you want quotes in an already quoted string you can escape them with a backslash.
```js
!bot name "Funky\" \"Name"
// or
!bot name 'Funky" "Name'
```
Will rename the bot to `Funky" "Name`

The last characters which need to be within quotes are '(' and ')', since they are used for command chaining (see further below)
```swift
!bot name "(sneaky)"
```
Will rename the bot to `(sneaky)`

# Command Chaining
## Chaining syntax
```swift
!<level1_1> (!<level2_1> <param2_1> <param2_2>) <param1_2> (!<level2_2> (!<level3_1>)))
```
A chained command is indicated with `(!...)`; please notice that there must be no space between '(' and '!'

## Simple chaining
If you want to combine two commands you can easily do that by 'chaining' them. Example:
```swift
!history play (!rng 0 100)
```
This will play a random song from the history by an id between 0 and 100.

## Execution order
The system will by default execute commands lazily from left to right. Lets take a look at at this simple example
```swift
!print (!list load .queue) (!list show)
```
We start at `!print` but print has two parameter which have to be executed first. We start at the first `!list load .queue` which only has two static parameter, so it can be executed. Now the second parameter `!list show` which -again- has only one static parameter and can be executed. Now all parameter of `!print` have been evaluated and print can be run.  
So this chained command actually loads the playlist named '.queue' and shows the content in one call.

Here's a bit more complex example:
```swift
!if (!rng 1 10) == 6 (!kickme (!if (!rng 1 2) == 1 near far)) (!print "You're lucky")
```
We start at the `!if` command, before the if command executes, we need to look at the parameter. The first parameter is `(!rng 1 10)` which itself has two static parameters and can be executed. Then the second and third parameter are static, `==` and `6`. Lets say we got a '6' from the `rng` so the 'true' branch will be executed. The next command therefore is `!kickme`. kickme can have an optional parameter so the first parameter has to be executed before we can continue in kickme. `!if` will now execute by the same scheme as the 'big if' and either return `near` or `far` which will then be passed to kickme.

## Parenthesis ommiting
```swift
!print My first number: (!rng 0 100) My second number (!rng 0 100
```
All closing brackets can be omitted. Unless you need them semantically like in the example.

On the other hand you can add superfluous closing brackets as much as you want. The will simply be ignored.