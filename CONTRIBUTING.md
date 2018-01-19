### Scope ###
To prevent conflicts, issues, and other annoyances, This page discusses practices and guidelines for new commits (both pull requests and official contributors).  Feel free to provide feedback.

### WHICH REPO? ###

Normally, we make all pull requests to the development branch. Don't make any patches to the stable master branch unless it is a serious bug fix. If there is enough interest, we may open another branch or two for "experimental" versions.

__For the master branch__:
Only bug fixes are going into the master branch.  If the same code is bugged in the development branch, create a separate PR for it in accordance with the development branch guidelines.  Only submit the specific files you are changing when using `git add`; i.e - 
```
git add src/api/player.py
git add src/proxy.py
git commit -m "just changing something in player.py and proxy.py!"
git push origin master
```

__For the development branch__:

Make your desired changes and ___don't run the build script___.

The idea is that we don't want everyone pushing their own builds - it'll get confusing pretty quickly once we have multiple people working simultaneously and pushing code. This is to prevent creating duplicate build numbers and limit inconsistency between everyone's versions.


Contribution Guidelines
-----------------------

Here are our basic guidelines:

1. When you start coding, try to submit one pull request early (e.g. somewhere
   between 50-100 lines). While this does allow any problems that we never thought
   about to be caught early, the primary purpose is to serve as "notice of intent"
   that you will be working in a certain portion of code.  This allows for better
   coordination of efforts and maybe we can avert working on the same areas of code
   at once!  Mark this commit as "first draft .." in the commit message.

2. After that first commit, feel free to submit pull requests as often or as
   infrequently as you like.

3. When you are done with your "first draft" of the code, let us know in the
   commit message using something like "final commit".  We'll review your work 
   at that time.

4. If your code is less than 120 lines, go ahead and mark it as a "final commit"
   in the first commit message.

### Other guidelines... ###

5. PEP-8 code please!  The only exception are plugins and the plugin API where 
   mixedCase is the historic norm. Using a checker tool of some kind (or an IDE) 
   that will highlight PEP-8 problems is recommended. One area that needs 
   improvement was using lines > 79 characters in length.  We got sloppy on 
   this because my PyCharm's default was 120. Any new code should aim for 
   lines < 80.  We are not going to set it as a hard-coded limit, but more 
   of a guideline (presuming it is reasonably close, i.e, 100 characters is
   _not_ reasonably close), or where where a shortened line will break
   something (like the documentation creator needs function definitions on
   one line).  This will also only apply to changed lines until
   such time that the code becomes more reasonably compliant. 

5. Make sure your code will run on both Python 2.7 and 3.5 (and above) as
   a minimum.

6. Ensure you 'git pull' regularly and especially _right before_ you start
   creating new code.

7. Avoid holding onto code fixes for a really long time.  If you experience 
   delays, please keep us in the loop.

8. If you make changes to the public API doc strings, please test your changes
   to make sure they are valid ReStructuredText with no errors and look nice: 
   http://rst.ninjs.org/

### About the documentation... ###
If you find problems with the Wrapper documentation files, be aware that these
files cannot be edited directly.  They are built when a new build is created
using the -d (build documentation) flag:
`python ./build/build_script.py . dev -d`

The documentation for Wrapper.py comes from within wrapper source code from two areas:
1) events are built from docstrings located right after the event code like this:
    ``` python
    self.wrapper.events.callevent("player.message", {
        "player": self.getplayer(name),
        "message": message,
        "original": original
    })
    """ eventdoc
        <group> core/mcserver.py <group>

        <description> Player chat scrubbed from the console.
        <description>

        <abortable> 
        <abortable>

        <comments>
        This event is triggered by console chat which has already been sent.
        <comments>

        <payload>
        "player": playerobject
        "message": <str> type - what the player said in chat. ('hello everyone')
        "original": The original line of text from the console ('<mcplayer> hello everyone`)
        <payload>

    """
    ```
2) API and function/method documentation is created from the method docstrings found in all the modules located in the `wrapper/api` folder of the source code. All data in the docstring must be valid *rst, such as this example from `wrapper/api/player.py`:
    ```python
    def sendCommand(self, command, args):
        """
        Sends a command to the wrapper interface as the player instance.
        This would find a nice application with a '\sudo' plugin command.
    
        :sample usage:
    
            .. code:: python
    
                player=getPlayer("username")
                player.sendCommand("perms", ("users", "SurestTexas00", "info"))
    
            ..
    
        :Args:
            :command: The wrapper (or plugin) command to execute; no
             slash prefix
            :args: list of arguments (I think it is a list, not a
             tuple or dict!)
    
        :returns: Nothing; passes command through commands.py function
         'playercommand()'
    
        """
        pay = {"player": self, "command": command, "args": args}
        self.wrapper.api.callEvent("player.runCommand", pay)
    ```
