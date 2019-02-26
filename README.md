# lurklite

luk3yx's "lightweight™" IRC bot (excluding commands).

## Config file

The lurklite config file has a format similar to `ini` files. It must have a
`[core]` section with the following values:

```ini
[core]
# The tempcmd db, commands added with .tempcmd are stored here.
# If you have msgpack installed, this database will be slightly smaller and
#   faster to read/write to/from.
tempcmd_db = /path/to/tempcmd/database

# The bot's command prefix.
prefix     = .

# (Optional) A list of hostmasks to ignore.
# ignored  = *!*@*/bot/*, baduser!*@*
```

### Connecting to IRC servers

You can then create sections starting with `irc.` (for example `irc.freenode`)
to connect to IRC servers:

```ini
[irc.freenode]
ip   = chat.freenode.net
port = 6697
nick = testbot
channels = #botwar,#other-channel

# List of hostmasks to ignore (optional)
# ignored = *!*@*/bot/*, *!*sopel*@*

# List of hostmasks for admins
# admins = *!*@unaffiliated/user
```

The following optional values may be added to the above config, and are sent
directly to [miniirc]:

```ini
connect_modes = +g
ident         = ident
ns_identity   = username password
quit_message  = Quit message
realname      = realname
ssl           = true
```

### Connecting to Discord servers

You can also connect to Discord servers (via [miniirc_discord]) with the
following config section:

```ini
[discord]
# You need miniirc_discord installed for this to work.
token    = your-discord-token

# admins = userid#1234
```

You can only have one Discord connection per bot process, and lurklite will use
slightly more RAM if `[discord]` exists, as [miniirc_discord] will be imported
(and if you don't specify a Discord bot token, [miniirc_discord] won't be
imported).

## Creating commands

Once your bot has connected to IRC (or Discord), you can use `tempcmd` to
create (permanent) commands. You can either do
`.tempcmd <command> <type> <code>` to add a tempcmd with a set type, or
`.tempcmd <command> <code>` to auto-detect the type (as long as the first word
in `<code>` is not a valid type).

*For now, tempcmds.py has a list of code types/formats and what they do.*

To delete commands, you can use `tempcmd del/delete/remove <command>`. To create
a command called `del`, `delete` or `remove`, you can prepend your bot's prefix
to the command name.

## Built-in commands

lurklite has the following built-in commands:

 - `reboot`: Reboot the bot.
 - `tempcmd`: Create and delete commands.
 - `version`: Display the miniirc version and quit.

## Migrating from older versions of lurklite

Older versions of lurklite had a `tempcmds.db` created using `repr()`. This is
slow(-ish), so is no longer supported. If you still have an old `tempcmds.db`,
you can run `tempcmds_migrate.py` to update it to the new msgpack/JSON format.

[miniirc]: https://github.com/luk3yx/miniirc
[miniirc_discord]: https://github.com/luk3yx/miniirc_discord
