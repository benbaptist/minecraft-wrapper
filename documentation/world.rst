
**< class World >**

    This class is accessed via getWorld().  Requires a running server.

    World is established by console when wrapper reads "preparing ...."

    

def fill(self, position1, position2, tilename, damage=0, mode="destroy", data=None)

        Fill a 3D cube with a certain block.

        :Args:
            :position1: tuple x, y, z
            :position2: tuple x, y, z
            :damage: see minecraft Wiki
            :mode: destroy, hollow, keep, outline
            :data: see minecraft Wiki

        

def replace(self, position1, position2, tilename1, damage1, tilename2, damage2=0)

        Replace specified blocks within a 3D cube with another specified block.

        :Args: see minecraft Wiki

        

def getBlock(self, pos)

        not implemented

        

def setChunk(self, x, z, chunk)
 not implemented 

**< class Chunk >**

    not implemented

    
