"""
This code was extracted in part from
https://github.com/PyCQA/bandit. Using similar heuristic logic,
we adapted it to fit our plugin infrastructure, to create an organized,
concerted effort in detecting all type of secrets in code.

Copyright (c) 2014 Hewlett-Packard Development Company, L.P.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
from __future__ import absolute_import

import re

from .base import BasePlugin
from .common.filetype import determine_file_type
from .common.filetype import FileType
from detect_secrets.core.potential_secret import PotentialSecret


# Note: All values here should be lowercase
DENYLIST = (
    'apikey',
    'api_key',
    'aws_secret_access_key',
    'db_pass',
    'password',
    'passwd',
    'private_key',
    'secret',
    'secrete',
)
FALSE_POSITIVES = {
    '""',
    '""):',
    '"\'',
    '")',
    '"dummy',
    '"replace',
    '"this',
    '#pass',
    '#password',
    '$(shell',
    "'\"",
    "''",
    "''):",
    "')",
    "'dummy",
    "'replace",
    "'this",
    '(nsstring',
    '-default}',
    '/etc/passwd:ro',
    '::',
    '<a',
    '<aws_secret_access_key>',
    '<input',
    '<password>',
    '<redacted>',
    '>',
    '=',
    '\\"$(shell',
    '\\k.*"',
    "\\k.*'",
    '`cat',
    '`grep',
    'account_password',
    'dummy_secret',
    'dummy_value',
    'false',
    'false):',
    'false,',
    'false;',
    'none',
    'none,',
    'none}',
    'not',
    'null',
    'null,',
    'null.*"',
    "null.*'",
    'null;',
    'password',
    'password)',
    'password,',
    'password},',
    'prompt',
    'redacted',
    'some_key',
    'str_to_sign',
    'string,',
    'string;',
    'string?',
    'string}',
    'string}}',
    'test-access-key',
    'thisisnottherealsecret',
    'todo',
    'true',
    'true):',
    'true,',
    'true;',
    '{',
}
# Includes ], ', " as closing
CLOSING = r'[]\'"]{0,2}'
DENYLIST_REGEX = r'|'.join(DENYLIST)
# Non-greedy match
OPTIONAL_WHITESPACE = r'\s*?'
OPTIONAL_NON_WHITESPACE = r'[^\s]*?'
QUOTE = r'[\'"]'
SECRET = r'[^\s]+'
SQUARE_BRACKETS = r'(\[\])'

FOLLOWED_BY_COLON_EQUAL_SIGNS_REGEX = re.compile(
    # e.g. my_password := "bar" or my_password := bar
    r'({denylist})({closing})?{whitespace}:=?{whitespace}({quote}?)({secret})(\3)'.format(
        denylist=DENYLIST_REGEX,
        closing=CLOSING,
        quote=QUOTE,
        whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
FOLLOWED_BY_COLON_REGEX = re.compile(
    # e.g. api_key: foo
    r'({denylist})({closing})?:{whitespace}({quote}?)({secret})(\3)'.format(
        denylist=DENYLIST_REGEX,
        closing=CLOSING,
        quote=QUOTE,
        whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
FOLLOWED_BY_COLON_QUOTES_REQUIRED_REGEX = re.compile(
    # e.g. api_key: "foo"
    r'({denylist})({closing})?:({whitespace})({quote})({secret})(\4)'.format(
        denylist=DENYLIST_REGEX,
        closing=CLOSING,
        quote=QUOTE,
        whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
FOLLOWED_BY_EQUAL_SIGNS_OPTIONAL_BRACKETS_OPTIONAL_AT_SIGN_QUOTES_REQUIRED_REGEX = re.compile(
    # e.g. my_password = "bar"
    # e.g. my_password = @"bar"
    # e.g. my_password[] = "bar";
    r'({denylist})({square_brackets})?{optional_whitespace}={optional_whitespace}(@)?(")({secret})(\5)'.format(  # noqa: E501
        denylist=DENYLIST_REGEX,
        square_brackets=SQUARE_BRACKETS,
        optional_whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
FOLLOWED_BY_EQUAL_SIGNS_REGEX = re.compile(
    # e.g. my_password = bar
    r'({denylist})({closing})?{whitespace}={whitespace}({quote}?)({secret})(\3)'.format(
        denylist=DENYLIST_REGEX,
        closing=CLOSING,
        quote=QUOTE,
        whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
FOLLOWED_BY_EQUAL_SIGNS_QUOTES_REQUIRED_REGEX = re.compile(
    # e.g. my_password = "bar"
    r'({denylist})({closing})?{whitespace}={whitespace}({quote})({secret})(\3)'.format(
        denylist=DENYLIST_REGEX,
        closing=CLOSING,
        quote=QUOTE,
        whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
FOLLOWED_BY_QUOTES_AND_SEMICOLON_REGEX = re.compile(
    # e.g. private_key "something";
    r'({denylist}){nonWhitespace}{whitespace}({quote})({secret})(\2);'.format(
        denylist=DENYLIST_REGEX,
        nonWhitespace=OPTIONAL_NON_WHITESPACE,
        quote=QUOTE,
        closing=CLOSING,
        whitespace=OPTIONAL_WHITESPACE,
        secret=SECRET,
    ),
)
DENYLIST_REGEX_TO_GROUP = {
    FOLLOWED_BY_COLON_REGEX: 4,
    FOLLOWED_BY_EQUAL_SIGNS_REGEX: 4,
    FOLLOWED_BY_QUOTES_AND_SEMICOLON_REGEX: 3,
}
GOLANG_DENYLIST_REGEX_TO_GROUP = {
    FOLLOWED_BY_COLON_EQUAL_SIGNS_REGEX: 4,
    FOLLOWED_BY_EQUAL_SIGNS_REGEX: 4,
    FOLLOWED_BY_QUOTES_AND_SEMICOLON_REGEX: 3,
}
OBJECTIVE_C_DENYLIST_REGEX_TO_GROUP = {
    FOLLOWED_BY_EQUAL_SIGNS_OPTIONAL_BRACKETS_OPTIONAL_AT_SIGN_QUOTES_REQUIRED_REGEX: 6,
}
QUOTES_REQUIRED_DENYLIST_REGEX_TO_GROUP = {
    FOLLOWED_BY_COLON_QUOTES_REQUIRED_REGEX: 5,
    FOLLOWED_BY_EQUAL_SIGNS_QUOTES_REQUIRED_REGEX: 4,
    FOLLOWED_BY_QUOTES_AND_SEMICOLON_REGEX: 3,
}
QUOTES_REQUIRED_FILETYPES = {
    FileType.CLS,
    FileType.JAVA,
    FileType.JAVASCRIPT,
    FileType.PYTHON,
    FileType.SWIFT,
}


class KeywordDetector(BasePlugin):
    """This checks if denylisted keywords
    are present in the analyzed string.
    """

    secret_type = 'Secret Keyword'

    def __init__(self, keyword_exclude=None, exclude_lines_regex=None, **kwargs):
        super(KeywordDetector, self).__init__(
            exclude_lines_regex,
        )

        self.keyword_exclude = None
        if keyword_exclude:
            self.keyword_exclude = re.compile(
                keyword_exclude,
                re.IGNORECASE,
            )

    def analyze_string_content(self, string, line_num, filename):
        output = {}
        if (
            self.keyword_exclude
            and self.keyword_exclude.search(string)
        ):
            return output
        for identifier in self.secret_generator(
            string,
            filetype=determine_file_type(filename),
        ):
            secret = PotentialSecret(
                self.secret_type,
                filename,
                identifier,
                line_num,
            )
            output[secret] = secret

        return output

    def secret_generator(self, string, filetype):
        lowered_string = string.lower()

        if filetype in QUOTES_REQUIRED_FILETYPES:
            denylist_regex_to_group = QUOTES_REQUIRED_DENYLIST_REGEX_TO_GROUP
        elif filetype == FileType.GO:
            denylist_regex_to_group = GOLANG_DENYLIST_REGEX_TO_GROUP
        elif filetype == FileType.OBJECTIVE_C:
            denylist_regex_to_group = OBJECTIVE_C_DENYLIST_REGEX_TO_GROUP
        else:
            denylist_regex_to_group = DENYLIST_REGEX_TO_GROUP

        for denylist_regex, group_number in denylist_regex_to_group.items():
            match = denylist_regex.search(lowered_string)
            if match:
                lowered_secret = match.group(group_number)

                # ([^\s]+) guarantees lowered_secret is not ''
                if not probably_false_positive(
                    lowered_secret,
                    filetype=filetype,
                ):
                    yield lowered_secret


def probably_false_positive(lowered_secret, filetype):
    if (
        'fake' in lowered_secret
        or 'forgot' in lowered_secret
        or lowered_secret in FALSE_POSITIVES
        # For e.g. "secret": "{secret}"
        or (
            lowered_secret[0] == '{'
            and lowered_secret[-1] == '}'
        ) or (
            filetype == FileType.PHP
            and lowered_secret[0] == '$'
        ) or (
            filetype == FileType.YAML
            and lowered_secret.startswith('{{')
            and lowered_secret.endswith('}}')
        )
    ):
        return True

    # Heuristic for no function calls
    try:
        if (
            lowered_secret.index('(') < lowered_secret.index(')')
        ):
            return True
    except ValueError:
        pass

    # Heuristic for e.g. request.json_body['hey']
    try:
        if (
            lowered_secret.index('[') < lowered_secret.index(']')
        ):
            return True
    except ValueError:
        pass

    # Heuristic for e.g. ${link}
    try:
        if (
            lowered_secret.index('${') < lowered_secret.index('}')
        ):
            return True
    except ValueError:
        pass

    return False
