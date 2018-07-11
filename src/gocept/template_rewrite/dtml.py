import re


dtml_regex = (
    # beginning
    r'(?P<before>'
    # the dtml tag
    r'(<dtml-\w+\s)'
    # We potentially capture multiple attributes in the tag here.
    r'(?P<firstAttrs>'
    # which can consist of word characters that may include a '='. This should
    # not match double quotes as it could be a python expression.
    r'(\w+)=?(\w+)\s'
    r')*'
    # start of the expression, if there were attributes before, we require
    # 'expr'
    r'(?(firstAttrs)(expr=")'
    # or we make it optional. Notice that by grammar documentation 'expr='
    # should be mandatory, but even in the Zope core a Python expression is
    # passed just as string like <dtml-if "num < 5">.
    r'|((expr=")|")'
    ')'
    # end of before group
    r')'
    # the python express
    r'(?P<expr>[^"]*)'
    # the characters after the expression, there might be other attributes
    # afterwards.
    r'(?P<end>"\s?([^>]*)>)'
)


dtml_let_regex = (
    # beginning
    r'(?P<before>'
    # the dtml-let tag
    r'(<dtml-let)\s)'
    # start of the expression section
    r'(?P<expr>'
    # groups of key="value", with possible line breaks (\v)
    r'([^>"]*"[^>"]*"\v?)*'
    # end of expression section
    r')'
    # the characters after the expression
    r'(?P<end>\s?>)'
)


dtml_let_expression_regex = (
    # beginning
    r'(?P<before>'
    # some whitespace potentially due to line breaks
    r'(\s*'
    # the key
    r'\w+="))'
    # the expression
    r'(?P<expr>[^"]*)'
    # the characters after the expression
    r'(?P<end>"\v?)'
)


class DTMLRegexRewriter(object):
    """A Rewriter based on regex instead of DTML parser."""

    rewrite_action = None

    def __init__(self, dtml_input, rewrite_action, *args, **kw):
        self.raw = dtml_input
        self.rewrite_action = rewrite_action

    def _rewrite_expression(self, match_ob):
        """Handle the match object to only expose the expression string."""
        return ''.join([
            match_ob.group('before'),
            self.rewrite_action(match_ob.group('expr'),
                                lineno=None, tag=None, filename=None),
            match_ob.group('end'),
        ])

    def _rewrite_let(self, match_ob):
        """Handle the dtml-let matches, that are different than expressions."""
        return ''.join([
            match_ob.group('before'),
            re.sub(dtml_let_expression_regex,
                   self._rewrite_expression,
                   match_ob.group('expr')
                   ),
            match_ob.group('end'),
        ])

    def __call__(self):
        """Return the rewrite of the parsed input."""
        res = re.sub(dtml_regex, self._rewrite_expression, self.raw)
        # let statements
        res = re.sub(dtml_let_regex, self._rewrite_let, res)

        return res
