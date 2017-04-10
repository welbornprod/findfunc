# FindFunc

Finds and prints function definitions/signatures in source code files.
It currently handles
JavaScript,
Shell,
Python (classes too, since they're just functions anyway :smile:),
and C-style
function definitions,
as well as Makefile targets. It will highlight the body of the functions for
readability.

## Dependencies

These are installable with `pip`:

Name | Description
---|---
[colr](https://github.com/welbornprod/colr)|Terminal colors.
[docopt](https://github.com/docopt/docopt)|Command line argument parsing.
[printdebug](https://github.com/welbornprod/printdebug)|Debug printing for command line tools.
[pygments](http://pygments.org)|Source code highlighting.

## Installation:

This package is listed on PyPi, and is installable with `pip`:
```bash
pip install findfunc
```

## Usage
```
Usage:
    findfunc -h | -v
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
    -S,--signature         : Just print the signatures found.
    -s,--short             : Use shorter output mode.
    -v,--version           : Show version.
```

## Demo

Here is a recording showing FindFunc's output when ran multiple times for
various file types:

[![asciicast](https://asciinema.org/a/112297.png)](https://asciinema.org/a/112297)

Instead of typing each command, I made a script to do it for me. So it may
seem a little fast. It's running `findfunc PATTERN DIR_OR_FILE` with or
without a `--maxcount` or `--signature` flag set.
