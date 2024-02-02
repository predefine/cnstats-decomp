#!/usr/bin/python
'''
    phplint.py - Copyright (C) 2014 Daniel Fairhead
    -------------------------------------
    a simple php linter/formatter in python.
    WORK IN PROGRESS.
    -------------------------------------
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
# I know how to use * and **
# pylint: disable=W0142 

from __future__ import print_function
import sys
from functions_map import fm, vm

# this could/should be expanded to full UTF-8 capacity:

VALID_LETTERS = 'abcdefghijklmnopqrstuvwxyz' \
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                '1234567890_'

OPERATORS = ['.', '+', '-', '*', '/', '&', '^', '%', '|', '?', ':', '=', '<' , '>', '++', '--',
             '.=', '+=', '-=', '*=', '/=', '&&', '||', '==', '=>', '->',
             '::', '!=', '<<', '>>', '<=', '>=', '===', '!=='][::-1]

KEYWORD_BLOCK_THINGS = ['if' ,'do', 'for', 'else', 'while', 'elseif', 'switch', 'foreach', 'else if']

# TODO: also class, and function.

class ParseError(Exception):
    ''' Generic Error '''
    pass

class UnexpectedEndOfFile(ParseError):
    ''' End of file, but it should not be! '''
    pass

class PHPError(ParseError):
    ''' Invalid PHP, for some reason. '''
    pass

class RollBack(Exception):
    ''' this parse-attempt isn't working.
    Please roll back to whereever you were. '''
    pass

###############################################################3


class Parser(object):
    ''' a generic parser object. '''

    line_no = 1
    chr_no = 0
    text = ''
    position = 0
    text_length = 0
    current_indent = ''
    expected_indent_level = 0
    k_and_r_braces = True
    indentation = '    '

    def __init__(self, warn=True, clean=True):
        ''' constructor '''

        self.display_warnings = warn
        self.cleanup = clean
        self.variables = []
        self.words = []

    def step_back(self, count=1):
        ''' go back <count> characters '''
        self.position -= count
        self.chr_no -= count

    def step_forward(self, count=1):
        ''' continue <count> number of characters '''

        for _ in range(count):
            if self.position < self.text_length:
                self.position += 1

            if self.next_chr_is('\n'):
                self.line_no += 1
                self.chr_no = 0
            else:
                self.chr_no += 1


    def next_chr_is(self, char):
        ''' test if the next character to be parsed is char '''
        try:
            return self.text[self.position] == char
        except IndexError:
            return False

    def next_chr_in(self, chars):
        ''' test if the next character is any of these characters '''

        cur = self.text[self.position]
        return cur in chars

    def next_starts(self, *texts):
        ''' test if the next text to be read starts with this text,
            and return it'''
        for text in texts:
            if self.text[self.position:].startswith(text):
                return text
        return False

    def next_word_in(self, *words):
        word = self.next_starts(*words)
        if word and self.text[self.position + len(word)] not in VALID_LETTERS:
            return word

        return False
            

    def _not_at_end(self):
        ''' used by parsing functions internally to continue one character
            at a time, and call the 'step_forward' function. '''

        if self.position < self.text_length - 1:
            self.step_forward()
            return True
        else:
            return False

    def warn(self, text, level=5):
        ''' display a warning message (usually to stderr) '''
        if self.display_warnings:
            print ("Warning(%i) [%i:%i]:  %s" % (level, self.line_no,
                                                 self.chr_no, text),
                                                 file=sys.stderr)

    def rollback(self, output):
        ''' return a 'with block' object which can be used to roll back from
            attempted parsing. If a parse attempt fails, you should
            raise RollBack. '''
        output_len = len(output)
        position = self.position
        line_no = self.line_no
        chr_no = self.chr_no

        parser = self
        output_list = output

        class Roller(object):
            ''' withblock object, which closes over the initial starting
                position, so it can roll back to that if a RollBack is raised.
            '''
            def __enter__(self):
                ''' start rollback block '''
                pass
            def __exit__(self, excptype, value, traceback):
                ''' exit rollback block.  if a RollBack exception has been
                    raised, roll back, and continue '''
                if excptype == RollBack:
                    while len(output_list) > output_len:
                        output_list.pop()
                    parser.position = position
                    parser.line_no = line_no
                    parser.chr_no = chr_no
                    return True

        return Roller()


class PHPParser(Parser):  # pylint: disable=R0904
    ''' a PHP specific Parser object '''

    def string_literal(self):
        ''' read a string literal 'like this' or "like this", return it. '''

        initial_quote_mark = self.text[self.position]
        start_position = self.position

        while self._not_at_end():
            if self.next_chr_is('\\'):
                self.step_forward()
            elif self.next_chr_is(initial_quote_mark):
                return self.text[start_position:self.position + 1]

        raise UnexpectedEndOfFile('end of file inside string literal!')

    def multiline_comment(self):
        ''' read from /* to */ '''

        start = self.position

        while self._not_at_end():
            if self.next_starts('*/'):
                self.step_forward()
                return self.text[start:self.position + 1]

        raise UnexpectedEndOfFile('end of file inside /* multi-line comment */')

    def inline_comment(self):
        ''' from // to the end of line. '''

        start = self.position

        while self._not_at_end():
            if self.next_chr_is('\n'):
                self.step_back()
                break
        return self.text[start:self.position + 1]

    def expression(self):  # pylint: disable=R0912
        ''' a section of code (inside brackets). nestable / recursive. '''
        output = ['(']

        # set indentation level to where this expression opens.
        if self.cleanup:
            previous_indent = self.current_indent
            previous_indentaton = self.indentation
            self.current_indent = self.chr_no * ' '
            self.indentation = ''

        if self.cleanup:
            # remove initial spaces:
            while self._not_at_end():
                if not self.next_chr_in(' \t'):
                    self.step_back()
                    break

        while self._not_at_end():
            if self.next_chr_is(')'):
                if self.cleanup:
                    while output[-1] in ' \t':
                        output.pop()
                    self.current_indent = previous_indent
                    self.indentation = previous_indentaton
                output.append(')')
                return ''.join(output)

            elif self.next_chr_is('\n'):
                output.append('\n')
            elif self.next_chr_is('('):
                output.append(self.expression())
            elif self.next_chr_in('"\''):
                output.append(self.string_literal())
            elif self.next_chr_is('$'):
                output.append(self.variable())
            elif self.next_starts('/*'):
                output.append(self.multiline_comment())
            elif self.next_starts('//'):
                output.append(self.inline_comment())
                output.append(self.expect_space())
            elif self.next_chr_is(';'):
                output.append(';')
                output.append(self.expect_space())
            elif self.next_chr_is(','):
                output.append(',')
                output.append(self.expect_space())
            elif self.next_starts(*OPERATORS):
                self.output_operator(output)
            elif self.next_chr_in(' \t'):
                if self.cleanup:
                    while output[-1] in ' \t':
                        output.pop()
                output.append(' ')
            else:
                output.append(self.text[self.position])

        self.warn(output)
        raise UnexpectedEndOfFile('end of file inside (expression)')

    def variable(self):
        ''' read a $variable, add it to the variables list, and return it '''
        start = self.position
        self.step_forward()  # advance past '$'

        while self._not_at_end():
            if not self.next_chr_in(VALID_LETTERS):
                name = self.text[start:self.position]
                varname = name
                is_non_renamed = False
                if name.startswith("$_") and name.lower() == name:
                    varname = vm.get(name)
                    if not varname:
                        varname = name
                        is_non_renamed = True

                if not varname in self.variables:
                    if is_non_renamed:
                        print(f"Non renamed variable {name}!")
                    self.variables.append(varname)
                self.step_back()
                return varname

        raise UnexpectedEndOfFile('end of file inside variable name!')

    def word(self):
        ''' not a variable, but either a function, keyword, or constant. '''
        start = self.position
        while self._not_at_end():
            if not self.next_chr_in(VALID_LETTERS):
                self.step_back()
                word = self.text[start:self.position + 1]
                if not word in self.words:
                    self.words.append(word)
                return word

        raise UnexpectedEndOfFile('end of file inside word.')

    def inline_html(self):
        ''' from ?> until we're back in <?php land... '''
        start = self.position

        while self._not_at_end():
            if self.next_starts('<?php'):
                self.step_forward(4)
                return self.text[start:self.position + 1]

        raise UnexpectedEndOfFile ('End of file within PHP {} block!')

    def line_indent(self, blocklevel=0, basic_indent=None):
        ''' we're at the end of a line, so make sure the new line
            is indented correctly. '''

        blanklines = '\n'  # initial newline...
        start = self.position + 1
        linestart = start

        while self._not_at_end():
            if self.next_chr_is('\n'):
                self.warn('extra newline!')
                linestart = self.position + 1
                blanklines += '\n'
                continue
            if not self.next_chr_in(' \t'):
                this_indent = self.text[linestart:self.position]
                if (blocklevel or basic_indent != None) and self.cleanup:
                    if self.current_indent != this_indent:
                        self.warn('oddball indentation!')
                else:
                    self.current_indent = this_indent

                self.step_back()
                return blanklines + self.current_indent
        # end of file
        return blanklines

    def expect_newline(self):
        ''' after some things, we expect a new line! is that too much to
            ask? '''

        while self._not_at_end():
            if self.next_chr_is('\n'):
                self.step_back()
                return ''

            if self.next_chr_in(' \t'):
                continue
            elif self.next_starts('?>'):
                self.step_back()
                return ' '  # space before end of php block...
            else:
                self.step_back()
                return '\n' + self.current_indent

        return ''  # end of file!

    def expect_space(self, strip_newlines=False):
        ''' after operators, etc, we expect 1 space only. '''
        output = []

        while self._not_at_end():
            if self.next_chr_is('\n'):
                if self.cleanup:
                    if not strip_newlines:
                        output.append('\n' + self.current_indent + self.indentation)
                    else:
                        pass
                else:
                    output.append('\n')

            elif self.next_chr_is(' '):
                if not output or not self.cleanup:
                    output.append(' ')
            elif self.next_chr_is('\t'):
                self.warn("expected ' ', got TAB")
                if self.cleanup:
                    output.append(' ')
                else:
                    output.append('\t')
            else:
                if not output:
                    self.warn('expected space!')
                    if self.cleanup:
                        output.append(' ')

                self.step_back()
                return ''.join(output)

        return '' # end of file

    ####################################
    # output_ functions: which take the current 'output' list and modify
    #                    it directly, rather than simply parsing new stuff
    #                    and returning it...

    def output_curlyblock(self, output, indent):
        ''' after reading a '{', add that and everything that follows into
            the output list '''

        if self.cleanup:
            if len(output) and output[-1] != ' ':
                output.append(' ')

        output.append('{')

        if self.cleanup:
            old_indent = self.current_indent
            self.current_indent += self.indentation
            output.append(self.expect_newline())

        output.append(self.php_section(indent + 1))

        if self.cleanup:
            self.current_indent = old_indent

    def output_semicolon(self, output):
        ''' after reading a ';', add that to the output, as well as tidying up
            any newline / hanging spaces / etc. '''

        if not len(output):
            self.warn('semicolon at beginning of <?php section.')
        else:
            if output[-1] in ' \t':
                self.warn('space before semicolon')
            elif output[-1] in ';\n':
                self.warn('semicolon without line of code!')

        if self.cleanup:
            while len(output) and output[-1] in '; \t\n':
                output.pop()
            if len(output):
                output.append(';')

            output.append(self.expect_newline())
        else:
            output.append(';')

    def output_comma(self, output):
        ''' after reading a comma, add it to the output list, also checking for
            spaces, formatting, etc. '''

        if self.text[self.position - 1] == ' ':
            self.warn('space before comma!')

        output.append(',')

        if self.text[self.position + 1] != ' ':
            self.warn('no space after comma')

        if self.cleanup:
            output.append(' ')

    def output_operator(self, output):
        ''' read an operator, add it to the output list, and check for spacing,
            etc. '''

        operator = self.next_starts(*OPERATORS)

        if operator not in ('++', '--', '::', '->') \
        and self.text[self.position - 1] != ' ':
            self.warn('no space before ' + operator)

            if self.cleanup:
                output.append(' ')

        output.append(operator)
        self.step_forward(len(operator) - 1)

        if operator not in ('++', '--', '::', '->'):
            output.append(self.expect_space())

    def output_clean_endbrace(self, output):
        ''' add the final } to a braced section, correcting the spacing. '''

        if self.cleanup and output and self.k_and_r_braces:
            if output[-1].endswith(self.indentation):
                output[-1] = output[-1][0:-4]
        output.append('}')

    def output_initial_space(self, output, indent):
        ''' when starting a braced section, ensure spacing is sane. '''
        if indent:
            self.step_back()
            output.append(self.expect_newline())
        else:
            output.append(self.text[self.position])

    def statement(self):
        ''' read one PHP statement (semicolon terminated...) '''
        return self.php_section(0, end_at_semicolon=True)

    def output_curly_or_statement(self, output, indent, keyword=''):
        ''' either output { until }, or wrap the next ; terminated statement
            inside it's own new { pair of braces } '''

        if self.text[self.position] != '{':
            self.warn(keyword + ' without {braced} section!')
            self.step_back()
            if self.cleanup:
                output.append('{')
                output.append('\n' + self.current_indent + self.indentation)
                output.append(self.statement())
                output.append('\n' + self.current_indent + '}')
            else:
                self.step_back()
                output.append(self.statement())
                self.step_forward()
                try:
                    if self.text[self.position] == '\n':
                        output.append('\n')
                    else:
                        self.step_back()
                except IndexError:
                    self.step_back()
        else:
            self.output_curlyblock(output, indent)

    def output_keyword_block(self, output, indent):
        ''' this will be for complex stuff like for loops, switches, etc, which
            take a keyword, a () expression (of sorts), and then a {} or single
            line terminated by a ; '''
        keyword = self.next_starts(*KEYWORD_BLOCK_THINGS)
        output.append(keyword)
        self.step_forward(len(keyword) - 1)

        output.append(self.expect_space(strip_newlines=True))
        self.step_forward()

        if keyword not in ('else', 'do'):
            if self.text[self.position] != '(':
                raise PHPError('Expection (expression) after ' + keyword)

            output.append(self.expression())

            if self.cleanup:
                output.append(self.expect_space(strip_newlines=True))
            self.step_forward()

        if not self.cleanup:
            self.step_forward()

        self.output_curly_or_statement(output, indent, keyword)

        if keyword in ('if', 'else if', 'elseif'):
            with self.rollback(output):
                output.append(self.expect_space(strip_newlines=True))
                self.step_forward()

                next_key = self.next_starts('elseif', 'else')
                if next_key:
                    self.output_keyword_block(output, indent)
                else:
                    raise RollBack()

        return True

    def output_function_block(self, output, indent):
        ''' parse and output a function ... block. '''
        output.append('function')
        self.step_forward(7)  # to the end of 'function'

        output.append(self.expect_space(strip_newlines=True))
        self.step_forward()

        if self.next_chr_is('('):
            # anonymous function!
            output.append(self.expression())
            output.append(self.expect_space(strip_newlines=True))
            self.step_forward()
        else:
            function_name = self.word()
            name = fm.get(function_name)
            if name == None:
                print(f"Non renamed function  {function_name}!")
                name = function_name
            # named function
            output.append(name)
            # TODO: now can be followed by 'using', or block....
            output.append(self.expect_space(strip_newlines=True))
            if self.cleanup:
                output.pop() # and remove that space...

            self.step_forward()
            output.append(self.expression())
            self.step_back()

            if self.cleanup:
                output.append(self.expect_newline())

        while self._not_at_end():
            if self.next_chr_is('{'):
                block_output = []
                self.output_curlyblock(block_output, indent)
                break

            else:
                if not self.cleanup:
                    if self.next_chr_in('\n\t '):
                        output.append(self.text[self.position])

        output.append(''.join(block_output))


    ####################################
    # the main parser functions:

    def php_section(self, indent=0, end_at_semicolon=False):  # pylint: disable=R0912
        '''
            parse / cleanup a php block. a block is either between
            '<?php ... ?>' anything inside {}.  inside a {}, '?>...<?php' is
            treated as part of the block, not as the end of the current one.
        '''

        output = []
        basic_indent = None

        while self._not_at_end():
            if self.next_starts('?>'):
                if not indent:
                    if len(output) and output[-1] == basic_indent:
                        output[-1] = '\n'
                    self.step_forward()
                    return ''.join(output)
                else:
                    output.append(self.inline_html())

            elif self.next_chr_in(' \t') and not len(output):
                self.output_initial_space(output, indent)

            elif self.next_chr_is('{'):
                self.output_curlyblock(output, indent)

            elif self.next_chr_is('}'):
                self.output_clean_endbrace(output)
                return ''.join(output)

            elif self.next_chr_is(';'):
                self.output_semicolon(output)
                if end_at_semicolon:
                    break

            elif self.next_chr_is('\n'):
                output.append(self.line_indent(indent, basic_indent))
                if basic_indent == None:
                    basic_indent = output[-1]

            elif self.next_chr_is(','):
                self.output_comma(output)

            elif self.next_chr_in('"\''):
                output.append(self.string_literal())

            elif self.next_starts('/*'):
                output.append(self.multiline_comment())

            elif self.next_starts('//'):
                output.append(self.inline_comment())

            elif self.next_starts(*OPERATORS):
                self.output_operator(output)

            elif self.next_chr_is('$'):
                output.append(self.variable())

            elif self.next_chr_is('('):
                output.append(self.expression())

            elif self.next_word_in(*KEYWORD_BLOCK_THINGS):
                self.output_keyword_block(output, indent)

            elif self.next_word_in('function'):
                self.output_function_block(output, indent)

            elif self.next_chr_in(VALID_LETTERS):
                output.append(self.word())

            else:
                output.append(self.text[self.position])

        try:
            return ''.join(output)
        except:
            print ('failed to join:', output)
            raise

    def parse(self, text):
        ''' the initial 'parse-a-php-file' function. Assumes that it is NOT
            starting inside a <?php block. '''

        self.text = text
        self.text_length = len(text)
        self.position = -1
        self.line_no = 1
        self.chr_no = 0


        output = []

        while self._not_at_end():
            if self.next_starts('<?php'):
                self.step_forward(4)

                output.append('<?php')

                php_block = self.php_section()

                output.append(php_block)
                if self.position < len(self.text) and self.next_starts('>'):
                    output.append('?>')
            else:
                try:
                    output.append(self.text[self.position])
                except IndexError:
                    self.warn('End of file OUTSIDE of <?php block...', 1)
                    break

        return ''.join(output)


def php_lint(input_text: str, verbose = True) -> str:
    output_text = input_text

    p = PHPParser(warn=verbose)
    try:
        output_text = p.parse(input_text)
    except ParseError as excp:
        print('Err:', excp, file=sys.stderr)
        print('---------\n' +
              input_text[0:p.position + 1] +
              "<-------- there!\n", file=sys.stderr)
        raise ParseError

    if verbose:
        print('Variables:', sorted(p.variables), file=sys.stderr)
        print('Words:', sorted(p.words), file=sys.stderr)
    return output_text


