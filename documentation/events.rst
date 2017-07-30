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

