-*- coding: utf-8 -*-
Copyright (C) 2016 - 2018 - BenBaptist and Wrapper.py developer(s).

**Welcome to the Wrapper.py Plugin API documentation!**

The API is divided into modules.  Click on each module to see it's documentation.

 [#api/wrapperconfig](/documentation/wrapperconfig.rst)

 [#api/base](/documentation/base.rst)

 [#api/minecraft](/documentation/minecraft.rst)

 [#api/player](/documentation/player.rst)

 [#api/world](/documentation/world.rst)

 [#api/entity](/documentation/entity.rst)

 [#api/backups](/documentation/backups.rst)

 [#api/helpers](/documentation/helpers.rst)

<br>**Click here for a list of Wrapper's events**<br>[Wrapper.py Events](/documentation/events.rst)<br>


Looking for a specific method?  search this list to see which api module has it:

-  Config file items and layout
 -> #api/wrapperconfig
-  addGroupPerm -> #api/base
-  adjustBackupInterval -> #api/backups
-  adjustBackupsKept -> #api/backups
-  backupInProgress -> #api/backups
-  backupIsIdle -> #api/backups
-  banIp -> #api/minecraft
-  banName -> #api/minecraft
-  banUUID -> #api/minecraft
-  blockForEvent -> #api/base
-  broadcast -> #api/minecraft
-  callEvent -> #api/base
-  changeServerProps -> #api/minecraft
-  chattocolorcodes -> #api/helpers
-  checkPassword -> #api/base
-  configWrapper -> #api/minecraft
-  config_to_dict_read -> #api/helpers
-  config_write_from_dict -> #api/helpers
-  connect -> #api/player
-  console -> #api/minecraft
-  countActiveEntities -> #api/entity
-  countEntitiesInPlayer -> #api/entity
-  createGroup -> #api/base
-  deOp -> #api/minecraft
-  deleteGroup -> #api/base
-  deleteGroupPerm -> #api/base
-  disableBackups -> #api/backups
-  enableBackups -> #api/backups
-  epoch_to_timestr -> #api/helpers
-  execute -> #api/player
-  existsEntityByEID -> #api/entity
-  fill -> #api/world
-  format_bytes -> #api/helpers
-  getAllPlayers -> #api/minecraft
-  getBlock -> #api/world
-  getClient -> #api/player
-  getDimension -> #api/player
-  getEntityByEID -> #api/entity
-  getEntityControl -> #api/minecraft
-  getEntityInfo -> #api/entity
-  getFirstLogin -> #api/player
-  getGameRules -> #api/minecraft
-  getGamemode -> #api/player
-  getGroups -> #api/player
-  getHeldItem -> #api/player
-  getItemInSlot -> #api/player
-  getLevelInfo -> #api/minecraft
-  getOfflineUUID -> #api/minecraft
-  getPlayer -> #api/minecraft
-  getPlayers -> #api/minecraft
-  getPluginContext -> #api/base
-  getPosition -> #api/player
-  getServer -> #api/minecraft
-  getServerPackets -> #api/minecraft
-  getServerPath -> #api/minecraft
-  getSpawnPoint -> #api/minecraft
-  getStorage -> #api/base
-  getTime -> #api/minecraft
-  getTimeofDay -> #api/minecraft
-  getUuidCache -> #api/minecraft
-  getWorld -> #api/minecraft
-  getWorldName -> #api/minecraft
-  get_int -> #api/helpers
-  getargs -> #api/helpers
-  getargsafter -> #api/helpers
-  getfileaslines -> #api/helpers
-  getjsonfile -> #api/helpers
-  getplayerby_eid -> #api/minecraft
-  giveStatusEffect -> #api/minecraft
-  hasGroup -> #api/player
-  hasPermission -> #api/player
-  hashPassword -> #api/base
-  isIpBanned -> #api/minecraft
-  isOp -> #api/player
-  isServerStarted -> #api/minecraft
-  isUUIDBanned -> #api/minecraft
-  isipv4address -> #api/helpers
-  kick -> #api/player
-  killEntityByEID -> #api/entity
-  lookupUUID -> #api/minecraft
-  lookupbyName -> #api/minecraft
-  lookupbyUUID -> #api/minecraft
-  makeOp -> #api/minecraft
-  message -> #api/minecraft
-  message -> #api/player
-  mkdir_p -> #api/helpers
-  openWindow -> #api/player
-  pardonIp -> #api/minecraft
-  pardonName -> #api/minecraft
-  pardonUUID -> #api/minecraft
-  performBackup -> #api/backups
-  pickle_load -> #api/helpers
-  pickle_save -> #api/helpers
-  processcolorcodes -> #api/helpers
-  processoldcolorcodes -> #api/helpers
-  pruneBackups -> #api/backups
-  putjsonfile -> #api/helpers
-  read_timestr -> #api/helpers
-  readout -> #api/helpers
-  refreshOpsList -> #api/minecraft
-  registerCommand -> #api/base
-  registerEvent -> #api/base
-  registerHelp -> #api/base
-  registerPermission -> #api/base
-  removeGroup -> #api/player
-  removePermission -> #api/player
-  replace -> #api/world
-  resetGroups -> #api/base
-  resetPerms -> #api/player
-  resetUsers -> #api/base
-  say -> #api/player
-  scrub_item_value -> #api/helpers
-  sendAlerts -> #api/base
-  sendBlock -> #api/player
-  sendCommand -> #api/player
-  sendEmail -> #api/base
-  setBlock -> #api/minecraft
-  setChunk -> #api/world
-  setGamemode -> #api/player
-  setGroup -> #api/player
-  setLocalName -> #api/minecraft
-  setPermission -> #api/player
-  setPlayerAbilities -> #api/player
-  setResourcePack -> #api/player
-  setVisualXP -> #api/player
-  set_item -> #api/helpers
-  summonEntity -> #api/minecraft
-  teleportAllEntities -> #api/minecraft
-  uuid -> #api/player
-  verifyTarInstalled -> #api/backups
-  wrapperHalt -> #api/base