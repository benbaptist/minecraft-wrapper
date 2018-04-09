Build 10 [1.0.8 RC 10]
- Remove player.interact event out of the block placement code because there
 really is no way to tell if the client is interacting or not based on inventory.
 clicking on a chest with no item or clicking on a chest with a block in hand still
 opens the chest, for example.
- added a player object "player" to event payloads that did not have it.  This is
 only a cosmetic change in the API (and a speed optimization) because the event
 code already added "player" objects to payloads missing the player object,  This
 also corrects the documentation that did not list player as a payload.  Retained
 the "playername" payload in these events, for backwards compatibility.
- Optimize regions plugin some more.

Build 9 [1.0.7 RC 9]
- Fix wrapper client inventory bugs (inconsistent use of None versus {"id" = -1}
 in code.

Build 8 [1.0.6 RC 8]
- api.helpers.get_int - accepts possible booleans
- add Regions suite to stable plugins.

Build 7 [1.0.5 RC 7]
- Make wrapper current through snapshot 18w14b:
    - add protocol 368 as PROTOCOL_PRE_RELEASE
    - add PROTOCOL_PRE_RELEASE packets for CB and SB.
    - Fix slot parsing, which has changed with new snapshots.
    **TEMPORARILY BROKE / not implemented yet** - server.autoCompletes
     (parse_cb.py) event is not compliant for sending/modding the new packet.
- Fix error that causes wrapper to think snapshots are pre-netty.
- Fix old Py3 Errors in NBT things
- Harden up wrapper's handling of disconnected players.
- Patch resource imports that may not work on Windows.

Build 6 [1.0.4 RC 6]
- Fixed wrapper's player.interact use_item event that has been broken
 ever since wrapper stopped using the old string-keys packet read() format.
- Restore interact event's ability to parse the placement coords of buckets.
- Add base API property `wrapper_version` to allow plugins to inspect Wrapper's version.

Build 5  [1.0.3 RC 5]
- Bugfix - name changes were not actually working (old name persisted).
- improved name changes to include offline hubs being able to update names too!
  : whitelist warning : Names are still whitelisted by offline name. An
   automatic name change will cause player to not be whitelisted (you will
   have to `whitelist add` the new name).

Starting with:
Build 4 [1.0.2 RC 4] - Development branch update
