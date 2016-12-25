
**def config_to_dict_read(filename, filepath)**

    reads a disk file with '=' lines (like server.properties) and returns a keyed dictionary.
    

**def scrub_item_value(item)**

    Takes a text item value and determines if it should be a boolean, integer, or text.. and returns it as the type.
    

**def epoch_to_timestr(epoch_time)**

    takes a time represented as integer/string which you supply and converts it to a formatted string.

    :epoch_time: string or integer (in seconds) of epoch time

    :returns: the string version like "2016-04-14 22:05:13 -0400", suitable in ban files.

    

**def format_bytes(number_raw_bytes)**

    takes a raw bytes number and returns an appropriate 4 place digit number > 1.0 and the corresponding units.
    

**def getargs(arginput, i)**

    returns a certain index of argument (without producting an error if our of range, etc).

    :arginput: A list of arguments.

    :i:  index of a desired argument

    :return:  return the 'i'th argument.  if item does not exist, returns ""

    

**def getargsafter(arginput, i)**

    returns all arguments starting at position. (positions start at '0', of course.)

    :arginput: A list of arguments.

    :i: Starting index of argument list

    :return: sub list of arguments

    

**def getjsonfile(filename, directory=".", encodedas="UTF-8")**

    Read a json file and return its contents as a dictionary.

    :filename: filename without extension

    :directory: by default, wrapper script directory.

    :encodedas: the encoding

    Returns: a dictionary if successful. If unsuccessful; None/no data or False (if file/directory not found)

    

**def getfileaslines(filename, directory=".")**

    Reads a file with lines and turns it into a list containing those lines.

    :filename: Complete filename

    :directory: by default, wrapper script directory.

    :rtype: list

    returns a list of lines in the file if successful.

        If unsuccessful; None/no data or False (if file/directory not found)

    

**def mkdir_p(path)**

    A simple way to recursively make a directory under any Python.

    :path: The desired path to create.

    :returns: Nothing - Raises exception if it fails

    

**def get_int(s)**

    returns an integer representations of a string, no matter what the input value.
    returns 0 for values it can't convert

    :s: Any string value.

    

**def isipv4address(addr)**

    Returns a Boolean indicating if the address is a valid IPv4 address.

    :addr: Address to validate.

    :return: True or False

    

**def processcolorcodes(messagestring)**

    Mostly used internally to process old-style color-codes with the & symbol, and returns a JSON chat object.
    message received should be string
    

**def processoldcolorcodes(message)**

    Just replaces text containing the (&) ampersand with section signs instead (§).
    

**def putjsonfile(data, filename, directory=".", indent_spaces=2, sort=False, encodedas="UTF-8")**

    writes entire data to a json file.
    This is not for appending items to an existing file!

    :data: json dictionary to write

    :filename: filename without extension.

    :directory: by default, wrapper script directory.

    :indent_spaces: indentation level. Pass None for no indents. 2 is the default.

    :sort: whether or not to sort the records for readability.

    :encodedas: encoding

    :returns: True if successful.

        If unsuccessful;
         None = TypeError,

         False = file/directory not found/accessible

    

**def read_timestr(mc_time_string)**

    The Minecraft server (or wrapper, using epoch_to_timestr) creates a string like this:

         "2016-04-15 16:52:15 -0400"

         This method reads out the date and returns the epoch time (well, really the server local time, I suppose)

    :mc_time_string: minecraft time string.

    :returns: regular seconds from epoch (integer).
            Invalid data (like "forever"), returns 9999999999 (what forever is).

    

**def set_item(item, string_val, filename, path='.')**

    Reads a file with "item=" lines and looks for 'item'.

    If found, it replaces the existing value
    with 'item=string_val'.

    :item: the config item in the file.  Will search the file for occurences of 'item='.

    :string_val: must have a valid __str__ representation (if not an actual string).

    :filename: full filename, including extension.

    :path: defaults to wrappers path.

    :returns:  Boolean indication of success or failure.

    
