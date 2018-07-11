import functools
from xml.sax import handler, saxutils
import collections
import html.parser
import io
import logging
import re


log = logging.getLogger(__name__)


RE_MULTI_ATTRIBUTES = (r'(?P<before>python:)(?P<expr>[^;]*)(?P<end>;|\Z)')
# [\w\W] matches any symbol including newlines
RE_SINGLE_ATTRIBUTES = (r'(?P<before>python:)(?P<expr>[\w\W]*)(?P<end>)')

DOUBLE_SEMICOLON_REPLACEMENT = '_)_replacement_☃_(_'


class PTParseError(SyntaxError):
    """Error while parsing a page template.

    Should be raised by rewrite_action on error."""


class PythonExpressionFilter(saxutils.XMLFilterBase):
    """Filter for sax handler to expose python expression in pagetemplates."""

    def __init__(self, parent, rewrite_action, filename):
        super().__init__(parent)
        self.rewrite_action = rewrite_action
        self.filename = filename

    def startDocument(self):
        """We return nothing here."""
        # The parent method renders a <xml> tag here, but we do not want that
        # here.
        pass

    def _join_expression(self, value, match_ob):
        """Re-join the matched groups."""
        return ''.join([
            match_ob.group('before'),
            value,
            match_ob.group('end'),
        ])

    def _rewrite_single_expression(self, match_ob, lineno, tag, filename):
        """Handle the match object of a single expression."""
        replaced_value = self.rewrite_action(
            match_ob.group('expr'),
            lineno=lineno,
            tag=tag,
            filename=filename,
        )
        return self._join_expression(replaced_value, match_ob)

    def _rewrite_multi_expression(self, match_ob, lineno, tag, filename):
        """Handle the match object of a multi expression."""
        # Turn the replacement to regular python after matching, before passing
        # it to the rewrite hook.
        unquoted_value = self.rewrite_action(
            match_ob.group('expr').replace(
                DOUBLE_SEMICOLON_REPLACEMENT, ';'),
            lineno=lineno,
            tag=tag,
            filename=filename,
        )
        # We have to escape the semicolon in python for pagetemplates
        quoted_value = unquoted_value.replace(';', ';;')
        return self._join_expression(quoted_value, match_ob)

    def _is_multi_expression(self, name, attr):
        if (name.startswith('tal:')
                and attr in ('attributes', 'define')):
            return True
        elif attr in ('tal:attributes', 'tal:define'):
            return True
        else:
            return False

    def startElement(self, name, attrs, ws_dict, is_short_tag, lineno):
        """Rewrite the attributes at the start of an element."""
        attrs = collections.OrderedDict(attrs)
        for attr, value in attrs.items():
            if name.startswith('tal:') or attr.startswith('tal:'):
                if self._is_multi_expression(name, attr):
                    zpt_regex = RE_MULTI_ATTRIBUTES
                    rewrite_expression = self._rewrite_multi_expression
                else:
                    zpt_regex = RE_SINGLE_ATTRIBUTES
                    rewrite_expression = self._rewrite_single_expression
                value = value.replace(';;', DOUBLE_SEMICOLON_REPLACEMENT)

                tag = join_element(name, attrs, ws_dict, is_short_tag)
                rewrite_expression = functools.partial(
                    rewrite_expression, lineno=lineno, tag=tag,
                    filename=self.filename)

                try:
                    rewritten_value = re.sub(
                        zpt_regex, rewrite_expression, value)
                except PTParseError:
                    rewritten_value = value
                # We want to undo the replacement also in cases the regex did
                # not match.
                attrs[attr] = rewritten_value.replace(
                    DOUBLE_SEMICOLON_REPLACEMENT, ';;')

        self._cont_handler.startElement(name, attrs, ws_dict, is_short_tag)

    def parse(self, source):
        self._parent.setContentHandler(self)
        self._parent.feed(source)
        self._parent.close()


leading_whitespace = '(\s*{})'


