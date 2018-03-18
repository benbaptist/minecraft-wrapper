# -*- coding: utf-8 -*-

# Copyright (C) 2016, 2017 - BenBaptist and Wrapper.py developer(s).
# https://github.com/benbaptist/minecraft-wrapper
# This program is distributed under the terms of the GNU
# General Public License, version 3 or later.

import json

from proxy.entity.entitybasics import Entity
from proxy.utils.constants import *

# Py3-2
import sys
PY3 = sys.version_info > (3,)
if PY3:
    # noinspection PyShadowingBuiltins
    xrange = range

TRANSLATE = {
    "op":
        [
            {'clickEvent': {'action': 'suggest_command', 'value': '/op '},
             'translate': 'commands.op.usage'},

            {'clickEvent': {'action': 'suggest_command', 'value': '/op '},
             'text':
                 '/op <player> [-s SUPEROP] [-o OFFLINE] [-l <superoplevel>]',
             'italic': True,
             'color': 'yellow'}
        ],
    "whitelist":
        [
            {'clickEvent': {'value': '/whitelist ', 'action': 'suggest_command'},  # noqa
             'translate': 'commands.whitelist.usage'},

            {'clickEvent': {'action': 'suggest_command', 'value': '/whitelist '},  # noqa
             'text':
                 '/whitelist <on|off|list|add|remvove|reload|offline|online>',
             'italic': True,
             'color': 'yellow'}
        ],
}


