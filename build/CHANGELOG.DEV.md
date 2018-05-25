Build 22
- Implement the proxy host as a ProcessPoolExecutor multiprocessor (only on Python3)

Build 21 (In-process Dev build) [1.0.16 RC 21]
- Refractor proxy and remove external "ServerVitals" class and integrate wrapper into proxy again.

Build 21 [1.0.16 RC 21]  (Patch to Master)
- Bugfix - at player logout (mcserver.py), server would attempt to run
 proxy method removestaleclients(), even if proxy mode was not running.

Starting with:
Build 20 [1.0.15 RC 20] - Development branch update
- includes first version of vanilla claims plugin.
