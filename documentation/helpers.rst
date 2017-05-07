
**< class Helpers >**

This is not actually a class at all, but a module collection of
Wrapper's helpful utilities.

This module is imported with the core API and is accessible
using 'self.api.helpers'

    .. code:: python

        # can be accessed directly:
        self.api.helpers.getargs(args, 2)

        # or a local reference to the module in your plugin:
        <yourobject> = self.api.helpers
        <yourobject>.getargs(args, 2)

    ..



-  config_to_dict_read(filename, filepath)

    reads a disk file with '=' lines (like server.properties) and
    returns a keyed dictionary.

    

-  scrub_item_value(item)

    Takes a text item value and determines if it should be a boolean,
    integer, or text.. and returns it as the type.

    

-  epoch_to_timestr(epoch_time)

    takes a time represented as integer/string which you supply and
    converts it to a formatted string.

    :arg epoch_time: string or integer (in seconds) of epoch time

    :returns: the string version like "2016-04-14 22:05:13 -0400",
     suitable in ban files.

    

-  format_bytes(number_raw_bytes)

    Internal wrapper function that takes number of bytes
    and converts to Kbtye, MiB, GiB, etc... using 4 most
    significant digits.

    :returns: tuple - (string repr of 4 digits, string units)

    

-  getargs(arginput, i)

    returns a certain index of argument (without producting an
    error if out of range, etc).

    :Args:
        :arginput: A list of arguments.
        :i:  index of a desired argument.

    :returns:  return the 'i'th argument.  If item does not
     exist, returns ""

    

-  getargsafter(arginput, i)

    returns all arguments starting at position. (positions start
    at '0', of course.)

    :Args:
        :arginput: A list of arguments.
        :i: Starting index of argument list.

    :returns: sub list of arguments

    

-  getjsonfile(filename, directory=".", encodedas="UTF-8")

    Read a json file and return its contents as a dictionary.

    :Args:
        :filename: filename without extension.
        :directory: by default, wrapper script directory.
        :encodedas: the encoding

    :returns:
        :if successful: a dictionary
        :if unsuccessful:  None/{}
        :File/directory not found: False

    

-  getfileaslines(filename, directory=".")

    Reads a file with lines and turns it into a list containing
    those lines.

    :Args:
        :filename: Complete filename
        :directory: by default, wrapper script directory.

    :returns:
        :if successful: a list of lines in the file.
        :if unsuccessful:  None/no data
        :File/directory not found: False

    (Pycharm return definition)
    :rtype: list

    

-  mkdir_p(path)

    A simple way to recursively make a directory under any Python.

    :arg path: The desired path to create.

    :returns: Nothing - Raises Exception if it fails

    

-  get_int(s)

    returns an integer representations of a string, no matter what
    the input value.

    :arg s: Any string value.

    :returns: Applicable value (or 0 for values it can't convert)

    

-  isipv4address(addr)

    Returns a Boolean indicating if the address is a valid IPv4
    address.

    :arg addr: Address to validate.

    :returns: True or False

    

-  processcolorcodes(messagestring)

    Mostly used internally to process old-style color-codes with
    the & symbol, and returns a JSON chat object. message received
    should be string.

    upgraded to allow inserting URLS by 

    :arg messagestring: String argument with "&" codings.

    :returns: Json dumps() string.

    

-  processoldcolorcodes(message)

    Just replaces text containing the (&) ampersand with section
    signs instead (§).

    

-  putjsonfile(data, filename, directory=".", indent_spaces=2, sort=True)

    Writes entire data dictionary to a json file.

    :Args:
        :data: Dictionary to write as Json file.
        :filename: filename without extension.
        :directory: by default, current directory.
        :indent_spaces: indentation level. Pass None for no
         indents. 2 is the default.
        :sort: whether or not to sort the records for readability.

    *There is no encodedas argument: This was removed for Python3*
    *compatibility.  Python 3 has no encoding argument for json.dumps.*

    :returns:
            :True: Successful write
            :None: TypeError
            :False: File/directory not found / not accessible:

    

-  read_timestr(mc_time_string)

    The Minecraft server (or wrapper, using epoch_to_timestr) creates
    a string like this:

         "2016-04-15 16:52:15 -0400"

    This method reads out the date and returns the epoch time (well,
    really the server local time, I suppose)

    :arg mc_time_string: minecraft time string.

    :returns:
        :regular seconds from epoch: Integer
        :9999999999 symbolizing forever: For invalid data
         (like "forever").

    

-  readout(commandtext, description, separator=" - ", pad=15,
            command_text_fg="magenta", command_text_opts=("bold",),
            description_text_fg="yellow", usereadline=True)

    display console text only with no logging - useful for displaying
    pretty console-only messages.

    Args:
        :commandtext: The first text field (magenta)
        :description: third text field (green)
        :separator: second (middle) field (white text)
        :pad: minimum number of characters the command text is padded to
        :command_text_fg: Foreground color, magenta by default
        :command_text_opts: Tuple of ptions, '(bold,)' by default)
        :description_text_fg: description area foreground color
        :usereadline: Use default readline  (or 'False', use
         readchar/readkey (with anti- scroll off capabilities))

    :returns: Nothing. Just prints to stdout/console for console
     operator readout:

    :DISPLAYS:
        .. code:: python

            '[commandtext](padding->)[separator][description]'
        ..

    

-  set_item(item, string_val, filename, path='.')

    Reads a file with "item=" lines and looks for 'item'. If
    found, it replaces the existing value with 'item=string_val'.
    Otherwise, it adds the entry, creating the file if need be.

    :Args:
        :item: the config item in the file.  Will search the file
         for occurences of 'item='.
        :string_val: must have a valid __str__ representation (if
         not an actual string).
        :filename: full filename, including extension.
        :path: defaults to wrappers path.

    :returns:  Nothing.  Writes the file with single entry if
     the file is not found.  Adds the entry to end of file if
     it is missing.

    

-  chattocolorcodes(jsondata)
 Convert a chat dictionary to a string with '§_' codes
    
    :jsondata: Dictionary of minecraft chat 
    :returns: a string formatted with '§_' codes
    
    
