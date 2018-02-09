import io
import re
import collections
from xml import sax
from xml.sax import handler, saxutils, xmlreader

zpt_regex = (r'(?P<before>python:)(?P<expr>[^;]*)(?P<end>;|\Z)')

DOUBLE_SEMICOLON_REPLACEMENT = '_)_replacement_☃_(_'


class PTRegexRewriter(object):
    """A Rewriter based on regex instead of pagetemplate parser."""

    rewrite_action = None
    zpt_regex = (
        # the beginning
        '(?P<before>'
        # match the python: handler in tales
        'python:)'
        # the staet of the actual python expression
        '(?P<expr>'
        # We can have anything except double quotes and semicolon which would
        # end the expression.
        '('
        '[^";]'
        # or
        '|'
        # we have two semicolon as this will escape one.
        '((;(?=;))(;(?<=;)))'
        # end of the expression
        ')*)'
        # the end, we either have a double quote in case of an attribute or a
        # semicolon in case of a tal:define statement.
        '(?P<end>;|")')

    def __init__(self, zpt_input, rewrite_action):
        self.raw = zpt_input
        self.rewrite_action = rewrite_action

    def _rewrite_expression(self, match_ob):
        """Handle the match object to only expose the expression string."""
        return ''.join([
            match_ob.group('before'),
            self.rewrite_action(match_ob.group('expr')),
            match_ob.group('end'),
        ])

    def __call__(self):
        """Return the rewrite of the parsed input."""
        res = self.raw
        res = re.sub(zpt_regex, self._rewrite_expression, self.raw)
        return res


class PythonExpressionFilter(saxutils.XMLFilterBase):
    """Filter for sax handler to expose python expression in pagetemplates."""

    def __init__(self, parent, rewrite_action):
        super().__init__(parent)
        self.rewrite_action = rewrite_action

    def startDocument(self):
        """We return nothing here."""
        # The parent method renders a <xml> tag here, but we do not want that
        # here.
        pass

    def _rewrite_expression(self, match_ob):
        """Handle the match object to only expose the expression string."""
        # Turn the replacement to regular python after matching, before passing
        # it to the rewrite hook.
        unquoted_value = self.rewrite_action(
            match_ob.group('expr').replace(
                DOUBLE_SEMICOLON_REPLACEMENT, ';'))
        # We have to escape the semicolon in python for pagetemplates
        quoted_value = unquoted_value.replace(';', ';;')
        return ''.join([
            match_ob.group('before'),
            quoted_value,
            match_ob.group('end'),
        ])

    def startElement(self, name, attrs):
        """Rewrite the attributes at the start of an element."""
        attrs = collections.OrderedDict(attrs)
        for attr, value in attrs.items():
            if name.startswith('tal:') or attr.startswith('tal:'):
                value = value.replace(';;', DOUBLE_SEMICOLON_REPLACEMENT)
                attrs[attr] = re.sub(
                    zpt_regex, self._rewrite_expression, value)

        saxutils.XMLFilterBase.startElement(self, name, attrs)

    def error(self, exception):
        self._err_handler.warning(exception)

    def fatalError(self, exception):
        self._err_handler.warning(exception)


class PTParserRewriter(object):
    """A rewriter for pagetemplates based on xml parser."""

    rewrite_action = None

    def __init__(self, zpt_input, rewrite_action):
        self.raw = zpt_input
        self.rewrite_action = rewrite_action
        self.output = io.StringIO()

    def rewrite_zpt(self, input_):
        """Rewrite the input_ by parsing it.

        Python expressions are passed to `rewrite_action` for processing
        """
        output_gen = saxutils.XMLGenerator(self.output, encoding='utf-8')
        parser = sax.make_parser()
        filter = PythonExpressionFilter(parser, self.rewrite_action)
        filter.setContentHandler(output_gen)
        filter.setErrorHandler(handler.ErrorHandler())
        for feature in handler.all_features:
            filter.setFeature(feature, False)
        inpsrc = xmlreader.InputSource()
        inpsrc.setCharacterStream(io.StringIO(input_))
        filter.parse(inpsrc)

        self.output.seek(0)
        return self.output.read()

    def __call__(self):
        """Return the rewrite of the parsed input."""
        res = self.rewrite_zpt(self.raw)

        return res
