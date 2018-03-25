
**< class World(object) >**

    .. code:: python

        def __init__(self, name, mcserver)

    ..

    This class is accessed via getWorld().  Requires a running server.

    .. code:: python

        <object> = self.api.minecraft.getWorld()
        <object>.<World_method>
    ..

    World is established by console when wrapper reads "preparing ...."

    

-  fill(self, position1, position2, tilename, damage=0, mode="destroy", data=None)

        Fill a 3D cube with a certain block.

        :Args:
            :position1: tuple x, y, z
            :position2: tuple x, y, z
            :damage: see minecraft Wiki
            :mode: destroy, hollow, keep, outline
            :data: see minecraft Wiki

        

-  replace(self, position1, position2, tilename1, damage1, tilename2, damage2=0)

        Replace specified blocks within a 3D cube with another specified block.

        :Args: see minecraft Wiki

        

-  getBlock(self, pos)

        not implemented

        

-  setChunk(self, x, z, chunk)
 not implemented 

**< class Chunk(object) >**

    not implemented

    
