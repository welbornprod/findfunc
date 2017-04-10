import os
import re
import sys
from io import TextIOBase

import colr
from printdebug import DebugColrPrinter

from pygments.formatters import Terminal256Formatter
from pygments import highlight
from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    guess_lexer,
)
from pygments.util import ClassNotFound

__version__ = '0.4.3'

C = colr.Colr
debugprinter = DebugColrPrinter()
debugprinter.disable()
debug = debugprinter.debug


def find_func(filename, pattern, include_pattern=None, exclude_pattern=None):
    """ Yields lines from a file that seem to be a matching function def.
        Arguments:
            filename         : File name to read and search.
            pattern          : Precompiled regex pattern for function def.
            include_pattern  : Precompiled regex, only include matching names.
            exclude_pattern  : Precompiled regex, exclude matching names.
    """
    if filename is not None:
        # File path for an already opened file?
        filepath = getattr(filename, 'name', filename)
        skip_file = (
            (include_pattern is not None) and
            (include_pattern.search(filepath) is None)
        ) or (
            (exclude_pattern is not None) and
            (exclude_pattern.search(filepath) is not None)
        )
        if skip_file:
            debug('Skipping filtered file: {}'.format(filepath))
        else:
            try:
                if isinstance(filename, TextIOBase):
                    # An already open file.
                    yield from find_func_in_file(filename, pattern)
                else:
                    with open(filepath, 'r') as f:
                        yield from find_func_in_file(f, pattern)
            except UnicodeDecodeError as ex:
                debug('Skipping file: {}'.format(filepath))
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
    filename = os.path.split(f.name)[-1]
    if filename.lower() == 'makefile':
        debug('Using makefile mode.')
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
    # Try retrieving cached version.
    cached = get_func_pattern.patterns.get(userpat, None)
    if cached is not None:
        return cached

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
        r'((\w{{3,16}} )?{userpattern} ?\(([^\)]+)?\) ? \{{)',
    )
    finalpat = '^({})'.format('|'.join(pats)).format(userpattern=userpat)
    debug('Compiling pattern: {}'.format(finalpat))
    repat = re.compile(
        finalpat,
        flags=re.IGNORECASE if ignore_case else 0,
    )
    # Cache this pattern for future calls to this function.
    get_func_pattern.patterns[userpat] = repat
    return repat


# This function remembers the patterns that it compiles.
get_func_pattern.patterns = {}


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

    # Try retrieving cached version.
    cached = get_make_target_pattern.patterns.get(userpat, None)
    if cached is not None:
        return cached

    finalpat = '^{userpattern}:'.format(userpattern=userpat)
    debug('Compiling make target pattern: {}'.format(finalpat))
    repat = re.compile(
        finalpat,
        flags=re.IGNORECASE if ignore_case else 0,
    )
    get_make_target_pattern.patterns[userpat] = repat
    return repat


# This function remembers the patterns that it compiles.
get_make_target_pattern.patterns = {}

# Pre-build the pattern for finding the beginning of any function def.
# This beginning is also usually the end of the def we were looking at.
STARTPAT = get_func_begin_pattern()
STARTMAKETARGETPAT = get_make_target_begin_pattern()


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
        if colr.disabled():
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

        style = (style or 'monokai').lower().strip() or 'monokai'
        lexer = self.get_lexer()
        try:
            fmter = Terminal256Formatter(style=style.lower())
        except ClassNotFound:
            raise InvalidArg('Invalid style name: {}'.format(style))
        if sig_only:
            # Fix braced signatures for C-style files.
            signature = self.signature.rstrip('{').rstrip()
            sig_line = highlight(signature, lexer, fmter).rstrip()
            if content_only:
                return str(sig_line)
            return '{}\n    {}'.format(sig_fmted, sig_line)

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
