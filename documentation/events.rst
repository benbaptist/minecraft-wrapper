**< Group 'core/mcserver.py' >**

:Event: "player.login"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: player.login

    :Payload:
        :"player": self.getplayer(username)

    :Can be aborted/modified: 

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

    :Description: player.message

    :Payload:
        :"player": self.getplayer(name)
        :"message": message
        :"original": original

    :Can be aborted/modified: 

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

:Event: "proxy.console"

    :Module: mcserver.py *(core/mcserver.py)*

    :Description: proxy.console

    :Payload:
         #{"command": console_command

    :Can be aborted/modified: 

**< Group 'server/parse_cb.py' >**

:Event: "player.chatbox"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description: player.chatbox

    :Payload:
        :"playername": self.client.username
        :"json": data

    :Can be aborted/modified: 

:Event: "player.spawned"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description: player.spawned

    :Payload:
        :"playername": self.client.username
        :"position": data

    :Can be aborted/modified: 

:Event: "player.usebed"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description: player.usebed

    :Payload:
        :"playername": self.client.username
        :"position": data[1]

    :Can be aborted/modified: 

:Event: "entity.unmount"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description: entity.unmount

    :Payload:
        :"playername": self.client.username
        :"vehicle_id": vehormobeid
        :"leash": leash

    :Can be aborted/modified: 

:Event: "entity.mount"

    :Module: parse_cb.py *(server/parse_cb.py)*

    :Description: entity.mount

    :Payload:
        :"playername": self.client.username
        :"vehicle_id": vehormobeid
        :"leash": leash

    :Can be aborted/modified: 

**< Group 'core/backups.py' >**

:Event: "wrapper.backupDelete"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupDelete

    :Payload:
        :"file": filename

    :Can be aborted/modified: 

:Event: "wrapper.backupFailure"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupFailure

    :Payload:
        :"reasonCode": 1
        :"reasonText": "Tarisnotinstalled.Pleaseinstall""tarbeforetryingtomakebackups."

    :Can be aborted/modified: 

:Event: "wrapper.backupBegin"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupBegin

    :Payload:
        :"file": filename

    :Can be aborted/modified: 

:Event: "wrapper.backupFailure"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupFailure

    :Payload:
        :"reasonCode": 3
        :"reasonText": "Backupfile'%s'doesnotexist."%backup_file_and_path

    :Can be aborted/modified: 

:Event: "wrapper.backupEnd"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupEnd

    :Payload:
        :"file": filename
        :"status": statuscode

    :Can be aborted/modified: 

:Event: "wrapper.backupFailure"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupFailure

    :Payload:
        :"reasonCode": 2
        :"reasonText": "Backupfiledidn'texistafterthetar""commandexecuted-assumingfailure."

    :Can be aborted/modified: 

:Event: "wrapper.backupFailure"

    :Module: backups.py *(core/backups.py)*

    :Description: wrapper.backupFailure

    :Payload:
        :"reasonCode": 4
        :"reasonText": "backups.jsoniscorrupted.Pleasecontactanadministerinstantly
         asthis""maybecritical."

    :Can be aborted/modified: 

**< Group 'entity/entitycontrol.py' >**

:Event: "proxy.console"

    :Module: entitycontrol.py *(entity/entitycontrol.py)*

    :Description: proxy.console

    :Payload:
        :"command": console_command

    :Can be aborted/modified: 

:Event: "proxy.console"

    :Module: entitycontrol.py *(entity/entitycontrol.py)*

    :Description: proxy.console

    :Payload:
        :"command": console_command

    :Can be aborted/modified: 

**< Group 'proxy/base.py' >**

:Event: "proxy.console"

    :Module: base.py *(proxy/base.py)*

    :Description: proxy.console

    :Payload:
        :"command": console_command

    :Can be aborted/modified: 

:Event: "proxy.console"

    :Module: base.py *(proxy/base.py)*

    :Description: proxy.console

    :Payload:
        :"command": console_command

    :Can be aborted/modified: 

:Event: "proxy.console"

    :Module: base.py *(proxy/base.py)*

    :Description: proxy.console

    :Payload:
        :"command": console_command

    :Can be aborted/modified: 

**< Group 'api/base.py' >**

:Event: "event"

    :Module: base.py *(api/base.py)*

    :Description: event

    :Payload:
         payload

    :Can be aborted/modified: 

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

**< Group 'client/clientconnection.py' >**

:Event: "player.preLogin"

    :Module: clientconnection.py *(client/clientconnection.py)*

    :Description: player.preLogin

    :Payload:
        :"playername": self.username
        :"player": self.username
         #notarealplayerobject!"online_uuid": self.uuid.string
        :"offline_uuid": self.serveruuid.string
        :"ip": self.ip
        :"secure_connection": self.onlinemode

    :Can be aborted/modified: 

:Event: "proxy.console"

    :Module: clientconnection.py *(client/clientconnection.py)*

    :Description: proxy.console

    :Payload:
        :"command": "whitelistreload"

    :Can be aborted/modified: 

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

    :Can be aborted/modified: Registered commands ARE aborted...
    :Comments:
        Called AFTER player.rawMessage event if rawMessage
        does not reject it.  However, rawMessage could have
        modified it before this point.

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
        returning a dictionary payload containing "lineX":
        "what you want"

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

