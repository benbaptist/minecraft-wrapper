SERVER_STARTED = 0x00
SERVER_STARTING = 0x01
SERVER_STOPPING = 0x02
SERVER_STOPPED = 0x03
SERVER_ERROR = 0x03

BACKUP_STARTED = 0x05
BACKUP_COMPLETE = 0x06
BACKUP_FAILED = 0x07

def bytes_to_human(bytesize, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(bytesize) < 1024.0:
            return "%3.1f%s%s" % (bytesize, unit, suffix)
        bytesize /= 1024.0
    return "%.1f%s%s" % (bytesize, "Yi", suffix)
