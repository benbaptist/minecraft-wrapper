**< Group 'core/mcserver.py' >**

:Event: "player.login"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description:
        When player logs into the java MC server.

    :Payload:
        :"playername": player name

    :Can be aborted/modified: No
    :Comments:
        All events in the core/mcserver.py group are collected
        from the console output, do not require proxy mode, and
        therefore, also, cannot be aborted.

:Event: "player.logout"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: player.logout

    :Payload:
        :"player": self.getplayer(players_name)

    :Can be aborted/modified: 

:Event: "server.stopped"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.stopped

    :Payload:
        :"reason": reason

    :Can be aborted/modified: 

:Event: "server.starting"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.starting

    :Payload:
        :"reason": reason

    :Can be aborted/modified: 

:Event: "server.started"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.started

    :Payload:
        :"reason": reason

    :Can be aborted/modified: 

:Event: "server.stopping"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.stopping

    :Payload:
        :"reason": reason

    :Can be aborted/modified: 

:Event: "server.state"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.state

    :Payload:
        :"state": state
        :"reason": reason

    :Can be aborted/modified: 

:Event: "server.consoleMessage"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.consoleMessage

    :Payload:
        :"message": buff

    :Can be aborted/modified: 

:Event: "player.message"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description:
        Player chat scrubbed from the console.

    :Payload:
        :"player": playerobject
        :"message": <str> type - what the player said in chat. ('hello everyone')
        :"original": The original line of text from the console ('<mcplayer> hello everyone`)

    :Can be aborted/modified: 
    :Comments:
        This event is triggered by console chat which has already been sent.

:Event: "player.action"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: player.action

    :Payload:
        :"player": self.getplayer(name)
        :"action": message

    :Can be aborted/modified: 

:Event: "player.achievement"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: player.achievement

    :Payload:
        :"player": name
        :"achievement": achievement

    :Can be aborted/modified: 

:Event: "server.say"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.say

    :Payload:
        :"player": name
        :"message": message
        :"original": original

    :Can be aborted/modified: 

:Event: "player.death"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: player.death

    :Payload:
        :"player": self.getplayer(name)
        :"death": getargsafter(line_words
         1)

    :Can be aborted/modified: 

:Event: "server.lagged"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: server.lagged

    :Payload:
        :"ticks": get_int(skipping_ticks)

    :Can be aborted/modified: 

:Event: "player.teleport"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description:
        When player teleports.

    :Payload:
        :"player": player object

    :Can be aborted/modified: No
    :Comments:
        driven from console message "Teleported ___ to ....".

**< Group 'wrapper' >**

:Event: "timer.second"

    :Module: wrapper.py *(core/wrapper.py)*

    :Description:
        a timer that is called each second.

    :Payload: None

    :Can be aborted/modified: No

:Event: "timer.tick"

    :Module: wrapper.py *(core/wrapper.py)*

    :Description:
        a timer that is called each 1/20th
          of a second, like a minecraft tick.

    :Payload: None

    :Can be aborted/modified: No
    :Comments:
        Use of this timer is not suggested and is turned off
          by default in the wrapper.config.json file

**< Group 'core/irc.py' >**

:Event: "irc.join"

    :Module: irc.py *(core/irc.py)*

    :Description: irc.join

    :Payload:
        :"nick": nick
        :"channel": channel

    :Can be aborted/modified: 

:Event: "irc.part"

    :Module: irc.py *(core/irc.py)*

    :Description: irc.part

    :Payload:
        :"nick": nick
        :"channel": channel

    :Can be aborted/modified: 

:Event: "irc.quit"

    :Module: irc.py *(core/irc.py)*

    :Description: irc.quit

    :Payload:
        :"nick": nick
        :"message": message
        :"channel": None

    :Can be aborted/modified: 

:Event: "irc.action"

    :Module: irc.py *(core/irc.py)*

    :Description: irc.action

    :Payload:
        :"nick": nick
        :"channel": channel
        :"action": getargsafter(message.split(" ")
         1)[:-1]

    :Can be aborted/modified: 

:Event: "irc.message"

    :Module: irc.py *(core/irc.py)*

    :Description: irc.message

    :Payload:
        :"nick": nick
        :"channel": channel
        :"message": message

    :Can be aborted/modified: 

**< Group 'Proxy' >**

:Event: "player.preLogin"

    :Module: clientconnection.py *(client/clientconnection.py)*

    :Description:
        Called before client logs on.

    :Payload:
        :"playername": self.username,
        :"player": username (name only - player object does not yet exist)
        :"online_uuid": online UUID,
        :"offline_uuid": UUID on local server (offline),
        :"ip": the user/client IP on the internet.
        :"secure_connection": Proxy's online mode

    :Can be aborted/modified: Yes, return False to disconnect the client.
    :Comments:
        - If aborted, the client is disconnnected with message
        "Login denied by a Plugin."
        - Event occurs after proxy ban code runs right after a
        successful handshake with Proxy.

:Event: "player.rawMessage"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        Raw message from client to server.
        Contains the "/", if present.

    :Payload:
        :"player": player's name
        :"message": the chat message string.

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False. Can be modified before
        passing to server.  'chatmsg' accepts both raw string
        or a dictionary payload containing ["message"] item.

:Event: "player.runCommand"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        When a player runs a command. Do not use
        for registering commands.

    :Payload:
        :"player": playerobject()
        :"command": slash command (or whatever is set in wrapper's
         config as the command cursor).
        :"args": the remaining words/args

    :Can be aborted/modified: Yes. Registered commands ARE already aborted since they do not get passed to the server.
    :Comments:
        Called AFTER player.rawMessage event (if rawMessage
        does not reject it).  However, rawMessage could have
        modified it before this point.
        
        The best use of this event is a quick way to prevent a client from
        passing certain commands or command arguments to the server.
        rawMessage is better if you need something else (parsing or
        filtering chat, for example).

:Event: "player.dig"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        When a player attempts to dig.  This event
        only supports starting and finishing a dig.

    :Payload:
        :"playername": playername (not the player object!)
        :"position": x, y, z block position
        :"action": begin_break or end_break (string)
        :"face": 0-5 (bottom, top, north, south, west, east)

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False. Note that the client
        may still believe the block is broken (or being broken).
        If you intend to abort the dig, it should be done at
        "begin_break". Sending a false bedrock to the client's
        digging position will help prevent the client from
        sending "end_break"

:Event: "player.interact"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        Called when the client is eating food,
        pulling back bows, using buckets, etc.

    :Payload:
        :"playername": playername (not the player object!)
        :"position":  the PLAYERS position - x, y, z, pitch, yaw
        :"action": "finish_using"  or "use_item"
        :"origin": Debugging information on where event was parsed.

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False. Note that the client
        may still believe the action happened, but the server
        will act as though the event did not happen.  This
        could be confusing to a player.  If the event is aborted,
        consider some feedback to the client (a message, fake
        particles, etc.)

:Event: "player.place"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        Called when the client places an item

    :Payload:
        :"playername": playername (not the player object!)
        :"position":  the PLAYERS position - x, y, z, pitch, yaw
        :"action": "finish_using"  or "use_item"
        :"origin": Debugging information on where event was parsed.

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False. Note that the client
        may still believe the action happened, but the server
        will act as though the event did not happen.  This
        could be confusing to a player.  If the event is aborted,
        consider some feedback to the client (a message, fake
        block, etc.)

:Event: "player.createSign"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        When a player creates a sign and finishes editing it

    :Payload:
        :"player": player name
        :"position": position of sign
        :"line1": l1
        :"line2": l2
        :"line3": l3
        :"line4": l4

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False.
        Any of the four line arguments can be changed by
        returning a dictionary payload containing the lines
        you want replaced:
        
        `return {"line2": "You can't write", "line3": "that!"}`

:Event: "player.slotClick"

    :Module: parse_sb.py *(client/parse_sb.py)*

    :Description:
        When a player clicks a window slot

    :Payload:
        :"player": Players name (not the object!)
        :"wid": window id ... always 0 for inventory
        :"slot": slot number
        :"button": mouse / key button
        :"action": unique action id - incrementing counter
        :"mode": varint:mode - see the wiki?
        :"clicked": item data

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False. Aborting is not recommended
        since that is how wrapper keeps tabs on inventory.

:Event: "player.chatbox"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description:
        Chat message sent from the server to the client.

    :Payload:
        :"playername": client username
        :"json": json or string data

    :Can be aborted/modified: Yes
    :Comments:
        - The message will not reach the client if the event is returned False.
        - If json chat (dict) or text is returned, that value will be sent
        to the client instead.

:Event: "player.usebed"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description:
        Sent when server sends client to bedmode.

    :Payload:
        :"playername": client username
        :"position": position of bed

    :Can be aborted/modified: No - The server thinks the client is in bed already.

:Event: "player.spawned"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description:
        Sent when server advises the client of its spawn position.

    :Payload:
        :"playername": client username
        :"position": position

    :Can be aborted/modified: No - Notification only.

:Event: "entity.unmount"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description:
        Sent when player attaches to entity.

    :Payload:
        :"playername": client username
        :"vehicle_id": EID of vehicle or MOB
        :"leash": leash True/False

    :Can be aborted/modified: No - Notification only.
    :Comments:
        Only works if entity controls are enabled.  entity controls
        add significant load to wrapper's packet parsing and is off by default.

:Event: "entity.mount"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description:
        Sent when player detaches/unmounts entity.

    :Payload:
        :"playername": client username
        :"vehicle_id": EID of vehicle or MOB
        :"leash": leash True/False

    :Can be aborted/modified: No - Notification only.
    :Comments:
        Only works if entity controls are enabled.  entity controls
        add significant load to wrapper's packet parsing and is off by default.

**< Group 'Backups' >**

:Event: "wrapper.backupDelete"

    :Module: backups.py *(core/backups.py)*

    :Description:
        Called upon deletion of a backup file.

    :Payload:
        :"file": filename

    :Can be aborted/modified: Yes, return False to abort.

:Event: "wrapper.backupFailure"

    :Module: backups.py *(core/backups.py)*

    :Description:
        Indicates failure of backup.

    :Payload:
        :"reasonCode": an integer 1-4
        :"reasonText": a string description of the failure.

    :Can be aborted/modified: No - informatinal only
    :Comments:
        Reasoncode and text provide more detail about specific problem.
        1 - Tar not installed.
        2 - Backup file does not exist after the tar operation.
        3 - Specified file does not exist.
        4 - backups.json is corrupted

:Event: "wrapper.backupBegin"

    :Module: backups.py *(core/backups.py)*

    :Description:
        Indicates a backup is being initiated.

    :Payload:
        :"file": Name of backup file.

    :Can be aborted/modified: Yes, return False to abort.
    :Comments:
        A console warning will be issued if a plugin cancels the backup.

:Event: "wrapper.backupEnd"

    :Module: backups.py *(core/backups.py)*

    :Description:
        Indicates a backup is complete.

    :Payload:
        :"file": Name of backup file.

    :Can be aborted/modified: No - informational only

