
**class EntityControl**

    This class is accessed using self.api.minecraft.getEntityControl() since it is tied to a functioning server only.

    Entity controls are established by console when wrapper reads "preparing ...."

    

**def getEntityByEID(self, eid)**
 Returns the entity context or False if the specified entity ID doesn't exist.

        WARNING! understand that entities are very DYNAMIC.  The entity object you get
        could be modified or even deleted at any time!

        

**def countActiveEntities(self)**
 return a count of all entities. 

**def countEntitiesInPlayer(self, playername)**
returns a list of entity info dictionaries
            [
            {getEntityInfo(eid#1)},  # see getEntityInfo(self, eid)
            {getEntityInfo(eid#2)},
            {getEntityInfo(eid#3)},
            {getEntityInfo(...)}
            ]
                      @:type Dict
        

**def getEntityInfo(self, eid)**
 get dictionary of info on the specified EID.  Returns None if fails

        Sample item:
          {
            "player": "SapperLeader2",  # the player in whose world the entity exists
            "rodeBy": false,
            "eid": 126,                 # eid of entity - if two or more players share chunks, the same creeper
            "name": "Creeper",          #   could be in the other player's client under other eids
            "Riding": false,
            "position": [
              3333,
              29,
              2847
            ],
            "type": 50,                 # the type code for Creeper
            "isObject": false,
            "uuid": "fae14015-dde6-4e07-b5e5-f27536937a79"  # uuids are only on 1.9+ , but should be unique to object
          }

        

**def existsEntityByEID(self, eid)**
 A way to test whether the specified eid is valid 

**def killEntityByEID(self, eid, dropitems=False, count=1)**
 takes the entity by eid and kills the first entity of that type centered
        at the coordinates where that entity is.

        Args:
            eid - Entity EID on server
            dropitems - whether or not the entity death will drop loot
            finishstateof_domobloot - True/False - what the desired global state of DoMobLoot is on the server.
            count - used to specify more than one entity; again, centers on the specified eid location.

        
