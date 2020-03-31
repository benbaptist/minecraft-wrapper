SERVER_STARTING= 0x00
SERVER_STARTED = 0x01
SERVER_STOPPING = 0x02
SERVER_STOPPED = 0x03
SERVER_ERROR = 0x04
SERVER_FROZEN = 0x05

BACKUP_STARTED = 0x10
BACKUP_COMPLETE = 0x11
BACKUP_FAILED = 0x12
BACKUP_CANCELED = 0x13

def bytes_to_human(bytesize, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(bytesize) < 1024.0:
            return "%3.1f%s%s" % (bytesize, unit, suffix)
        bytesize /= 1024.0
    return "%.1f%s%s" % (bytesize, "Yi", suffix)

CONFIG_TEMPLATE = {
    "general": {
        "debug-mode": True
    },
    "server": {
        "jar": "server.jar",
        "arguments": "",
        "auto-restart": True
    },
    "dashboard": {
        "enable": False,
        "bind": {
            "ip": "127.0.0.1",
            "port": 8025
        },
        "root-password": None
    },
    "scripts": {
        "enable": False,
        "scripts": {
            "server-started": None,
            "server-stopped": None,
            "backup-start": None,
            "backup-complete": None,
            "player-join": None,
            "player-part": None
        }
    },
    "backups": {
        "enable": False,
        "archive-format": {
            "format": "auto",
            "compression": {
                "enable": True
            }
        },
        "history": 50,
        "interval-seconds": 600,
        "only-backup-if-player-joins": True,
        "destination": "backups",
        "ingame-notification": {
            "enable": True,
            "only-ops": False,
            "verbose": False
        },
        "backup-mode": "auto",
        "include": {
            "world": True,
            "logs": False,
            "server-properties": False,
            "wrapper-data": True,
            "whitelist-ops-banned": True
        },
        "include-paths": ["wrapper-data"]
    }
}