# noinspection PyMethodMayBeStatic
class ParseCB(object):
    """
    ParseSB parses client bound packets that are coming from the server.
    """
    def __init__(self, server, packet):
        self.server = server
        self.log = self.server.log
        self.client = server.client
        self.pktCB = self.server.pktCB
        self.pktSB = self.server.pktSB
        self.proxy = server.client.proxy
        self.packet = packet
        self.ent_control = self.proxy.entity_control

    # Items that need parsed and re-sent with proper offline/online UUID
    # translation.

    def parse_play_player_list_item(self):
        """This must be parsed and modified to make sure UUIDs match.
        Otherwise weird things can happen like players not seeing
        each other or duplicate names on the tab list, etc."""
        if self.server.version >= PROTOCOL_1_8START:
            header = self.packet.readpkt([VARINT, VARINT])
            # ("varint:action|varint:length")
            number_players = header[1]
            action = header[0]
            curr_index = 0

            while curr_index < number_players:
                player_uuid_from_server = self.packet.readpkt([UUID])[0]
                player_client = self.proxy.getclientbyofflineserveruuid(
                    player_uuid_from_server)

                if not player_client:
                    self.log.debug(
                        "(%s)parse.cb.py - Player list item:  Player uuid "
                        "not on server: %s" % (self.client.username,
                                               player_uuid_from_server)
                    )
                    curr_index += 1
                    continue
                # self.log.debug(
                #    "(%s)parse.cb.py - Player list item: %s" % (
                #        self.client.username,
                #        player_uuid_from_server)
                # )
                uuid_to_send = player_client.wrapper_uuid
                curr_index += 1
                # raw = b''

                # Action Add Player
                if action == 0:
                    properties = player_client.properties
                    raw = b""
                    for prop in properties:
                        raw += self.client.packet.send_string(prop["name"])
                        raw += self.client.packet.send_string(prop["value"])
                        if "signature" in prop:
                            raw += self.client.packet.send_bool(True)
                            raw += self.client.packet.send_string(
                                prop["signature"])
                        else:
                            raw += self.client.packet.send_bool(False)
                    raw += self.client.packet.send_varint(0)
                    raw += self.client.packet.send_varint(0)
                    raw += self.client.packet.send_bool(False)
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM[PKT],
                        [VARINT, VARINT, UUID, STRING, VARINT, RAW],
                        (0, 1, uuid_to_send, player_client.username,
                         len(properties), raw))

                # Action Update Gamemode
                elif action == 1:
                    data = self.packet.readpkt([VARINT])
                    # I think if we are sending this packet to our own player
                    # we need to send the client the online UUID.  Everyone
                    # else would get the offline version
                    # TODO Corrects the noclip spectator problem??
                    gamemode = data[0]
                    # ("varint:gamemode")

                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM[PKT],
                        [VARINT, VARINT, UUID, VARINT],
                        (1, 1, uuid_to_send, gamemode))

                # Action Update Latency
                elif action == 2:
                    data = self.packet.readpkt([VARINT])
                    ping = data[0]
                    # ("varint:ping")
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM[PKT],
                        [VARINT, VARINT, UUID, VARINT],
                        (2, 1, uuid_to_send, ping))

                # Action Update Display Name
                elif action == 3:
                    data = self.packet.readpkt([BOOL])
                    # ("bool:has_display")
                    hasdisplay = data[0]
                    if hasdisplay:
                        data = self.packet.readpkt([STRING])
                        displayname = data[0]
                        # ("string:displayname")
                        self.client.packet.sendpkt(
                            self.pktCB.PLAYER_LIST_ITEM[PKT],
                            [VARINT, VARINT, UUID, BOOL, STRING],
                            (3, 1, uuid_to_send, True, displayname))

                    else:
                        self.client.packet.sendpkt(
                            self.pktCB.PLAYER_LIST_ITEM[PKT],
                            [VARINT, VARINT, UUID, VARINT],
                            (3, 1, uuid_to_send, False))

                # Remove Player
                elif action == 4:
                    self.client.packet.sendpkt(
                        self.pktCB.PLAYER_LIST_ITEM[PKT],
                        [VARINT, VARINT, UUID],
                        (4, 1, uuid_to_send))

            # final send should go here?
            # This was indented with the elif's - would that be an error, cutting the list short??  # noqa
            return False
        else:  # version < 1.7.9 needs no processing
            return True

        # moving the return False above made this line unreachable
        #return True

    def parse_play_spawn_player(self):  # embedded UUID -must parse.
        """
        This packet  is used to spawn other players into a player
        client's world.  if this packet does not arrive, the other
        player(s) will not be visible to the client
        it does not play a role in the player's spawing process.
        """
        dt = self.packet.readpkt(self.pktCB.SPAWN_PLAYER[PARSER])
        # dt = (eid, uuid, REST)
        # We dont need to read the whole thing.
        eid, player_uuid_on_server, rest = dt

        player_client = self.proxy.getclientbyofflineserveruuid(
            player_uuid_on_server
        )
        self.log.debug(
            "(%s)parse.spawn.player - My UUIDs: %s|%s\n"
            "This uuid: %s" % (self.client.username,
                               self.client.wrapper_uuid.string,
                               self.client.local_uuid.string,
                               player_uuid_on_server)
        )
        if player_client:
            if player_client.wrapper_uuid:
                self.client.packet.sendpkt(
                    self.pktCB.SPAWN_PLAYER[PKT],
                    self.pktCB.SPAWN_PLAYER[PARSER],
                    (eid, player_client.wrapper_uuid, rest))
            return False
        return False

    # Wrapper events and info section:

    def parse_play_chat_message(self):
        if not self.client.local:
            return True
        data, position = self.packet.readpkt(self.pktCB.CHAT_MESSAGE[PARSER])
        # position (1.8+ only)
        # 0: chat (chat box), 1: system message (chat box), 2: above hotbar

        # Over-ride help display

        for eachtrans in TRANSLATE:
            if TRANSLATE[eachtrans][0] == data:
                new_usage = TRANSLATE[eachtrans][1]
                data = new_usage
        # self.log.debug(data)

        payload = self.proxy.eventhandler.callevent(
            "player.chatbox", {"playername": self.client.username,
                               "json": data})
        """ eventdoc
            <group> Proxy <group>

            <description> Chat message sent from the server to the client.
            <description>

            <abortable> Yes <abortable>

            <comments>
            - The message will not reach the client if the event is returned False.
            - If json chat (dict) or text is returned, that value will be sent 
            to the client instead.
            <comments>
            
            <payload>
            "playername": client username
            "json": json or string data
            <payload>

        """  # noqa

        # reject the packet outright .. no chat gets sent to the client
        if payload is False:
            return False

        # packet allowed to pass (but not changed by any plugin event)
        if payload is True:
            return True

        # pre - 1.8 only accepts string (now it's a dict/json parse)
        if self.client.clientversion < PROTOCOL_1_8START:
            if type(payload) == dict:
                payload = json.dumps(payload)

        self.client.packet.sendpkt(self.pktCB.CHAT_MESSAGE[PKT],
                                   self.pktCB.CHAT_MESSAGE[PARSER],
                                   (payload, position))
        return False

    def parse_play_player_poslook(self):
        """This packet is not actually sent very often.  Maybe on respawns
        or position corrections.  Hub requires this to be updated"""
        # CAVEAT - The client and server bound packet formats are different!
        data = self.packet.readpkt(self.pktCB.PLAYER_POSLOOK[PARSER])
        relativemarker = data[5]
        # fill player pos if this is absolute position (or a pre 1.8 server)
        if relativemarker == 0 or self.server.version < PROTOCOL_1_8START:
            self.client.position = (data[0], data[1], data[2])
        return True

    def parse_play_use_bed(self):
        if not self.client.local:
            return True
        data = self.packet.readpkt([VARINT, POSITION])
        if data[0] == self.client.server_eid:
            self.proxy.eventhandler.callevent(
                "player.usebed",
                {"playername": self.client.username, "position": data[1]},
                abortable=False
            )

            """ eventdoc
                <group> Proxy <group>

                <description> Sent when server sends client to bedmode.
                <description>

                <abortable> No - The server thinks the client is in bed already. <abortable>

                <comments>
                <comments>

                <payload>
                "playername": client username
                "position": position of bed
                <payload>

            """  # noqa
        return True

    def parse_play_join_game(self):
        """Hub continues to track these items, especially dimension"""
        self.client.server_connection.plugin_ping()
        data = self.packet.readpkt(self.pktCB.JOIN_GAME[PARSER])
        self.client.gamemode = data[1]
        self.client.dimension = data[2]
        self.client.server_eid = data[0]
        self.log.debug(
            "(Client: %s) sending Join.Game GM: %s|DIM: %s| EID %s" % (
                self.client.username,
                self.client.gamemode,
                self.client.dimension,
                self.client.server_eid
            )
        )

        return True

    def parse_play_spawn_position(self):
        """Sent by the server after login to specify the coordinates of the
        spawn point (the point at which players spawn at, and which the
        compass points to). It can be sent at any time to update the point
        compasses point at."""
        if not self.client.local:
            return True
        data = self.packet.readpkt([POSITION])
        self.proxy.eventhandler.callevent(
            "player.spawned", {"playername": self.client.username,
                               "position": data},
            abortable=False
        )

        """ eventdoc
            <group> Proxy <group>

            <description> Sent when server advises the client of the Spawn position.
            <description>

            <abortable> No - Notification only. <abortable>

            <comments>  Sent by the server after login to specify the coordinates of the spawn point (the point at which players spawn at, and which the compass points to). It can be sent at any time to update the point compasses point at.
            <comments>

            <payload>
            "playername": client username
            "position": Spawn's position
            <payload>

        """  # noqa
        return True

    def parse_play_respawn(self):
        """Hub continues to track these items, especially dimension"""
        data = self.packet.readpkt([INT, UBYTE, UBYTE, STRING])
        # "int:dimension|ubyte:difficulty|ubyte:gamemode|level_type:string")
        self.client.dimension = data[0]
        self.client.difficulty = data[1]
        self.client.gamemode = data[2]
        self.client.level_type = data[3]
        return True

    def parse_play_change_game_state(self):
        """Hub needs to track these items to prevent perpetual raining, etc."""
        data = self.packet.readpkt([UBYTE, FLOAT])
        # ("ubyte:reason|float:value")
        if data[0] == 3:
            self.client.gamemode = int(data[1])
        if data[0] == 2:
            self.client.raining = True
        if data[0] == 1:
            self.client.raining = False
        return True

    def parse_play_disconnect(self):
        """Hub needs to monitor this to respawn someone to the hub."""
        if self.client.local:
            return True
        message = self.packet.readpkt([JSON])
        self.server.close_server("Server kicked %s with PLAY disconnect: %s" %
                                 (self.client.username, message))
        # client connection will determine if player needs to be kicked
        self.server.client.notify_disconnect(message)
        return False

    def parse_play_time_update(self):
        if not self.client.local:
            return True
        data = self.packet.readpkt([LONG, LONG])
        # "long:worldage|long:timeofday")
        # There could be a number of clients trying to update this at once
        # noinspection PyBroadException
        try:
            self.proxy.srv_data.timeofday = data[1]
        except:
            pass
        return True

    def parse_play_tab_complete(self):
        if not self.client.local:
            return True
        rawdata = self.packet.readpkt(self.pktCB.TAB_COMPLETE[PARSER])
        data = rawdata[0]

        payload = self.proxy.eventhandler.callevent(
            "server.autoCompletes", {
                "playername": self.client.username,
                "completes": data})
        """ eventdoc
            <group> Proxy <group>

            <description> internalfunction <description>

            <abortable> Yes <abortable>

            <comments>
            Can be aborted by returning False. To change the contents, return
            an alternate list of strings.
            *This is a wrapper internal function* Errors could be created if 
            you try to abort/edit this event payload.
            <comments>
            <payload>
            "playername": player's name
            "completes": A list of auto-completions supplied by the server.
            <payload>

        """

        # allow to cancel event...
        if payload is False:
            return False

        # change payload.
        if type(payload) == list:
            self.client.packet.sendpkt(self.pktCB.TAB_COMPLETE[PKT],
                                       self.pktCB.TAB_COMPLETE[PARSER],
                                       [payload])
            return False
        return True

    # chunk processing
    def parse_play_chunk_data(self):
        """CHUNK_DATA
        Cache first 49 raw chunks for use with respawning."""
        if len(self.client.first_chunks) < 49:
            data = self.packet.readpkt([RAW, ])
            self.client.first_chunks.append(data)
        return True

    # Window processing/ inventory tracking
    # ---------------------------------------

    def parse_play_held_item_change(self):
        data = self.packet.readpkt(self.pktCB.HELD_ITEM_CHANGE[PARSER])
        self.client.slot = data[0]

    def parse_play_open_window(self):
        # This works together with SET_SLOT to maintain
        #  accurate inventory in wrapper
        data = self.packet.readpkt(self.pktCB.OPEN_WINDOW[PARSER])
        self.client.currentwindowid = data[0]
        # self.client.noninventoryslotcount = data[3]
        return True

    def parse_play_set_slot(self):
        """Hub still needs this to set player inventory on login"""
        data = self.packet.readpkt(self.pktCB.SET_SLOT[PARSER])

        if data[0] == 0:
            self.client.inventory[data[1]] = data[2]
        if data[0] < 0:
            return True

        # This part updates our inventory from additional
        #  windows the player may open
        # MC|PickItem causes windowid = -2
        if data[0] in (self.client.currentwindowid, -2):
            currentslot = data[1]
            slotdata = data[2]
            self.client.inventory[currentslot] = slotdata
        return True

    # Entity processing sections.  Needed to track entities and EIDs

    def parse_play_spawn_object(self):
        if not self.client.local:
            return True
        # objects are entities and are GC-ed by detroy entities packet
        if not self.ent_control:
            return True  # return now if no object tracking
        if self.server.version < PROTOCOL_1_9START:
            dt = self.packet.readpkt(
                [VARINT, NULL, BYTE, INT, INT, INT, BYTE, BYTE])
            dt[3], dt[4], dt[5] = dt[3] / 32, dt[4] / 32, dt[5] / 32
            # "varint:eid|byte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw")
        else:
            dt = self.packet.readpkt(
                [VARINT, UUID, BYTE, DOUBLE, DOUBLE, DOUBLE, BYTE, BYTE])
            # "varint:eid|uuid:objectUUID|byte:type_|int:x|int:y|int:z|
            #     byte:pitch|byte:yaw|int:info|
            # short:velocityX|short:velocityY|short:velocityZ")
        entityuuid = dt[1]

        # we have to check these first, lest the object type be new
        # and cause an exception.
        if dt[2] in self.ent_control.objecttypes:
            objectname = self.ent_control.objecttypes[
                dt[2]]
            newobject = {dt[0]: Entity(dt[0], entityuuid, dt[2], objectname,
                                       (dt[3], dt[4], dt[5],), (dt[6], dt[7]),
                                       True, self.client.username)}

            self.ent_control.entities.update(newobject)
        return True

    def parse_play_spawn_mob(self):
        if not self.client.local:
            return True
        if not self.ent_control:
            return True
        if self.server.version < PROTOCOL_1_9START:
            dt = self.packet.readpkt(
                [VARINT, NULL, UBYTE, INT, INT, INT, BYTE, BYTE, BYTE, REST])
            dt[3], dt[4], dt[5] = dt[3] / 32, dt[4] / 32, dt[5] / 32
            # "varint:eid|ubyte:type_|int:x|int:y|int:z|byte:pitch|byte:yaw|"
            # "byte:head_pitch|...
            # STOP PARSING HERE: short:velocityX|short:velocityY|
            #     short:velocityZ|rest:metadata")
        else:
            dt = self.packet.readpkt([VARINT, UUID, UBYTE, DOUBLE, DOUBLE,
                                      DOUBLE, BYTE, BYTE, BYTE, REST])

            # ("varint:eid|uuid:entityUUID|ubyte:type_|int:x|int:y|int:z|"
            # "byte:pitch|byte:yaw|byte:head_pitch|
            # STOP PARSING HERE: short:velocityX|short:velocityY|
            #     short:velocityZ|rest:metadata")

        entityuuid = dt[1]

        # if the dt[2] mob type is not in our defined entity types,
        # it won't be tracked.. however, the undefined mob will not
        # cause an exception.
        if dt[2] in self.ent_control.entitytypes:
            mobname = self.ent_control.entitytypes[
                dt[2]]["name"]
            newmob = {dt[0]: Entity(dt[0], entityuuid, dt[2], mobname,
                                    (dt[3], dt[4], dt[5],),
                                    (dt[6], dt[7], dt[8]),
                                    False, self.client.username)}

            self.ent_control.entities.update(newmob)
        return True

    def parse_play_entity_relative_move(self):
        if not self.client.local:
            return True
        if not self.ent_control:
            return True
        if self.server.version < PROTOCOL_1_8START:  # 1.7.10 - 1.7.2
            data = self.packet.readpkt([INT, BYTE, BYTE, BYTE])

        # FutureVersion > elif self.version > mcpacket.PROTOCOL_1_7_9:  1.8 ++
        else:
            data = self.packet.readpkt([VARINT, BYTE, BYTE, BYTE])
        # ("varint:eid|byte:dx|byte:dy|byte:dz")

        entupd = self.ent_control.getEntityByEID(
            data[0])
        if entupd:
            entupd.move_relative((data[1], data[2], data[3]))
        return True

    def parse_play_entity_teleport(self):
        if not self.client.local:
            return True
        if not self.ent_control:
            return True
        if self.server.version < PROTOCOL_1_8START:  # 1.7.10 and prior
            data = self.packet.readpkt([INT, INT, INT, INT, REST])
        elif PROTOCOL_1_8START <= self.server.version < PROTOCOL_1_9START:
            data = self.packet.readpkt([VARINT, INT, INT, INT, REST])
        else:
            data = self.packet.readpkt([VARINT, DOUBLE, DOUBLE, DOUBLE, REST])
            data[1], data[2], data[3] = data[1] * 32, \
                data[2] * 32, data[3] * 32

        # ("varint:eid|int:x|int:y|int:z|byte:yaw|byte:pitch")

        entupd = self.ent_control.getEntityByEID(
            data[0])
        if entupd:
            entupd.teleport((data[1], data[2], data[3]))
        return True

    def parse_play_attach_entity(self):
        if not self.client.local:
            return True
        if not self.ent_control:
            return True
        data = []
        leash = True  # False to detach
        if self.server.version < PROTOCOL_1_8START:
            data = self.packet.readpkt([INT, INT, BOOL])
            leash = data[2]
        if self.server.version >= PROTOCOL_1_9START:
            data = self.packet.readpkt([INT, INT])
            if data[1] == -1:
                leash = False
        entityeid = data[0]  # rider, leash holder, etc
        vehormobeid = data[1]  # vehicle, leashed entity, etc

        if entityeid == self.client.server_eid:
            if not leash:
                self.proxy.eventhandler.callevent(
                    "entity.unmount", {"playername": self.client.username,
                                       "vehicle_id": vehormobeid,
                                       "leash": leash},
                    abortable=False
                )
                """ eventdoc
                    <group> Proxy <group>

                    <description> Sent when player attaches to entity.
                    <description>

                    <abortable> No - Notification only. <abortable>

                    <comments> Only works if entity controls are enabled.  Entity controls
                    add significant load to wrapper's packet parsing and is off by default.
                    <comments>

                    <payload>
                    "playername": client username
                    "vehicle_id": EID of vehicle or MOB
                    "leash": leash True/False
                    <payload>

                """  # noqa
                self.log.debug("player unmount called for %s",
                               self.client.username)
                self.client.riding = None
            else:
                self.proxy.eventhandler.callevent(
                    "entity.mount", {"playername": self.client.username,
                                     "vehicle_id": vehormobeid,
                                     "leash": leash},
                    abortable=False
                )
                """ eventdoc
                    <group> Proxy <group>

                    <description> Sent when player detaches/unmounts entity.
                    <description>

                    <abortable> No - Notification only. <abortable>

                    <comments> Only works if entity controls are enabled.  Entity controls
                    add significant load to wrapper's packet parsing and is off by default.
                    <comments>

                    <payload>
                    "playername": client username
                    "vehicle_id": EID of vehicle or MOB
                    "leash": leash True/False
                    <payload>

                """  # noqa
                self.client.riding = vehormobeid
                self.log.debug("player mount called for %s on eid %s",
                               self.client.username, vehormobeid)
                if not self.ent_control:
                    return
                entupd = self.ent_control.getEntityByEID(
                    vehormobeid)
                if entupd:
                    self.client.riding = entupd
                    entupd.rodeBy = self.client
        return True

    def parse_play_destroy_entities(self):
        # Get rid of dead entities so that python can GC them.
        # TODO - not certain this works correctly (errors -
        # eids not used and too broad exception)
        if not self.client.local:
            return True
        if not self.ent_control:
            return True

        # noinspection PyUnusedLocal
        eids = []  # todo what was this for??
        if self.server.version < PROTOCOL_1_8START:
            # make sure we get iterable integer
            entitycount = bytearray(self.packet.readpkt([BYTE])[0])[0]
            parser = [INT]
        else:
            # TODO - error when more than 256 entities?
            rawread = self.packet.readpkt([VARINT])
            entitycount = rawread[0]
            parser = [VARINT]

        for _ in range(entitycount):
            eid = self.packet.readpkt(parser)[0]
            # noinspection PyBroadException
            if eid in self.ent_control.entities:
                self.ent_control.entities.pop(eid, None)

        return True
