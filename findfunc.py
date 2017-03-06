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

from colr import (
    auto_disable as colr_auto_disable,
    disabled as colr_disabled,
    docopt,
    Colr as C,
)
from printdebug import DebugColrPrinter

from pygments.formatters import Terminal256Formatter
from pygments import highlight
from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    guess_lexer,
)
from pygments.util import ClassNotFound

# Disable colors when piping output.
colr_auto_disable()

debugprinter = DebugColrPrinter()
debugprinter.disable()
debug = debugprinter.debug

NAME = 'FindFunc'
VERSION = '0.4.0'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}

    Finds function definitions and Makefile targets in files.

    Usage:
        {script} -h | -v
        {script} [-D] [-a] PAT [PATH...] [-S] [-s]
                 [-c pat] [-C pat] [-e pat] [-f pat] [-l num]

    Options:
        PATH                   : Zero or more file paths to search.
                                 If the path is a directory it will be walked.
                                 Default: stdin
        PAT                    : Function name or regex pattern to search for.
        -a,--any               : Matches anywhere in the name.
                                 This is the same as: (.+?pattern|pattern.+?)
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

        -S,--signature         : Just print the signatures found.
        -s,--short             : Use shorter output mode.
        -v,--version           : Show version.

    Any file with a name like '[Mm]akefile' will trigger makefile-mode.
    Unfortunately that mode doesn't work for stdin data.

