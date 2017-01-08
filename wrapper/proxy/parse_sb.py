# -*- coding: utf-8 -*-

# Copyright (C) 2017 - BenBaptist and minecraft-wrapper (AKA 'Wrapper.py')
#  developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU General Public License,
#  version 3 or later.

from proxy import mcpackets
# noinspection PyPep8Naming
from utils import pkt_datatypes as D


# noinspection PyMethodMayBeStatic
class ParseSB:
    """
    ParseSB parses server bound packets that are coming from the client.
    """
    def __init__(self, client, packet):
        self.client = client
        self.proxy = client.proxy
        self.wrapper = client.proxy.wrapper
        self.log = client.proxy.wrapper.log
        self.config = client.proxy.wrapper.config
        self.packet = packet

        self.command_prefix = self.wrapper.command_prefix
        self.command_prefix_non_standard = self.command_prefix != "/"
        self.command_prefix_len = len(self.command_prefix)

    def parse_play_player_poslook(self):  # player position and look
        if self.client.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.DOUBLE, D.FLOAT, D.FLOAT, D.BOOL])
        else:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.FLOAT, D.FLOAT, D.BOOL])
        # ("double:x|double:y|double:z|float:yaw|float:pitch|bool:on_ground")
        self.client.position = (data[0], data[1], data[4])
        self.client.head = (data[4], data[5])
        return True

    def parse_play_chat_message(self):
        data = self.packet.readpkt([D.STRING])
        if data is None:
            return False

        # Get the packet chat message contents
        chatmsg = data[0]

        payload = self.wrapper.events.callevent("player.rawMessage", {
            "player": self.client.getplayerobject(),
            "message": chatmsg
        })

        # This part allows the player plugin event "player.rawMessage" to...
        if payload is False:
            return False  # ..reject the packet (by returning False)

        # This is here for compatibility.  older plugins may attempt to send a string back
        if type(payload) == str:  # or, if it can return a substitute payload
            chatmsg = payload

        # Newer plugins return a modified version of the original payload (i.e., a dictionary).
        if type(payload) == dict and "message" in payload:  # or, if it can return a substitute payload
            chatmsg = payload["message"]

        # determine if this is a command. act appropriately
        if chatmsg[0:self.command_prefix_len] == self.command_prefix:  # it IS a command of some kind
            if self.wrapper.events.callevent(
                    "player.runCommand", {
                        "player": self.client.getplayerobject(),
                        "command": chatmsg.split(" ")[0][1:].lower(),
                        "args": chatmsg.split(" ")[1:]}):

                return False  # wrapper processed this command.. it goes no further

        if chatmsg[0] == "/" and self.command_prefix_non_standard:
            chatmsg = chatmsg[1:]  # strip out any leading slash if using a non-slash command  prefix

        # NOW we can send it (possibly modded) on to server...
        self.client.chat_to_server(chatmsg)
        return False  # and cancel this original packet

    def parse_play_player_position(self):
        if self.client.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.DOUBLE, D.DOUBLE, D.BOOL])
            # ("double:x|double:y|double:yhead|double:z|bool:on_ground")
        elif self.client.clientversion >= mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.DOUBLE, D.DOUBLE, D.NULL, D.DOUBLE, D.BOOL])
            # ("double:x|double:y|double:z|bool:on_ground")
        else:
            data = [0, 0, 0, 0]
        self.client.position = (data[0], data[1], data[3])  # skip 1.7.10 and lower protocol yhead args
        return True

    def parse_play_teleport_confirm(self):
        # don't interfere with this and self.pktSB.PLAYER_POSLOOK... doing so will glitch the client
        # data = self.packet.readpkt([D.VARINT])
        return True

    def parse_play_player_look(self):
        data = self.packet.readpkt([D.FLOAT, D.FLOAT, D.BOOL])
        # ("float:yaw|float:pitch|bool:on_ground")
        self.client.head = (data[0], data[1])
        return True

    def parse_play_player_digging(self):
        if self.client.clientversion < mcpackets.PROTOCOL_1_7:
            data = None
            position = data
        elif mcpackets.PROTOCOL_1_7 <= self.client.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.BYTE, D.INT, D.UBYTE, D.INT, D.BYTE])
            # "byte:status|int:x|ubyte:y|int:z|byte:face")
            position = (data[1], data[2], data[3])
        else:
            data = self.packet.readpkt([D.BYTE, D.POSITION, D.NULL, D.NULL, D.BYTE])
            # "byte:status|position:position|byte:face")
            position = data[1]

        if data is None:
            return True

        # finished digging
        if data[0] == 2:
            if not self.wrapper.events.callevent("player.dig", {
                "player": self.client.getplayerobject(),
                "position": position,
                "action": "end_break",
                "face": data[4]
            }):
                return False  # stop packet if  player.dig returns False

        # started digging
        if data[0] == 0:
            if self.client.gamemode != 1:
                if not self.wrapper.events.callevent("player.dig", {
                    "player": self.client.getplayerobject(),
                    "position": position,
                    "action": "begin_break",
                    "face": data[4]
                }):
                    return False
            else:
                if not self.wrapper.events.callevent("player.dig", {
                    "player": self.client.getplayerobject(),
                    "position": position,
                    "action": "end_break",
                    "face": data[4]
                }):
                    return False
        if data[0] == 5 and data[4] == 255:
            if self.client.position != (0, 0, 0):
                playerpos = self.client.position
                if not self.wrapper.events.callevent("player.interact", {
                    "player": self.client.getplayerobject(),
                    "position": playerpos,
                    "action": "finish_using"
                }):
                    return False
        return True

    def parse_play_player_block_placement(self):
        player = self.client.getplayerobject()
        hand = 0  # main hand
        helditem = player.getHeldItem()

        if self.client.clientversion < mcpackets.PROTOCOL_1_7:
            data = None
            position = data

        elif mcpackets.PROTOCOL_1_7 <= self.client.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.INT, D.UBYTE, D.INT, D.BYTE, D.SLOT_NO_NBT, D.REST])
            # "int:x|ubyte:y|int:z|byte:face|slot:item")  D.REST includes cursor positions x-y-z
            position = (data[0], data[1], data[2])

            # just FYI, notchian servers have been ignoring this field ("item")
            # for a long time, using server inventory instead.
            helditem = data[4]  # "item" - D.SLOT

        elif mcpackets.PROTOCOL_1_8START <= self.client.clientversion < mcpackets.PROTOCOL_1_9REL1:
            data = self.packet.readpkt([D.POSITION, D.NULL, D.NULL, D.BYTE, D.SLOT, D.REST])
            # "position:Location|byte:face|slot:item|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
            # helditem = data["item"]  -available in packet, but server ignores it (we should too)!
            # starting with 1.8, the server maintains inventory also.
            position = data[0]

        else:  # self.clientversion >= mcpackets.PROTOCOL_1_9REL1:
            data = self.packet.readpkt([D.POSITION, D.NULL, D.NULL, D.VARINT, D.VARINT, D.BYTE, D.BYTE, D.BYTE])
            # "position:Location|varint:face|varint:hand|byte:CurPosX|byte:CurPosY|byte:CurPosZ")
            hand = data[4]  # used to be the spot occupied by "slot"
            position = data[0]

        # Face and Position exist in all version protocols at this point
        clickposition = position
        face = data[3]

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

        if helditem is None:
            # if no item, treat as interaction (according to wrappers
            # inventory :(, return False  )
            if not self.wrapper.events.callevent("player.interact", {
                "player": player,
                "position": position,
                "action": "useitem",
                "origin": "pktSB.PLAYER_BLOCK_PLACEMENT"
            }):
                return False

        # block placement event
        self.client.lastplacecoords = position
        if not self.wrapper.events.callevent("player.place", {"player": player,
                                                              "position": position,  # where new block goes
                                                              "clickposition": clickposition,  # block clicked
                                                              "hand": hand,
                                                              "item": helditem}):
            return False
        return True

    def parse_play_use_item(self):  # no 1.8 or prior packet
        data = self.packet.readpkt([D.REST])
        # "rest:pack")
        player = self.client.getplayerobject()
        position = self.client.lastplacecoords
        if "pack" in data:
            if data[0] == '\x00':
                if not self.wrapper.events.callevent("player.interact", {
                    "player": player,
                    "position": position,
                    "action": "useitem",
                    "origin": "pktSB.USE_ITEM"
                }):
                    return False
        return True

    def parse_play_held_item_change(self):
        slot = self.packet.readpkt([D.SHORT])
        # "short:short")  # ["short"]
        if 9 > slot[0] > -1:
            self.client.slot = slot[0]
        else:
            return False
        return True

    def parse_play_player_update_sign(self):
        if self.client.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.INT, D.SHORT, D.INT, D.STRING, D.STRING, D.STRING, D.STRING])
            # "int:x|short:y|int:z|string:line1|string:line2|string:line3|string:line4")
            position = (data[0], data[1], data[2])
            pre_18 = True
        else:
            data = self.packet.readpkt([D.POSITION, D.NULL, D.NULL, D.STRING, D.STRING, D.STRING, D.STRING])
            # "position:position|string:line1|string:line2|string:line3|string:line4")
            position = data[0]
            pre_18 = False

        l1 = data[3]
        l2 = data[4]
        l3 = data[5]
        l4 = data[6]
        payload = self.wrapper.events.callevent("player.createsign", {
            "player": self.client.getplayerobject(),
            "position": position,
            "line1": l1,
            "line2": l2,
            "line3": l3,
            "line4": l4
        })
        if not payload:  # plugin can reject sign entirely
            return False

        if type(payload) == dict:  # send back edits
            if "line1" in payload:
                l1 = payload["line1"]
            if "line2" in payload:
                l2 = payload["line2"]
            if "line3" in payload:
                l3 = payload["line3"]
            if "line4" in payload:
                l4 = payload["line4"]

        self.client.editsign(position, l1, l2, l3, l4, pre_18)
        return False

    def parse_play_client_settings(self):  # read Client Settings
        """ This is read for later sending to servers we connect to """
        self.client.clientSettings = self.packet.readpkt([D.RAW])[0]
        self.client.clientSettingsSent = True  # the packet is not stopped, sooo...
        return True

    def parse_play_click_window(self):  # click window
        if self.client.clientversion < mcpackets.PROTOCOL_1_8START:
            data = self.packet.readpkt([D.BYTE, D.SHORT, D.BYTE, D.SHORT, D.BYTE, D.SLOT_NO_NBT])
            # ("byte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
        elif mcpackets.PROTOCOL_1_8START < self.client.clientversion < mcpackets.PROTOCOL_1_9START:
            data = self.packet.readpkt([D.UBYTE, D.SHORT, D.BYTE, D.SHORT, D.BYTE, D.SLOT])
            # ("ubyte:wid|short:slot|byte:button|short:action|byte:mode|slot:clicked")
        elif mcpackets.PROTOCOL_1_9START <= self.client.clientversion < mcpackets.PROTOCOL_MAX:
            data = self.packet.readpkt([D.UBYTE, D.SHORT, D.BYTE, D.SHORT, D.VARINT, D.SLOT])
            # ("ubyte:wid|short:slot|byte:button|short:action|varint:mode|slot:clicked")
        else:
            data = [False, 0, 0, 0, 0, 0, 0]

        datadict = {
            "player": self.client.getplayerobject(),
            "wid": data[0],  # window id ... always 0 for inventory
            "slot": data[1],  # slot number
            "button": data[2],  # mouse / key button
            "action": data[3],  # unique action id - incrementing counter
            "mode": data[4],
            "clicked": data[5]  # item data
        }

        if not self.wrapper.events.callevent("player.slotClick", datadict):
            return False

        # for inventory control, the most straightforward way to update wrapper's inventory is
        # to use the data from each click.  The server will make other updates and corrections
        # via SET_SLOT

        # yes, this probably breaks for double clicks that send the item to who-can-guess what slot
        # we can fix that in a future update... this gets us 98% fixed (versus 50% before)
        # another source of breakage is if lagging causes server to deny the changes.  Our code
        # is not checking if the server accepted these changes with a CONFIRM_TRANSACTION.

        if data[0] == 0 and data[2] in (0, 1):  # window 0 (inventory) and right or left click
            if self.client.lastitem is None and data[5] is None:  # player first clicks on an empty slot - mark empty.
                self.client.inventory[data[1]] = None

            if self.client.lastitem is None:  # player first clicks on a slot where there IS some data..
                # having clicked on it puts the slot into NONE status (since it can now be moved)
                self.client.inventory[data[1]] = None  # we set the current slot to empty/none
                self.client.lastitem = data[5]  # ..and we cache the new slot data to see where it goes
                return True

            # up to this point, there was not previous item
            if self.client.lastitem is not None and data[5] is None:  # now we have a previous item to process
                self.client.inventory[data[1]] = self.client.lastitem  # that previous item now goes into the new slot.
                self.client.lastitem = None  # since the slot was empty, there is no newer item to cache.
                return True

            if self.client.lastitem is not None and data[5] is not None:
                # our last item now occupies the space clicked and the new item becomes the cached item.
                self.client.inventory[data[1]] = self.client.lastitem  # set the cached item into the clicked slot.
                self.client.lastitem = data[5]  # put the item that was in the clicked slot into the cache now.
                return True
        return True

    def parse_play_spectate(self):  # Spectate - convert packet to local server UUID
        # !? WHAT!?
        # ___________
        # "Teleports the player to the given entity. The player must be in spectator mode.
        # The Notchian client only uses this to teleport to players, but it appears to accept
        #  any type of entity. The entity does not need to be in the same dimension as the
        # player; if necessary, the player will be respawned in the right world."
        """ Inter-dimensional player-to-player TP ! """  # TODO !

        data = self.packet.readpkt([D.UUID, D.NULL])  # solves the uncertainty of dealing with what gets returned.
        # ("uuid:target_player")
        for client in self.wrapper.proxy.clients:
            if data[0] == client.uuid:
                self.client.server_connection.packet.sendpkt(self.client.pktSB.SPECTATE, [D.UUID], [client.serveruuid])
                return False
        return True
