#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" findfunc.py
    Finds function definitions in local source files.
    This is a rewrite of findfunc.sh to better handle pygments integration.
    It currently handles Python, Javascript, Bash, Make, and C-like languages.

    The search is regex-based, and depends on function defs starting on a new
    line. No AST-parser or anything like that. It works for me to find
    "snippets" or commonly-used functions.

    -Christopher Welborn 11-15-2016
"""

import os
import re
import sys

from colr import docopt
from .tools import (
    __version__,
    colr,
    C,
    debug,
    debugprinter,
    find_func,
    find_func_in_dir,
    InvalidArg,
)


# Disable colors when piping output.
colr.auto_disable()


NAME = 'FindFunc'
VERSIONSTR = '{} v. {}'.format(NAME, __version__)
SCRIPT = 'findfunc'
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}

    Finds function definitions and Makefile targets in files.

    Usage:
        {script} -h | -v
        {script} PAT [PATH...] [-a] [--color] [-D] [-S] [-s]
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

    Any file with a name like '[Mm]akefile' will trigger makefile-mode.
    Unfortunately that mode doesn't work for stdin data.

""".format(script=SCRIPT, versionstr=VERSIONSTR)

# This can be set with -D,--debug from the command line.
DEBUG = False

# Length checks that can be used with -l,--length.
LEN_OPS = {
    '=': (lambda length, x: length == x),
    '>': (lambda length, x: length > x),
    '<': (lambda length, x: length < x),
    '>=': (lambda length, x: length >= x),
    '<=': (lambda length, x: length <= x),
}
LEN_OPS['=='] = LEN_OPS['=']


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd. """
    global DEBUG
    DEBUG = argd['--debug']
    if DEBUG:
        debugprinter.enable()
    if argd['--color']:
        colr.enable()
    if argd['--any']:
        argd['PAT'] = '(.+?{pat}|{pat}.+?)'.format(pat=argd['PAT'])
    # Using the default 'all' pattern for possible future function listing.
    userpat = try_repat(argd['PAT'], default=re.compile('.+'))
    containspat = try_repat(argd['--contains'], default=None)
    withoutpat = try_repat(argd['--without'], default=None)
    includepat = try_repat(argd['--filter'], default=None)
    excludepat = try_repat(argd['--exclude'], default=None)
    lengthfunc = parse_length_arg(argd['--length'], default=None)
    maxcount = parse_int(argd['--maxcount'], default=None)

    if not argd['PATH']:
        # Use stdin.
        argd['PATH'] = [None]

    total = 0
    try:
        for filepath in argd['PATH']:
            try:
                total += handle_path(
                    filepath,
                    userpat=userpat,
                    includepat=includepat,
                    excludepat=excludepat,
                    containspat=containspat,
                    withoutpat=withoutpat,
                    lengthfunc=lengthfunc,
                    maxcount=maxcount,
                    content_only=argd['--short'],
                    sig_only=argd['--signature'],
                )
            except MaxReached as exmax:
                total = exmax.maxcount
                break
    except KeyboardInterrupt:
        if not argd['--short']:
            print_footer(total)
        raise

    exitcode = 0 if total > 0 else 1
    if argd['--short']:
        return exitcode
    return print_footer(total, maxcount=maxcount)


def debug_args(argd, **kwargs):
    """ Debug current argd settings, raw and parsed.
        Arguments:
            argd : Dict containing user's raw arguments parsed by docopt.

        Keyword Arguments:
            Name, ArgInfo pairs in the form of:
                varname={'flag': '--flag', 'parsed': parsed_value}
    """
    debug('Arguments:')
    for name, info in kwargs.items():
        debug(
            '{:<12} ({:<12}) = {!r}'.format(
                name,
                info['flag'],
                info.get('parsed', argd[info['flag']]),
            ),
            align=True,
        )


def handle_path(
        filepath, *,
        userpat=None, includepat=None, excludepat=None,
        containspat=None, withoutpat=None,
        lengthfunc=None, maxcount=None,
        content_only=False, sig_only=False,
        _total=0):
    """ Handle a single path argument from the user. """
    if filepath and os.path.isdir(filepath):
        funcfinder = find_func_in_dir
    else:
        funcfinder = find_func
    for funcdef in funcfinder(
            filepath,
            userpat,
            include_pattern=includepat,
            exclude_pattern=excludepat):
        # Test content?
        if (
                (containspat is not None) and
                (not funcdef.contains(containspat))):
            debug('Skipping non-match: {}'.format(funcdef.signature))
            continue
        if (
                (withoutpat is not None) and
                funcdef.contains(withoutpat)):
            debug('Skipping match: {}'.format(funcdef.signature))
            continue
        # Test length?
        if (
                (lengthfunc is not None) and
                (not lengthfunc(len(funcdef)))):
            debug('Skipping non-length match: {}'.format(
                funcdef.signature
            ))
            continue
        # Passed the gauntlet.
        _total += 1
        print(
            funcdef.highlighted(
                content_only=content_only,
                sig_only=sig_only,
            )
        )
        if maxcount and _total == maxcount:
            debug('Stopping at max count: {}'.format(maxcount))
            raise MaxReached(maxcount)
    return _total


def make_length_op(func, length):
    """ Make a function that tests length equality, for --length. """
    def test_def_length(deflength):
        return func(deflength, length)
    return test_def_length


def parse_int(s, default=None):
    """ Parse a string as an integer, returns `default` for falsey value.
        Raises InvalidArg with a message on invalid numbers.
    """
    if not s:
        # None, or less than 1.
        return default
    try:
        val = int(s)
    except ValueError:
        raise InvalidArg('invalid number: {}'.format(s))
    return val


def parse_length_arg(s, default=None):
    """ Parse the user's --length operation arg, turning it into a function.
        The functions can then be used like:
            lengthfunc = parse_length_arg('>5')
            if lengthfunc(len(functiondef)):
                print('FunctionDef has more than 5 lines.')
        Returns the function on success.
        Raises InvalidArg on bad integers/test-syntax.
    """
    if not s:
        return default

    for opstr in LEN_OPS:
        if s.startswith(opstr):
            func = LEN_OPS[opstr]
            s = s[len(opstr):]
            break
    else:
        # No function provided, use =.
        func = LEN_OPS['=']

    try:
        intval = int(s)
    except ValueError:
        raise InvalidArg(
            '\n'.join((
                'Invalid --length operation: {}',
                'Expecting an integer or >N,<N,>=N,<=N,=N,==N.'
            )).format(s)
        )
    return make_length_op(func, intval)


def print_err(*args, **kwargs):
    """ A wrapper for print() that uses stderr by default. """
    if kwargs.get('file', None) is None:
        kwargs['file'] = sys.stderr
    print(
        C(kwargs.get('sep', ' ').join(str(a) for a in args), fore='red'),
        **kwargs
    )


def print_footer(total, maxcount=None):
    """ Print the 'Found X functions' message, return an exit status code. """
    msg = C(str(total), fore='blue', style='bold').join(
        C('\nFound ', fore='cyan'),
        C(
            ' definition.' if total == 1 else ' definitions.',
            fore='cyan'
        )
    )
    if total == maxcount:
        msg = C(' ').join(
            msg,
            C('Max count was satisfied.', fore='cyan'),
        )
    print(msg)
    return 0 if total > 0 else 1


def try_repat(s, default=None):
    """ Try compiling a regex pattern.
        If `s` is Falsey, `default` is returned.
        On errors, InvalidArg is raised.
        On success, a compiled regex pattern is returned.
    """
    if not s:
        return default
    try:
        p = re.compile(s)
    except re.error as ex:
        raise InvalidArg('Invalid pattern: {}\n{}'.format(s, ex))
    return p


def entry_point():
    """ Main entry point for setuptools.
        Handles module-level exceptions, and exiting with the correct
        status code.
    """
    try:
        mainret = main(docopt(USAGESTR, version=VERSIONSTR, script=SCRIPT))
    except (InvalidArg, EnvironmentError) as ex:
        print_err(ex)
        mainret = 1
    except (EOFError, KeyboardInterrupt):
        print_err('\nUser cancelled.\n')
        mainret = 2
    except BrokenPipeError:
        print_err('\nBroken pipe, input/output was interrupted.\n')
        mainret = 3
    sys.exit(mainret)


class MaxReached(ValueError):
    def __init__(self, maxcount):
        self.maxcount = maxcount or 0

    def __str__(self):
        return 'Maximum count reached: {}'.format(self.maxcount)


if __name__ == '__main__':
    entry_point()