""".format(script=SCRIPT, versionstr=VERSIONSTR)

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

    if argd['--any']:
        argd['PAT'] = '(.+?{pat}|{pat}.+?)'.format(pat=argd['PAT'])
    # Using the default 'all' pattern for possible future function listing.
    userpat = try_repat(argd['PAT'], default=re.compile('.+'))
    containspat = try_repat(argd['--contains'], default=None)
    withoutpat = try_repat(argd['--without'], default=None)
    includepat = try_repat(argd['--filter'], default=None)
    excludepat = try_repat(argd['--exclude'], default=None)
    lengthfunc = parse_length_arg(argd['--length'], default=None)
    if not argd['PATH']:
        # Use stdin.
        argd['PATH'] = [None]

    total = 0
    try:
        for filepath in argd['PATH']:
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
                total += 1
                print(
                    funcdef.highlighted(
                        content_only=argd['--short'],
                        sig_only=argd['--signature'],
                    )
                )
    except KeyboardInterrupt:
        if not argd['--short']:
            print_footer(total)
        raise

    exitcode = 0 if total > 0 else 1
    return exitcode if argd['--short'] else print_footer(total)


def find_func(filename, pattern, include_pattern=None, exclude_pattern=None):
    """ Yields lines from a file that seem to be a matching function def.
        Arguments:
            filename         : File name to read and search.
            pattern          : Precompiled regex pattern for function def.
            include_pattern  : Precompiled regex, only include matching names.
            exclude_pattern  : Precompiled regex, exclude matching names.
    """
    if filename:
        skip_file = (
            (include_pattern is not None) and
            (include_pattern.search(filename) is None)
        ) or (
            (exclude_pattern is not None) and
            (exclude_pattern.search(filename) is not None)
        )
        if skip_file:
            debug('Skipping filtered file: {}'.format(filename))
        else:
            debug('Opening file: {}'.format(filename))
            try:
                with open(filename, 'r') as f:
                    yield from find_func_in_file(f, pattern)
            except UnicodeDecodeError as ex:
                debug('Skipping file: {}'.format(filename))
                debug('Message: {}'.format(ex), align=True)
    else:
        debug('Reading from: stdin')
        if sys.stdout.isatty() and sys.stdin.isatty():
            print('\nReading from stdin until EOF (Ctrl + D)...\n')
        yield from find_func_in_file(sys.stdin, pattern)


def find_func_in_dir(
        dirpath, pattern, include_pattern=None, exclude_pattern=None):
    """ Uses find_func() on all files in a directory. """
    for root, dirs, files in os.walk(dirpath):
        for filename in files:
            filepath = os.path.join(root, filename)
            yield from find_func(
                filepath,
                pattern,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
            )


def find_func_in_file(f, pattern):
    """ Yields FunctionDefs from an open file object that seem to be
        a matching function def.
        Arguments:
            f            : File object to read.
            pattern      : Precompiled regex pattern for function def.
    """
    if f.name.lower() == 'makefile':
        startpat = STARTMAKETARGETPAT
        pattern = get_make_target_pattern(pattern, ignore_case=True)
    else:
        startpat = STARTPAT
        pattern = get_func_pattern(pattern, ignore_case=True)
    funcdef = None
    lineno = 0
    for line in f:
        lineno += 1
        line = line.rstrip()
        if not funcdef:
            if pattern.search(line) is not None:
                # Start of matching function.
                debug('Found start of def: {!r}'.format(line))
                funcdef = FunctionDef(
                    f.name,
                    first_line=line,
                    lineno=lineno,
                )
            else:
                # Not a start, not in the body.
                continue
        elif funcdef:
            child_indent = (
                len(FunctionDef.get_indent(line)) > len(funcdef.indent)
            )
            if (startpat.search(line) is not None) and (not child_indent):
                # Start of another function def.
                debug('Found start of another def: {!r}'.format(line))
                yield funcdef
                if pattern.search(line) is not None:
                    # ...that matches the user's pattern.
                    funcdef = FunctionDef(
                        f.name,
                        first_line=line,
                        lineno=lineno,
                    )
                    continue
                else:
                    funcdef = None
                    continue
            elif (
                    line and
                    (not line.startswith((' ', '\t')))):
                # End if func def? There's a new line with no indention.
                if funcdef.signature.endswith('{'):
                    # Must find a closing brace to be the end.
                    if line.startswith('}'):
                        debug('Found end of braced def: {!r}'.format(line))
                        funcdef.add_line(line)
                        yield funcdef
                        funcdef = None
                        continue
                else:
                    # Special-case, starting brace on newline.
                    if line == '{' and (funcdef is not None):
                        funcdef.append_signature(' {')
                        continue
                    # Not a brace-style function def.
                    debug('Found end of non-braced def: {!r}'.format(line))
                    yield funcdef
                    funcdef = None
                    continue
            if funcdef:
                # Inside the body, haven't found the end.
                funcdef.add_line(line)

    if funcdef:
        yield funcdef


def get_func_begin_pattern():
    """ Build a regex that will match the beginning of any function def.
    """
    return get_func_pattern(re.compile(r'[\w\d_]+'))


def get_func_pattern(pattern, ignore_case=True):
    """ Build a regex that will find function defs based on the user's
        pattern.
        Arguments:
            pattern  : A precompiled regex pattern.
    """
    userpat = pattern.pattern
    if not (userpat.startswith('(') and userpat.endswith(')')):
        userpat = '({})'.format(userpat)
    pats = (
        # Javascript patterns
        r'(var {userpattern} ?\=)',
        r'(function {userpattern} ?\()',
        # Python patterns.
        r'(def {userpattern} ?\()',
        r'(([ \t]+)def {userpattern} ?\()',
        r'({userpattern} ?= ? lambda)',
        # Python class pattern.
        r'(class {userpattern} ?\()',
        # Shell patterns.
        r'(function {userpattern} ?\{{)',
        r'({userpattern}\(\) ?\{{)',
        # Basic C patterns.
        r'(\w{{3,16}} {userpattern} ?\(([^\)]+)?\) ? \{{)',
    )
    finalpat = '^({})'.format('|'.join(pats)).format(userpattern=userpat)
    debug('Compiling pattern: {}'.format(finalpat))
    return re.compile(
        finalpat,
        flags=re.IGNORECASE if ignore_case else 0,
    )


def get_make_target_begin_pattern():
    """ Build a regex that will match the beginning of any make target.
    """
    return get_make_target_pattern(re.compile(r'[\w\d_]+'))


def get_make_target_pattern(pattern, ignore_case=True):
    """ Build a regex that will find make targets based on the user's
        pattern.
        Arguments:
            pattern  : A precompiled regex pattern.
    """
    userpat = pattern.pattern
    if not (userpat.startswith('(') and userpat.endswith(')')):
        userpat = '({})'.format(userpat)

    finalpat = '^{userpattern}:'.format(userpattern=userpat)
    debug('Compiling make target pattern: {}'.format(finalpat))
    return re.compile(
        finalpat,
        flags=re.IGNORECASE if ignore_case else 0,
    )


def make_length_op(func, length):
    """ Make a function that tests length equality, for --length. """
    def test_def_length(deflength):
        return func(deflength, length)
    return test_def_length


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


def print_footer(total):
    """ Print the 'Found X functions' message, return an exit status code. """
    print(C(str(total), fore='blue', style='bold').join(
        C('\nFound ', fore='cyan'),
        C(
            ' definition.' if total == 1 else ' definitions.',
            fore='cyan'
        )
    ))
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


class FunctionDef(object):
    """ Holds info and helper methods for a single function definition. """
    def __init__(self, filename, first_line=None, lineno=None):
        self.filename = filename
        self.lines = []
        self.lineno = lineno or 0
        # These are set on the first add_line(), which should be the def.
        self.signature = None
        self.indent = ''
        self.indent_len = 0

        if first_line:
            self.add_line(first_line)

    def __bool__(self):
        """ FunctionDefs are truthy if it's lines are truthy (non-empty). """
        return bool(self.lines)

    def __len__(self):
        """ A FunctionDef's length is the length of it's lines. """
        return len(self.lines)

    def __str__(self):
        """ Non-highlighted/colorized formatting. """
        return self.to_str()

    def add_line(self, line):
        """ Add a line to the body of this function def.
            If this is the first line, it is considered the signature.
        """
        line = self.fix_whitespace(line)
        if not self.lines:
            self.signature = line
            self.indent = self.get_indent(self.signature)
            self.indent_len = len(self.indent)
        # Remove one level of indention and trailing newlines.
        line = line.rstrip()[self.indent_len:]
        self.lines.append(line)

    def append_signature(self, text):
        """ Append something to the signature (first line) of this function
            def, like a brace that was on the next line.
        """
        if not self.lines:
            raise ValueError('No signature set yet.')
        self.lines[0] = ''.join((self.lines[0], text))
        self.signature = self.lines[0]
        return None

    def contains(self, pattern):
        """ Return True if this FuncDef's body contains the regex `pattern`.
        """
        if isinstance(pattern, str) or (not hasattr(pattern, 'pattern')):
            # str?
            try:
                trypattern = re.compile(str(pattern))
            except re.error as ex:
                raise InvalidArg(
                    'Bad pattern for FuncDef.contains: {}\n{}'.format(
                        pattern,
                        ex
                    ))
            else:
                pattern = trypattern

        for line in self.lines:
            if pattern.search(line) is not None:
                return True
        return False

    def get_content(self, indent=4):
        """ Return only the content for this function def, no file name.
            Arguments:
                indent  : Number of spaces to prepend to each line.
                          Default: 4
        """
        spaces = ' ' * (indent or 0)
        # Make a copy so that the original is untouched.
        lines = self.lines[:]
        lines[0] = '{}{}'.format(spaces, lines[0])
        return '\n{}'.format(spaces).join(lines)

    @staticmethod
    def fix_whitespace(line, cnt=4):
        """ Replace all tabs with spaces (4 by default). """
        tabs = 0
        while line.startswith('\t'):
            tabs += 1
            line = line[1:]
        spaces = ' ' * cnt
        return ''.join((spaces * tabs, line))

    def get_filename(self):
        """ Returns self.filename if set, otherwise 'stdin'. """
        if self.is_stdin():
            return 'stdin'
        return self.filename

    @staticmethod
    def get_indent(line):
        """ Return only the leading whitespace from a line. """
        indent = []
        while line.startswith((' ', '\t')):
            indent.append(line[0])
            line = line[1:]
        return ''.join(indent)

    def get_lexer(self):
        """ Return the proper lexer for this function def.
            If no filename is set, try guessing by content.
            If all else fails, just return the text lexer.
        """
        try:
            if self.is_stdin():
                debug('Guessing lexer...')
                lexer = guess_lexer(str(self))
            else:
                debug('Getting lexer from filename: {}'.format(self.filename))
                lexer = get_lexer_for_filename(self.filename)
        except ClassNotFound:
            debug('Failed to get lexer, using the default.')
            lexer = get_lexer_by_name('text')
        lexername = lexer.aliases[0] if lexer.aliases else lexer.name
        debug('Using lexer: {}'.format(lexername))
        return lexer

    def highlighted(self, style=None, content_only=False, sig_only=False):
        """ Return self.lines, highlighted with pygments.
            The lexer is based on self.filename.
        """
        if colr_disabled():
            # No colors.
            return self.to_str(content_only=content_only, sig_only=sig_only)

        linecntfmt = C(': ', style='bright').join(
            C('lines', fore='cyan'),
            C(len(self), fore='blue'),
        ).join('(', ')', style='bright')

        sig_fmted = (
            '\n{filename} {pnd}{lineno} {linecntinfo}:'.format(
                filename=C(self.get_filename(), fore='lightblue'),
                pnd=C('#', fore='lightblue'),
                lineno=C(self.lineno, fore='blue', style='bright'),
                linecntinfo=linecntfmt,
            )
        )

        if sig_only:
            sig_line = C(self.signature, fore='yellow')
            if content_only:
                return str(sig_line)
            return '{}\n    {}'.format(sig_fmted, sig_line)

        style = (style or 'monokai').lower().strip() or 'monokai'
        lexer = self.get_lexer()
        try:
            fmter = Terminal256Formatter(style=style.lower())
        except ClassNotFound:
            raise InvalidArg('Invalid style name: {}'.format(style))
        debug('Highlighting lines: {}, Total: {}'.format(
            self.get_filename(),
            len(self),
        ))
        if content_only:
            return highlight(
                self.get_content(indent=0),
                lexer,
                fmter
            ).rstrip()

        return '\n'.join((
            sig_fmted,
            highlight(self.get_content(), lexer, fmter).rstrip(),
        ))

    def is_stdin(self):
        """ Return True if no filename is set, or it is a stdin marker. """
        return self.filename in (None, '<stdin>', '-', 'stdin')

    def to_str(self, content_only=False, sig_only=False):
        """ Plain string, no color, with optional filename/name. """
        if content_only:
            return self.get_content(indent=0)
        sig_fmted = '\n{filename} #{lineno} (lines: {linecnt}):'.format(
            filename=self.get_filename(),
            lineno=self.lineno,
            linecnt=len(self),
        )
        if sig_only:
            if content_only:
                return str(self.signature)
            return '{}\n    {}'.format(sig_fmted, self.signature)

        return '{}\n{}'.format(
            sig_fmted,
            self.get_content(indent=4),
        )


class InvalidArg(ValueError):
    """ Raised when the user has used an invalid argument. """
    def __init__(self, msg=None):
        self.msg = msg or ''

    def __str__(self):
        if self.msg:
            return str(self.msg)
        return 'Invalid argument!'


# Pre-build the pattern for finding the beginning of any function def.
# This beginning is also usually the end of the def we were looking at.
STARTPAT = get_func_begin_pattern()
STARTMAKETARGETPAT = get_make_target_begin_pattern()

if __name__ == '__main__':
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
