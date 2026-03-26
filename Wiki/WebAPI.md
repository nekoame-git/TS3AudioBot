# Calling API functions
First make sure the webserver is running, and all settings are correctly set for you.
```toml
[web]
# You can restrict via which hosts the api can be accessed with.
# For example set it to `http://contoso.com` and your api will only accept calls form `http://contoso.com/api/...`
# You can set it to "*" to keep this unrestricted
hosts = ["*"]
# The port for the web server.
port = 58913

[web.api]
# !! Make sure this value is set to true before starting the TS3AB
enabled = true
```

## API call syntax
The API address is
```
http://<address:port>/api/<command>/<param1>/<param2>
```
where `<address:port>` is your server address and the configured port (default `58913`).

## Simple API call
```
http://localhost:8180/api/history/last/10
```
This will get a JSON array with the last 10 played songs.

## Escaping
All parameter need to be URL Encoded (see [here](http://www.w3schools.com/tags/ref_urlencode.asp) or [here](https://en.wikipedia.org/wiki/Percent-encoding)).

For example if you want a parameter with a space or slash it would look like that:
```
http://localhost:8180/api/history/title/Text%20with%20Spaces%2FSlashes
```
This will search for all songs containing `Text with Spaces/Slashes` in the title.

Quoted strings are not used in API calls since the syntax is not ambiguous anymore with URL Encoding.
E.g. use `)` when you want to close a subcommand, use `%29` when you want the closing bracket character.

## Command chaining
The command chaining works exactly like from the TeamSpeak chat, except ` ` (space) is replaced with `/` (forward slash) and `(!` is replaced with `(/`.

An example:
```
!history play (!rng 0 100)
// will become
http://localhost:8180/api/history/play/(/rng/0/100)
```

# Available API functions
The (almost) entire command list from the bot is also available from the web api.

For more information about a particular command please refer to the in your TSAudioBot integrated live api generator at `http://localhost:58913/openapi/index.html`.  
If you don't have a TSAudioBot running you can also go to [our openapi geneartor](https://tab.splamy.de/openapi/index.html).

# Authentication
We currently use [Basic Authentication](https://en.wikipedia.org/wiki/Basic_access_authentication) to authenticate calls.

## Get a Token
To get started write in teamspeak with the identity you want to get API access `!api token` to the bot. You will get something like that:
```
uA0U7t4PBxdJ5TLnarsOHQh4/tY=:RandomTokenABCDEFGHIJKLMONO
```
The string has two parts, separated by a colon:
- The first part is your ts3 public unique Id (you can also look it up under Tools>Identities>Unique ID), this will be your **username**.
- The second part is your **access token** (or sometimes just called 'token'). **Make sure to keep this part private**.

## Basic Authentication
It is highly recommended to reverse proxy the api behind an HTTPS connection with any service like nginx, apache, caddy, etc; or only work within localhost on the same server.

To authenticate simply set the HTTP authorization header on each call like that:
```
Authorization: Basic base64(<username>:<token>)
```
Example with `Base64EncodedPublicTs3Id=` as username and `RandomTokenABCDEFGHIJKLMONO` as token:
```
Authorization: Basic QmFzZTY0RW5jb2RlZFB1YmxpY1RzM0lkPTpSYW5kb21Ub2tlbkFCQ0RFRkdISUpLTE1PTk8=
```

# Tips 'n Tricks
## Json Merge
If you want to request multiple information in on request you can use the `!json merge` command. Example:
```json
http://localhost:8180/api/json/merge/(/loop)/(/repeat)/(/quiz)/(/random)/(/random/seed)
// Result:
[ { "Value": false },
  { "Value": false },
  { "Value": false },
  { "Value": true },
  { "Value": "aezalnb" } ]
```
will return an array of all subcommands which return an json object.

## AST Parser
To see how a command is parsed you can use `!parse` to get an abstract syntax tree (=AST).

## Examples

### PHP (Curl)

Change the bot name via php_curl:
```php
<?php
    $botid = "0";
    $newname = "NEW BOT NAME";
    $token = "TOKEN FROM !api token";
    $ch = curl_init();
    $token = str_replace(":ts3ab:", ":", token);
    $headers = array(
        'Content-Type:application/json',
        'Authorization: Basic '. base64_encode(token)
    );
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    $name = rawurlencode(newname);
    // the api call for '!bot use $botid (!xecute (!bot name $name) (!settings set connect.name $name))'
    curl_setopt($ch, CURLOPT_URL, "http://localhost:8180/api/bot/use/$botid/(/xecute/(/bot/name/$name)/(/settings/set/connect.name/$name))";
    curl_exec($ch);
    curl_close($ch);
?>
```

## Configuring your proxy
If you routed the TSAB webserver behind a reverse proxy and you want to use ip matcher  
make sure to forward the remote ip address in the `X-Real-IP` header.  
Examples for some proxies:
### nginx
To forward the header here use `proxy_set_header X-Real-IP $remote_addr;`.
```nginx
location / {
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_pass         http://127.0.0.1:58913/;
}
```

### caddy
To forward the header here use `transparent`.
```
my.domain.com {
    proxy / http://127.0.0.1:58913 {
        transparent
    }
}
```