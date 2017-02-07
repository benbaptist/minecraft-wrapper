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
         self.getplayer(players_name)

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

**< Group 'proxy/parse_cb.py' >**

:Event: "player.chatbox"

    :Module: parse_cb.py *(proxy/parse_cb.py)*

    :Description: player.chatbox

    :Payload:
        :"player": self.client.getplayerobject()
        :"json": data

    :Can be aborted/modified: 

:Event: "player.spawned"

    :Module: parse_cb.py *(proxy/parse_cb.py)*

    :Description: player.spawned

    :Payload:
        :"player": self.client.getplayerobject()
        :"position": data

    :Can be aborted/modified: 

:Event: "player.usebed"

    :Module: parse_cb.py *(proxy/parse_cb.py)*

    :Description: player.usebed

    :Payload:
        :"player": self.wrapper.javaserver.players[self.client.username]
        :"position": data[1]

    :Can be aborted/modified: 

:Event: "player.unmount"

    :Module: parse_cb.py *(proxy/parse_cb.py)*

    :Description: player.unmount

    :Payload:
        :"player": player
        :"vehicle_id": vehormobeid
        :"leash": leash

    :Can be aborted/modified: 

:Event: "player.mount"

    :Module: parse_cb.py *(proxy/parse_cb.py)*

    :Description: player.mount

    :Payload:
        :"player": player
        :"vehicle_id": vehormobeid
        :"leash": leash

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

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description:
        Raw message from client to server.
        Contains the "/", if present.

    :Payload:
        :"player": self.client.getplayerobject()
        :"message": chatmsg

    :Can be aborted/modified: Yes
    :Comments:
        Can be aborted by returning False. Can be modified before
        passing to server.  'chatmsg' accepts both raw string
        or a dictionary payload containing ["message"] item.

:Event: "player.runCommand"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

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

:Event: "player.createSign"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description:
        When a player creates a sign and finishes editing it

    :Payload:
        :"player": playerobject()
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

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description:
        When a player clicks a window slot

    :Payload:
        :"player": playerobject()
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

**< Group 'proxy/parse_sb.py' >**

:Event: "player.dig"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.dig

    :Payload:
        :"player": self.client.getplayerobject()
        :"position": position
        :"action": "end_break"
        :"face": data[4]

    :Can be aborted/modified: 

:Event: "player.dig"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.dig

    :Payload:
        :"player": self.client.getplayerobject()
        :"position": position
        :"action": "begin_break"
        :"face": data[4]

    :Can be aborted/modified: 

:Event: "player.dig"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.dig

    :Payload:
        :"player": self.client.getplayerobject()
        :"position": position
        :"action": "end_break"
        :"face": data[4]

    :Can be aborted/modified: 

:Event: "player.interact"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.interact

    :Payload:
        :"player": self.client.getplayerobject()
        :"position": playerpos
        :"action": "finish_using"

    :Can be aborted/modified: 

:Event: "player.interact"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.interact

    :Payload:
        :"player": player
        :"position": position
        :"action": "useitem"
        :"origin": "pktSB.PLAYER_BLOCK_PLACEMENT"

    :Can be aborted/modified: 

:Event: "player.place"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.place

    :Payload:
        :"player": player
        :"position": position
        :"clickposition": clickposition
        :"hand": hand
        :"item": helditem

    :Can be aborted/modified: 

:Event: "player.interact"

    :Module: parse_sb.py *(proxy/parse_sb.py)*

    :Description: player.interact

    :Payload:
        :"player": player
        :"position": position
        :"action": "useitem"
        :"origin": "pktSB.USE_ITEM"

    :Can be aborted/modified: 

**< Group 'proxy/clientconnection.py' >**

:Event: "player.preLogin"

    :Module: clientconnection.py *(proxy/clientconnection.py)*

    :Description: player.preLogin

    :Payload:
        :"player": self.username
        :"online_uuid": self.uuid.string
        :"offline_uuid": self.serveruuid.string
        :"ip": self.ip
        :"secure_connection": self.wrapper_onlinemode

    :Can be aborted/modified: 

