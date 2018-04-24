# -*- coding: utf-8 -*-

# Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json
import threading
import time

from proxy.utils.constants import *
from proxy.utils.mcuuid import MCUUID


# noinspection PyMethodMayBeStatic
class ParseSB(object):
    """
    ParseSB parses server bound packets that are coming from the client.
    """
    def __init__(self, client, packet):
        self.client = client
        self.proxy = client.proxy
        self.log = client.log
        self.packet = packet
        self.pktSB = self.client.pktSB
        self.pktCB = self.client.pktCB

        self.command_prefix = self.proxy.srv_data.command_prefix
        self.command_prefix_non_standard = self.command_prefix != "/"

    def keep_alive(self):
        data = self.packet.readpkt(self.pktSB.KEEP_ALIVE[PARSER])

        if data[0] == self.client.keepalive_val:
            self.client.time_client_responded = time.time()
        return False

    def plugin_message(self):
        """server-bound"""
        channel = self.packet.readpkt([STRING, ])[0]

        if channel not in self.proxy.registered_channels:
            # we are not actually registering our channels with the MC server
            # and there will be no parsing of other channels.
            return True

        if channel == "MC|Brand":
            data = self.packet.readpkt([STRING])[0]
            self.log.debug(
                "(%s) client MC|Brand = %s", self.client.username, data
            )
            return True

        # SB PING
        if channel == "WRAPPER.PY|PING":
            # then we now know this wrapper is a child wrapper since
            # minecraft clients will not ping us
            self.client.info["client-is-wrapper"] = True
            self._plugin_poll_client_wrapper()

        # SB RESP
        elif channel == "WRAPPER.PY|RESP":
            # read some info the client wrapper sent
            # since we are only communicating with wrappers; we use the modern
            #  format:
            datarest = self.packet.readpkt([STRING, ])[0]
            response = json.loads(datarest, encoding='utf-8')
            if self._plugin_response(response):
                pass  # for now...

        # do not pass Wrapper.py registered plugin messages
        return False

    def _plugin_response(self, response):
        """
        Process the WRAPPER.PY|RESP plugin response packet
        """
        if "ip" in response:
            self.client.info["username"] = response["username"]
            self.client.info["realuuid"] = MCUUID(response["realuuid"]).string
            self.client.info["ip"] = response["ip"]

            self.client.ip = response["ip"]
            if response["realuuid"] != "":
                self.client.mojanguuid = MCUUID(response["realuuid"])
            self.client.username = response["username"]
            return True
        else:
            self.log.debug(
                "some kind of error with _plugin_response - no 'ip' key"
            )
            return False

    def _plugin_poll_client_wrapper(self):
        """
        CB PONG
        Send this wrapper client's self.info to another wrapper that
        PINGed this wrapper.
        """
        channel = "WRAPPER.PY|PONG"
        data = json.dumps(self.client.info)
        # only our wrappers communicate with this, so, format is not critical
        self.packet.sendpkt(self.pktCB.PLUGIN_MESSAGE[PKT], [STRING, STRING],
                            (channel, data))

    def play_player_poslook(self):  # player position and look
        """decided to use this one solely for tracking the client position"""

        # DOUBLE, DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BOOL - 1.7 - 1.7.10
        # ("double:x|double:feety|double:heady|double:z|float:yaw|float:pitch|bool:on_ground")

        # DOUBLE, DOUBLE, DOUBLE, FLOAT, FLOAT, BOOL - 1.8 and up
        # ("double:x|double:feety|double:z|float:yaw|float:pitch|bool:on_ground")
        if not self.client.local:
            return True
        data = self.packet.readpkt(self.pktSB.PLAYER_POSLOOK[PARSER])
        if self.client.clientversion > PROTOCOL_1_8START:
            self.client.position = (data[0], data[1], data[2])
            self.client.head = (data[3], data[4])
        else:
            self.client.position = (data[0], data[1], data[3])
            self.client.head = (data[4], data[5])
        return True

    def play_chat_message(self):
        data = self.packet.readpkt([STRING])
        if data is None:
            return False

        # Get the packet chat message contents
        chatmsg = data[0]

        if chatmsg[:4] == "/hub":
            if len(chatmsg) == 4:
                goto = ""
                if not self.client.local or self.client.info["client-is-wrapper"]:  # noqa
                    self._world_hub_command(goto)
                    return False
            else:
                if self.client.usehub:
                    arg = chatmsg.split()
                    # the command may have been something else like "/hubbify"..
                    if arg[0] == "/hub" and len(arg) > 1:
                        goto = arg[1]
                        self._world_hub_command(goto)
                        return False

        if not self.client.local:
            return True

        try:
            player = self.client.srv_data.players[self.client.username]
        except KeyError:
            return False
        payload = self.proxy.eventhandler.callevent("player.rawMessage", {
            "playername": self.client.username,
            "player": player,
            "message": chatmsg
        })
        """ eventdoc
            <group> Proxy <group>

            <description> Raw message from client to server.
            Contains the "/", if present.
            <description>

            <abortable> Yes <abortable>

            <comments>
            Can be aborted by returning False. Can be modified before
            passing to server.  'chatmsg' accepts both raw string
            or a dictionary payload containing ["message"] item.
            <comments>
            <payload>
            "player": player object
            "playername": player's name
            "message": the chat message string.
            <payload>

        """

        # This part allows the player plugin event "player.rawMessage" to...
        if payload is False:
            return False  # ..reject the packet (by returning False)

        # This is here for compatibility.  older plugins
        #  may attempt to send a string back
        if type(payload) == str:  # or, if it can return a substitute payload
            chatmsg = payload

        # Newer plugins return a modified version of the original
        # payload (i.e., a dictionary).

        # or, if it can return a substitute payload
        if type(payload) == dict and "message" in payload:
            chatmsg = payload["message"]

        # determine if this is a command. act appropriately
        if chatmsg[0] == self.command_prefix:
            # it IS a command of some kind
            allwords = chatmsg.split(" ")
            self.proxy.eventhandler.callevent(
                "player.runCommand", {
                    "playername":
                        self.client.username,
                    "player":
                        self.client.srv_data.players[self.client.username],
                    "command":
                        allwords[0][1:],
                    "args":
                        allwords[1:]
                }, abortable=False
            )

            # wrapper processed this command.. it goes no further
            """ eventdoc
                <group> Proxy <group>

                <description> internalfunction <description>

                <abortable> 
                No. Proxy - all commands are automatically aborted and re-handled by Wrapper.
                <abortable>

                <comments>
                 When a player runs a command. Do not use
                for registering commands.  There is not real good use-case 
                for a plugin developer to use this event.  Registering
                your own commands will do the same job.  You could use this 
                to overrided a minecraft command with your own... but again,
                registering an identical command will do the same thing.
                
                Called AFTER player.rawMessage event (if rawMessage
                does not reject it).  However, rawMessage could have
                modified it before this point. rawMessage is better if you 
                need to, for example, parse or filter chat.
                <comments>

                <payload>
                "player": playerobject()
                "playername": player's name
                "command": slash command (or whatever is set in wrapper's
                config as the command cursor).
                "args": the remaining words/args
                <payload>

            """  # noqa
            return False

        if chatmsg[0] == "/" and self.command_prefix_non_standard:
            # strip leading slash if using a non-slash command  prefix
            chatmsg = chatmsg[1:]

        # NOW we can send it (possibly modded) on to server...
        self.client.chat_to_server(chatmsg)
        return False  # and cancel this original packet

    def _world_hub_command(self, where=""):
        ip = "127.0.0.1"
        if where == "help":
            return self._world_hub_help("h")

        elif where == "worlds":
            return self._world_hub_help("w")

        elif where == "":
            port = self.proxy.srv_data.server_port

        else:
            worlds = self.proxy.proxy_worlds
            if where in worlds:
                port = self.proxy.proxy_worlds[where]["port"]
            else:
                return self._world_hub_help("w")
        t = threading.Thread(target=self.client.change_servers,
                             name="hub", args=(ip, port))
        t.daemon = True
        t.start()

    def _world_hub_help(self, htype):
        if htype == "h":
            self.client.chat_to_client(
                {
                    "text": "HUB System help", "color": "gold"
                }
            )
            self.client.chat_to_client(
                {
                    "text": "---------------------------", "color": "gold"
                }
            )
            self.client.chat_to_client(
                {
                    "text": "/hub - Return to the primary server.",
                    "color": "dark_green"
                }
            )
            self.client.chat_to_client(
                {
                    "text": "/hub <world_name> - Spawn in another world.",
                    "color": "dark_green"
                }
            )
            self.client.chat_to_client(
                {
                    "text": "/hub worlds - List available worlds.",
                    "color": "dark_green"
                }
            )
        elif htype == "w":
            self.client.chat_to_client(
                {
                    "text": "Available HUB worlds", "color": "gold"
                }
            )
            self.client.chat_to_client(
                {
                    "text": "---------------------------", "color": "gold"
                }
            )
            self.client.chat_to_client(
                {
                    "text": "/hub - back to the root server.", "color":
                    "dark_green"
                }
            )
            for places in self.proxy.proxy_worlds:
                self.client.chat_to_client(
                    {
                        "text": "/hub %s - Go to %s." % (
                            places,
                            self.proxy.proxy_worlds[places]["desc"]
                        ),
                        "color": "dark_green"
                    }
                )

    def play_player_position(self):
        """ hub needs accurate position """
        if self.client.clientversion < PROTOCOL_1_8START:
            data = self.packet.readpkt([DOUBLE, DOUBLE, DOUBLE, DOUBLE, BOOL])
            # ("double:x|double:y|double:yhead|double:z|bool:on_ground")
        elif self.client.clientversion >= PROTOCOL_1_8START:
            data = self.packet.readpkt([DOUBLE, DOUBLE, NULL, DOUBLE, BOOL])
            # ("double:x|double:y|double:z|bool:on_ground")
        else:
            data = [0, 0, 0, 0]
        # skip 1.7.10 and lower protocol yhead args
        self.client.position = (data[0], data[1], data[3])
        return True

    def play_player_look(self):
        """ hub needs accurate position """
        data = self.packet.readpkt([FLOAT, FLOAT, BOOL])
        # ("float:yaw|float:pitch|bool:on_ground")
        self.client.head = (data[0], data[1])
        return True

    def play_player_digging(self):
        if not self.client.local:
            return True
        data = self.packet.readpkt(self.pktSB.PLAYER_DIGGING[PARSER])
        if self.client.clientversion < PROTOCOL_1_8START:
            data = None
            position = (data[1], data[2], data[3])
        else:
            position = data[1]

        try:
            player = self.client.srv_data.players[self.client.username]
        except KeyError:
            return False
        # finished digging
        if data[0] == 2:
            print("CALL FINISH DIGGING", time.time())
            if not self.proxy.eventhandler.callevent("player.dig", {
                "playername": self.client.username,
                "player": player,
                "position": position,
                "action": "end_break",
                "face": data[4]
            }):
                return False  # stop packet if  player.dig returns False
            print("DIG FINISHED", time.time())
            """ eventdoc
                        <group> Proxy <group>

                        <description> When a player attempts to dig.  This event
                        only supports starting and finishing a dig.
                        <description>

                        <abortable> Yes <abortable>

                        <comments>
                        Can be aborted by returning False. Note that the client
                        may still believe the block is broken (or being broken).
                        If you intend to abort the dig, it should be done at
                        "begin_break". Sending a false bedrock to the client's 
                        digging position will help prevent the client from 
                        sending "end_break"
                        
                        <comments>

                        <payload>
                        "playername": player's name
                        "player": player object
                        "position": x, y, z block position
                        "action": begin_break or end_break (string)
                        "face": 0-5 (bottom, top, north, south, west, east)
                        <payload>

                    """
        # started digging
        if data[0] == 0:
            if self.client.gamemode != 1:
                if not self.proxy.eventhandler.callevent("player.dig", {
                    "playername": self.client.username,
                    "player": self.client.srv_data.players[
                        self.client.username],
                    "position": position,
                    "action": "begin_break",
                    "face": data[4]
                }):
                    return False
            else:
                if not self.proxy.eventhandler.callevent("player.dig", {
                    "playername": self.client.username,
                    "player": self.client.srv_data.players[
                        self.client.username],
                    "position": position,
                    "action": "end_break",
                    "face": data[4]
                }):
                    return False
        if data[0] == 5:  # and position == (0, 0, 0):
            playerpos = self.client.position
            if not self.proxy.eventhandler.callevent("player.interact", {
                "playername": self.client.username,
                "player": player,
                "position": playerpos,
                "action": "finish_using",
                "hand": 0,  # hand = 0 ( main hand)
                "origin": "pktSB.PLAYER_DIGGING"
            }):
                return False
            """ eventdoc
                <group> Proxy <group>

                <description> Called when the client is eating food, 
                pulling back bows, using buckets, etc.
                <description>

                <abortable> Yes <abortable>

                <comments>
                Can be aborted by returning False. Note that the client
                may still believe the action happened, but the server
                will act as though the event did not happen.  This 
                could be confusing to a player.  If the event is aborted, 
                consider some feedback to the client (a message, fake 
                particles, etc.)
                <comments>

                <payload>
                "playername": player's name
                "player": player object
                "position":  the PLAYERS position - x, y, z, pitch, yaw
                "action": "finish_using"  or "use_item"
                "hand": 0 = main hand, 1 = off hand (shield).
                "origin": Debugging information on where event was parsed.
                 Either 'pktSB.PLAYER_DIGGING' or 'pktSB.USE_ITEM'
                <payload>

            """
        print("DIG RETURNS TRUE", time.time())
        return True

    def play_player_block_placement(self):
        if not self.client.local:
            return True
        hand = 0  # main hand
        helditem = self.client.inventory[36 + self.client.slot]

        if self.client.clientversion < PROTOCOL_1_7:
            data = None
            position = data

        elif PROTOCOL_1_7 <= self.client.clientversion < PROTOCOL_1_8START:
            data = self.packet.readpkt(
                [INT, UBYTE, INT, BYTE, SLOT_NO_NBT, REST])
            # "int:x|ubyte:y|int:z|byte:face|slot:item")
            #  REST includes cursor positions x-y-z
            position = (data[0], data[1], data[2])

            # just FYI, notchian servers have been ignoring this field ("item")
            # for a long time, using server inventory instead.
            helditem = data[4]  # "item" - SLOT

        elif PROTOCOL_1_8START <= self.client.clientversion < PROTOCOL_1_9REL1:
            data = self.packet.readpkt(
                [POSITION, NULL, NULL, BYTE, SLOT, REST])
            # "position:Location|byte:face|slot:item|byte:CurPosX|
            #     byte:CurPosY|byte:CurPosZ")
            # helditem = data["item"]  -available in packet, but server
            # ignores it (we should too)!
            # starting with 1.8, the server maintains inventory also.
            position = data[0]

        else:  # self.clientversion >= PROTOCOL_1_9REL1:
            data = self.packet.readpkt(
                [POSITION, NULL, NULL, VARINT, VARINT, BYTE, BYTE, BYTE])
            # "position:Location|varint:face|varint:hand|byte:CurPosX|
            #     byte:CurPosY|byte:CurPosZ")
            hand = data[4]  # used to be the spot occupied by "slot"
            position = data[0]

        # Face and Position exist in all version protocols at this point
        clickposition = position
        face = data[3]
        self.client.lastplacecoords = position, time.time()

        if face == 0:  # Compensate for block placement coordinates
            position = (position[0], position[1] - 1, position[2])
        elif face == 1:
            position = (position[0], position[1] + 1, position[2])
        elif face == 2:
            position = (position[0], position[1], position[2] - 1)
        elif face == 3:
            position = (position[0], position[1], position[2] + 1)
        elif face == 4:
            position = (position[0] - 1, position[1], position[2])
        elif face == 5:
            position = (position[0] + 1, position[1], position[2])

        try:
            player = self.client.srv_data.players[self.client.username]
        except KeyError:
            return False

        # block placement event
        # position is where new block goes
        # clickposition is the block actually clicked
        if not self.proxy.eventhandler.callevent(
                "player.place",
                {"playername": self.client.username,
                 "player": player,
                 "position": position,
                 "clickposition": clickposition,
                 "hand": hand, "item": helditem}):
            """ eventdoc
                <group> Proxy <group>

                <description> Called when the client places an item
                <description>

                <abortable> Yes <abortable>

                <comments>
                Can be aborted by returning False. Note that the client
                may still believe the action happened, but the server
                will act as though the event did not happen.  This 
                could be confusing to a player.  If the event is aborted, 
                consider some feedback to the client (a message, fake 
                block, etc.)
                <comments>

                <payload>
                "playername": player's name
                "player": player object
                "position":  the clicked position, corrected for 'face' (i.e., 
                 the adjoining block position)
                "clickposition": The position of the block that was actually
                 clicked
                "item": The item player is holding (item['id'] = -1 if no item)
                "hand": hand in use (0 or 1)
                <payload>

            """
            return False
        return True

    def play_use_item(self):  # no 1.8 or prior packet
        """intercept things like lava and water bukkit placement"""
        if not self.client.local:
            return True
        data = self.packet.readpkt([VARINT])[0]
        position = self.client.position
        et = time.time() - self.client.lastplacecoords[1]
        # the time frame for this is to ensure coords are still relavant.
        if et < .5:
            position = self.client.lastplacecoords[0]

        try:
            player = self.client.srv_data.players[self.client.username]
        except KeyError:
            return False
        if not self.proxy.eventhandler.callevent("player.interact", {
            "playername": self.client.username,
            "player": player,
            "position": position,
            "action": "use_item",
            "hand": data,
            "origin": "pktSB.USE_ITEM"
        }):
            return False
        return True

    def play_held_item_change(self):
        if not self.client.local:
            return True
        slot = self.packet.readpkt([SHORT])
        if 9 > slot[0] > -1:
            self.client.slot = slot[0]
        else:
            self.log.debug("held item change returned False (SB)")
            return False
        return True

    def play_player_update_sign(self):
        if not self.client.local:
            return True
        if self.client.clientversion < PROTOCOL_1_8START:
            data = self.packet.readpkt(
                [INT, SHORT, INT, STRING, STRING, STRING, STRING])
            # "int:x|short:y|int:z|string:line1|string:line2|string:line3|
            #   string:line4")
            position = (data[0], data[1], data[2])
            pre_18 = True
        else:
            data = self.packet.readpkt(
                [POSITION, NULL, NULL, STRING, STRING, STRING, STRING])
            # "position:position|string:line1|string:line2|string:line3|
            #   string:line4")
            position = data[0]
            pre_18 = False

        l1 = data[3]
        l2 = data[4]
        l3 = data[5]
        l4 = data[6]

        try:
            player = self.client.srv_data.players[self.client.username]
        except KeyError:
            return False
        payload = self.proxy.eventhandler.callevent("player.createSign", {
            "playername": self.client.username,
            "player": player,
            "position": position,
            "line1": l1,
            "line2": l2,
            "line3": l3,
            "line4": l4
        })

        # plugin can reject sign entirely
        if not payload:
            return False

        # send back edits
        if type(payload) == dict:
            if "line1" in payload:
                l1 = payload["line1"]
            if "line2" in payload:
                l2 = payload["line2"]
            if "line3" in payload:
                l3 = payload["line3"]
            if "line4" in payload:
                l4 = payload["line4"]
        """ eventdoc
            <group> Proxy <group>

            <description> When a player creates a sign and finishes editing it
            <description>

            <abortable> Yes <abortable>

            <comments>
            Can be aborted by returning False.
            Any of the four line arguments can be changed by
            returning a dictionary payload containing the lines 
            you want replaced:    
            
            `return {"line2": "You can't write", "line3": "that!"}`
            <comments>

            <payload>
            "player": player object
            "playername": player's name
            "position": position of sign
            "line1": l1
            "line2": l2
            "line3": l3
            "line4": l4
            <payload>

        """
        self.client.editsign(position, l1, l2, l3, l4, pre_18)
        return False

    def play_client_settings(self):  # read Client Settings
        """
        This is read for later sending to servers we connect to
        """
        if not self.client.local:
            return True

        self.client.clientSettings = self.packet.readpkt([RAW])[0]
        # the packet is not stopped, sooo...
        return True

    def play_click_window(self):  # click window
        if not self.client.local:
            return True
        if self.client.clientversion < PROTOCOL_1_8START:
            data = self.packet.readpkt(
                [BYTE, SHORT, BYTE, SHORT, BYTE, SLOT_NO_NBT])
            # ("byte:wid|short:slot|byte:button|short:action|byte:mode|
            #   slot:clicked")
        elif PROTOCOL_1_8START < self.client.clientversion < PROTOCOL_1_9START:
            data = self.packet.readpkt(
                [UBYTE, SHORT, BYTE, SHORT, BYTE, SLOT])
            # ("ubyte:wid|short:slot|byte:button|short:action|byte:mode|
            #   slot:clicked")
        elif PROTOCOL_1_9START <= self.client.clientversion < PROTOCOL_MAX:
            data = self.packet.readpkt(
                [UBYTE, SHORT, BYTE, SHORT, VARINT, SLOT])
            # ("ubyte:wid|short:slot|byte:button|short:action|varint:mode|
            #   slot:clicked")
        else:
            data = [False, 0, 0, 0, 0, 0, 0]

        try:
            player = self.client.srv_data.players[self.client.username]
        except KeyError:
            return False
        datadict = {
            "playername": self.client.username,
            "player": player,
            "wid": data[0],  # window id ... always 0 for inventory
            "slot": data[1],  # slot number
            "button": data[2],  # mouse / key button
            "action": data[3],  # unique action id - incrementing counter
            "mode": data[4],
            "clicked": data[5]  # item data
        }
        if data[5] == {"id": -1}:
            data[5] = None
        if not self.proxy.eventhandler.callevent("player.slotClick", datadict):
            return False
        """ eventdoc
            <group> Proxy <group>

            <description> When a player clicks a window slot
            <description>

            <abortable> Yes <abortable>

            <comments>
            Can be aborted by returning False. Aborting is not recommended
            since that is how wrapper keeps tabs on inventory.
            <comments>

            <payload>
            "player": Player object
            "playername": the player's name
            "wid": window id ... always 0 for inventory
            "slot": slot number
            "button": mouse / key button
            "action": unique action id - incrementing counter
            "mode": varint:mode - see the wiki?
            "clicked": item data
            <payload>

        """
        # for inventory control, the most straightforward way to update
        # wrapper's inventory is to use the data from each click.  The
        # server will make other updates and corrections via SET_SLOT

        # yes, this probably breaks for double clicks that send the item
        # to who-can-guess what slot. We can fix that in a future update...
        # this gets us 98% fixed (versus 50% before) another source of
        # breakage is if lagging causes server to deny the changes.  Our
        # code does not check if the server accepted these changes with
        # a CONFIRM_TRANSACTION.

        # window 0 (inventory) and right or left click
        if data[0] == 0 and data[2] in (0, 1):
            # player first clicks on an empty slot - mark empty.
            if self.client.lastitem is None and data[5] is None:
                self.client.inventory[data[1]] = {"id": -1}

            # player first clicks on a slot where there IS some data..
            if self.client.lastitem is None:
                # having clicked on it puts the slot into NONE
                # status (since it can now be moved).
                # So we set the current slot to empty/none
                self.client.inventory[data[1]] = {"id": -1}
                # ..and we cache the new slot data to see where it goes
                self.client.lastitem = data[5]
                return True

            # up to this point, there was not previous item
            if self.client.lastitem is not None and data[5] is None:
                # now we have a previous item to process

                # that previous item now goes into the new slot.
                self.client.inventory[data[1]] = self.client.lastitem
                # since the slot was empty, there is no newer item to cache.
                self.client.lastitem = None
                return True

            if self.client.lastitem is not None and data[5] is not None:
                # our last item now occupies the space clicked and the new
                # item becomes the cached item.

                # set the cached item into the clicked slot.
                self.client.inventory[data[1]] = self.client.lastitem
                # put the item that was in the clicked slot into the cache now.
                self.client.lastitem = data[5]
                return True
        return True

    def play_spectate(self):
        if not self.client.local:
            return True
        # Spectate - convert packet to local server UUID

        # "Teleports the player to the given entity. The player must be in
        # spectator mode. The Notchian client only uses this to teleport to
        # players, but it appears to accept any type of entity. The entity
        # does not need to be in the same dimension as the player; if
        # necessary, the player will be respawned in the right world."

        """ Inter-dimensional player-to-player TP ! """  # TODO !

        # solves the uncertainty of dealing with what gets returned.
        data = self.packet.readpkt([UUID, NULL])

        # ("uuid:target_player")
        for client in self.proxy.clients:
            if data[0] == client.wrapper_uuid:
                self.client.server_connection.packet.sendpkt(
                    self.client.pktSB.SPECTATE[PKT],
                    [UUID],
                    [client.wrapper_uuid])
                self.log.debug("spectate returned False (SB)")
                return False
        return True
