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