class HTMLGenerator(html.parser.HTMLParser):
    """A HTML parser which also generates a html file."""

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, is_short_tag=True)

    def handle_starttag(self, tag, attrs, is_short_tag=False):
        full_tag = self.get_starttag_text()
        ws_dict = {}
        for attr, value in attrs:
            # We include the '=' to ensure that we get the attribute instead of
            # another string in the tag.
            mo = re.search(leading_whitespace.format(attr) + '(?==)', full_tag,
                           flags=re.IGNORECASE)
            if not mo:
                # We seem to have a attribute without `=` so we ensure
                # whitespaces around it and hope that the will not be another
                # occurrence of it.
                mo = re.search(
                    leading_whitespace.format(attr) + '(\s*)', full_tag,
                    flags=re.IGNORECASE)
            ws_dict[attr] = mo.group(1)

        if is_short_tag:
            short_tag = '/>'
            mo = re.search(leading_whitespace.format(short_tag), full_tag)
            ws_dict[short_tag] = mo.group()

        # XXX We are deeply coupling to our generator here, as we change the
        # signature wrt the base class.
        self._cont_handler.startElement(
            tag, attrs, ws_dict, is_short_tag=is_short_tag,
            lineno=self.getpos()[0])

    def _write_raw(self, data):
        # We use `ignorableWhitespace` here as it does no escaping.
        self._cont_handler.ignorableWhitespace(data)

    def handle_endtag(self, tag):
        self._cont_handler.endElement(tag)

    def handle_charref(self, name):
        self._write_raw(f'&#{name};')

    # Overridable -- handle entity reference
    def handle_entityref(self, name):
        self._write_raw(f'&{name};')

    # Overridable -- handle data
    def handle_data(self, data):
        self._write_raw(data)

    # Overridable -- handle comment
    def handle_comment(self, data):
        self._write_raw(f'<!--{data}-->')

    # Overridable -- handle declaration
    def handle_decl(self, decl):
        self._cont_handler.startElement('!' + decl, {}, {}, is_short_tag=False)

    # Overridable -- handle processing instruction
    def handle_pi(self, data):
        self._write_raw(f'<?{data}>')

    def unknown_decl(self, data):
        raise NotImplementedError

    def setContentHandler(self, cont_handler):
        self._cont_handler = cont_handler


def quoteattr(data, entities={}):
    """Quote an attribute value.

    Escape less then xml.saxutils.quoteattr.
    """
    if '"' in data:
        if "'" in data:
            data = '"%s"' % data.replace('"', "&quot;")
        else:
            data = "'%s'" % data
    else:
        data = '"%s"' % data
    return data


def join_element(name, attrs, ws_dict, is_short_tag):
    """Synthesize the element from parsed parts."""
    content = []
    content.append(u'<' + name)
    for (attr, value) in attrs.items():
        if name.startswith('tal:') or attr.startswith('tal:'):
            # Do not insert additional quoting for tales expressions
            content.append(u'%s=%s' % (ws_dict[attr], quoteattr(value)))
        else:
            # Keep the quoting for the other cases.
            if value is None:
                content.append(u'%s' % ws_dict[attr])
            else:
                content.append(u'%s=%s' % (ws_dict[attr],
                                           saxutils.quoteattr(value)))
    if is_short_tag:
        # if we have a short_tag we want to render it with whitespaces.
        content.append(ws_dict['/>'])
    else:
        content.append(u'>')
    return ''.join(content)


class CustomXMLGenerator(saxutils.XMLGenerator):
    """XMLGenerator with escape tweaks."""

    def startElement(self, name, attrs, ws_dict, is_short_tag):
        self._write(join_element(name, attrs, ws_dict, is_short_tag))


class PTParserRewriter(object):
    """A rewriter for pagetemplates based on xml parser."""

    rewrite_action = None

    def __init__(self, zpt_input, rewrite_action, filename=''):
        self.raw = zpt_input
        self.rewrite_action = rewrite_action
        self.output = io.StringIO()
        self.filename = filename

    def rewrite_zpt(self, input_):
        """Rewrite the input_ by parsing it.

        Python expressions are passed to `rewrite_action` for processing
        """
        if 'tal:' in input_:
            output_gen = CustomXMLGenerator(self.output, encoding='utf-8')
            parser = HTMLGenerator(convert_charrefs=False)
            filter = PythonExpressionFilter(
                parser, self.rewrite_action, filename=self.filename)
            filter.setContentHandler(output_gen)
            filter.setErrorHandler(handler.ErrorHandler())
            filter.parse(input_)

            self.output.seek(0)
            return self.output.read()
        return input_

    def __call__(self):
        """Return the rewrite of the parsed input."""
        res = self.rewrite_zpt(self.raw)

        return res
