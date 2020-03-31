# Overview #
[![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying
the Minecraft server jar. It comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used
to create Bukkit-like plugins without any server modding.

Join us on Gitter!

# Quick Start #
```
pip install https://github.com/benbaptist/minecraft-wrapper/archive/lite.zip
```

Just run `wrapper-lite` in the working directory of your Minecraft server to start.
On first start, it'll write a configuration file to `wrapper-data/config.json`. Edit to your needs, and then run `wrapper-lite` again.

You may need to adjust your shell's $PATH to incorporate your local bin folder, depending on your system. For some systems, adding this to your .bashrc may work:

```
export PATH=$PATH:~/.local/bin
```

Wrapper.py will automatically accept the Minecraft server EULA on your behalf.

# 'Lite' Version #
This is a new branch of Wrapper.py. It's a complete re-write of Wrapper.py, and is focused on being extremely lightweight and clean.

### **Design Goals of the 'Lite' Version**
- Quick setup
- Robust, stable, set-it-and-forget-it design
    - Wrapper should always be able to start without user input (e.g. with a physical server boot)
    - Updates to Wrapper should never intrude or require user input to fix problems
    - Resilient to corruption, should repair itself
- No excess of functionality; only bare bone features will be implemented
- Plugin API, to supplement any specific features or use cases not built into the wrapper
- Python 2.x and 3.x compatible
