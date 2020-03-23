# Overview #
Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying
the server jar file. It comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used
to create Bukkit-like plugins without any server modding.

We also have a gitter channel: [![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# 'Lite' Version #
This is a new branch of Wrapper.py. It's a complete re-write of Wrapper.py, and is focused on being extremely lightweight and clean.

### **Design Goals**
- Quick setup
- Robust, stable, set-it-and-forget-it design
    - Wrapper should always be able to start without user input (e.g. with a physical server boot)
    - Updates to Wrapper should never intrude or require user input to fix problems
    - Resilient to corruption, should repair itself
- No excess of functionality; only bare bone features will be implemented
- Plugin API, to supplement any specific features or use cases
- Python 2.x and 3.x compatible

###  **Wrapper.py Versions**

 - [Master branch "stable"](https://github.com/benbaptist/minecraft-wrapper/tree/master):  Stable branch that is only updated with serious bug fixes and major releases. <sup id="a1">[1](#f1)</sup>
 - [Development branch "dev"](https://github.com/benbaptist/minecraft-wrapper/tree/development):  Development branch with newer features.
 - [Lite branch "dev"](https://github.com/benbaptist/minecraft-wrapper/tree/development):  A brand new, complete re-write of Wrapper.py, with a focus on being lightweight.

WARNING: Wrapper.py will automatically accept the Minecraft EULA on your behalf. <sup id="a2">[2](#f2)</sup>
