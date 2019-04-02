FindFunc
========

Finds and prints function definitions/signatures in source code files.
It currently handles JavaScript, Shell, Python (classes too, since
they're just functions anyway :smile:), and C-style function
definitions, as well as Makefile targets. It will highlight the body of
the functions for readability.

Dependencies
------------

These are installable with ``pip``:

+--------------------------------------------------------------+------------------------------------------+
| Name                                                         | Description                              |
+==============================================================+==========================================+
| `colr <https://github.com/welbornprod/colr>`__               | Terminal colors.                         |
+--------------------------------------------------------------+------------------------------------------+
| `docopt <https://github.com/docopt/docopt>`__                | Command line argument parsing.           |
+--------------------------------------------------------------+------------------------------------------+
| `printdebug <https://github.com/welbornprod/printdebug>`__   | Debug printing for command line tools.   |
+--------------------------------------------------------------+------------------------------------------+
| `pygments <http://pygments.org>`__                           | Source code highlighting.                |
+--------------------------------------------------------------+------------------------------------------+

Installation:
-------------

This package is listed on PyPi, and is installable with ``pip``:

.. code:: bash

    pip install findfunc

Usage
-----

::

        Usage:
            findfunc -h | -v
            findfunc PAT -p [-a] [--color] [-D] [-S] [-s]
                     [-c pat] [-C pat] [-e pat] [-f pat] [-l num] [-m num]
            findfunc PAT [PATH...] [-a] [--color] [-D] [-S] [-s]
                     [-c pat] [-C pat] [-e pat] [-f pat] [-l num] [-m num]

        Options:
            PATH                   : Zero or more file paths to search.
                                     If the path is a directory it will be walked.
                                     Default: stdin
            PAT                    : Function name or regex pattern to search for.
            -a,--any               : Matches anywhere in the name.
                                     This is the same as: (.+?pattern|pattern.+?)
            --color                : Always use color.
            -c pat,--contains pat  : Only show definitions that contain this
                                     pattern in the body.
            -C pat,--without pat   : Only show definitions that do not contain
                                     this pattern in the body.
                                     This cancels out any -c pattern.
            -D,--debug             : Print some debugging info while running.
            -e pat,--exclude pat   : Regex pattern to exclude file paths.
            -f pat,--filter pat    : Regex pattern to include file paths.
            -h,--help              : Show this help message.
            -l num,--length num    : Show definitions that match this line length.
                                     Tests can be prepended:
                                         >N  : More than N lines.
                                         <N  : Less than N lines.
                                        >=N  : More than or equal to N lines.
                                        <=N  : Less than or equal to N lines.
                                         =N  : Exactly N lines.
                                        ==N  : Exactly N lines.
                                          N  : Exactly N lines.
            -m num,--maxcount num  : Maximum number of definitions to show.
            -p,--paths             : Search all directories found in the config
                                     file.
            -S,--signature         : Just print the signatures found.
            -s,--short             : Use shorter output mode.
            -v,--version           : Show version.

        Any file with a name like '[Mm]akefile' will trigger makefile-mode.
        Unfortunately that mode doesn't work for stdin data.

        JSON config can be loaded from: ~/findfunc.json

Demo
----

Here is a recording showing FindFunc's output when ran multiple times
for various file types:

|asciicast|

Instead of typing each command, I made a script to do it for me. So it
may seem a little fast. It's running ``findfunc PATTERN DIR_OR_FILE``
with or without a ``--maxcount`` or ``--signature`` flag set.

Config
------

Config is a JSON file that can be loaded from ``CWD``,
``~/findfunc.json``, or ``~/.local/share/findfunc.json``.

It's format is:

.. code:: json

    {
        "default_paths": ["my_dir1", "my_file1", "/home/me/scripts"]
    }

``default_paths`` is a list of directory or file paths to search when
the ``-p`` flag is given.

.. |asciicast| image:: https://asciinema.org/a/112297.png
   :target: https://asciinema.org/a/112297
