# FindFunc

Like `grep`, except it will find and print functions in source code files. It
currently handles
JavaScript,
Shell,
Python (classes too, since they're just functions anyway :smile:),
and C-style
function definitions,
as well as Makefile targets.


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
