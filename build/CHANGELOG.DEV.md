Build 3:
- implement PARSER for player digging (internal refactor).
- remove some more test code (tracer branch leftovers).
- push build with staged code.  Has a bug:
    does not work with compression disabled.

Build 2:
- give plugins ability to return a False for onEnable().
Fixed a UUID error in API:
    - Turns out that plugins can call api.minecraft.lookupbyUUID and if a MCUUID
      object gets passed, you fry the wrapper cache with a non-json-serializable
      MCUUID(xx-xx--x--x--) object as the uuid index.
- start adding some type-hinting to wrapper functions.
- clean up stable plugins

Build 1:
- small footnote typo in main README.md corrected
- made the UUID lookups for getuuidbyusername case in-sensitive.  This was
 causing un-necessary mojang API lookups during certain operations just because
 a name was not capitalized properly.  Usernames are unique regardless of
 capitalization, making this an un-needed check.
- Fix bug allowing a group to be assigned to a player more than once.
- upgrade player permission items to operate with optional uuid=<MCUUID> to
 operate upon another player (logged on or not).
- add plugins "groupsmanager" and "portals" to stable plugins.

Starting with:
Build 0 [1.0.0 RC 0] - Development branch update
