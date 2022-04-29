from xml.sax import handler
from xml.sax import saxutils
import collections
import functools
import html.parser
import io
import lib2to3.pgen2.parse
import logging
import re


log = logging.getLogger(__name__)


RE_MULTI_ATTRIBUTES = (r'(?P<before>python:)(?P<expr>[^;]*)(?P<end>;|\Z)')
# [\w\W] matches any symbol including newlines
RE_SINGLE_ATTRIBUTES = (r'(?P<before>python:)(?P<expr>[\w\W]*)(?P<end>)')

DOUBLE_SEMICOLON_REPLACEMENT = '_)_replacement_☃_(_'

# This prevents collision with attribute names.
ENDTAG = '>endtag<'


class PTParseError(SyntaxError):
    """Error while parsing a page template.

    Should be raised by rewrite_action on error."""


class PythonExpressionFilter(saxutils.XMLFilterBase):
    """Filter for sax handler to expose python expression in pagetemplates."""

    def __init__(self, parent, rewrite_action, filename):
        super().__init__(parent)
        self.rewrite_action = rewrite_action
        self.filename = filename

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

                if value is None:
                    raise PTParseError

                value = value.replace(';;', DOUBLE_SEMICOLON_REPLACEMENT)

                tag = join_element(name, attrs, ws_dict)
                rewrite_expression = functools.partial(
                    rewrite_expression, lineno=lineno, tag=tag,
                    filename=self.filename)

                rewritten_value = re.sub(
                    zpt_regex, rewrite_expression, value)

                # We want to undo the replacement also in cases the regex did
                # not match.
                attrs[attr] = rewritten_value.replace(
                    DOUBLE_SEMICOLON_REPLACEMENT, ';;')

        self._cont_handler.startElement(name, attrs, ws_dict, is_short_tag)

    def parse(self, source):
        self._parent.setContentHandler(self)
        self._parent.feed(source)
        self._parent.close()


class HTMLGenerator(html.parser.HTMLParser):
    """A HTML parser which also generates a html file."""

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, is_short_tag=True)

    def handle_starttag(self, tag, attrs, is_short_tag=False):
        full_tag = self.get_starttag_text()
        ws_dict = {}
        raw_attrs = []
        parse_error = False
        # Pattern that selects both the key with preceding whitespaces and the
        # raw value
        patterns = [
            r'(\s+{})="([^"]*)"',  # Double quotes
            r"(\s+{})='([^']*)'",  # Single quotes
            r"(\s+{})\b",  # Singleton, no value
        ]
        for attr, value in attrs:
            for pattern in patterns:
                mo = re.search(pattern.format(attr), full_tag,
                               flags=re.IGNORECASE)
                if mo:
                    break
            else:
                # No pattern matches
                parse_error = True
                break

            # The value is already unescaped, but we want the raw value as this
            # is the only way to preserve both `&` and `&amp;` in one string at
            # the same time.
            raw_value = mo.group(2) if len(mo.groups()) == 2 else None
            ws_dict[attr] = mo.group(1)
            raw_attrs.append((attr, raw_value))

        if not parse_error:
            # Find end tag matching whitespaces and shorttag
            mo = re.search(r'(\s*/?>$)', full_tag)
            ws_dict[ENDTAG] = mo.group()

            # XXX We are deeply coupling to our generator here, as we change
            # the signature wrt the base class.
            try:
                self._cont_handler.startElement(
                    tag, raw_attrs, ws_dict, is_short_tag=is_short_tag,
                    lineno=self.getpos()[0])
            except (PTParseError, lib2to3.pgen2.parse.ParseError):
                parse_error = True

        if parse_error:
            self.parse_errors.append({
                'lineno': self.getpos()[0],
                'tag': full_tag,
            })

    def _write_raw(self, data):
        # We use `ignorableWhitespace` here as it does no escaping.
        self._cont_handler.ignorableWhitespace(data)

    def handle_pi(self, data):
        self._write_raw(f'<?{data}>')

    def handle_comment(self, data):
        data = data.replace('--', '')
        self._write_raw(f'<!--{data}-->')

    def handle_charref(self, name):
        self._write_raw(f'&#{name};')

    def handle_entityref(self, name):
        self._write_raw(f'&{name};')

    def handle_decl(self, decl):
        # lineno is only needed for tal-expressions.
        self._cont_handler.startElement(
            '!' + decl, {}, {ENDTAG: '>'}, is_short_tag=False,
            lineno=self.getpos()[0])

    def handle_endtag(self, tag):
        self._cont_handler.endElement(tag)

    def handle_data(self, data):
        self._write_raw(data)

    def unknown_decl(self, data):
        raise NotImplementedError

    def setContentHandler(self, cont_handler):
        self._cont_handler = cont_handler


def quoteattr(data):
    """Quote an attribute value.

    Escape less then the obvious xml.saxutils.quoteattr,
    e.g. do not convert `\n` to `&#10;`.
    """
    return '"%s"' % data.replace('"', "&quot;")


def join_element(name, attrs, ws_dict):
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
                                           quoteattr(value)))
    content.append(ws_dict[ENDTAG])
    return ''.join(content)


class CustomXMLGenerator(saxutils.XMLGenerator):
    """XMLGenerator with escape tweaks."""

    def startElement(self, name, attrs, ws_dict, is_short_tag):
        self._write(join_element(name, attrs, ws_dict))


class PTParserRewriter(object):
    """A rewriter for pagetemplates based on xml parser."""

    rewrite_action = None

    def __init__(self, zpt_input, rewrite_action, filename=''):
        self.raw = zpt_input
        self.rewrite_action = rewrite_action
        self.output = io.StringIO()
        self.filename = filename

    @property
    def _is_tal_content(self):
        return 'tal:' in self.raw

    def rewrite_zpt(self, input_):
        """Rewrite the input_ by parsing it.

        Python expressions are passed to `rewrite_action` for processing
        """
        output_gen = CustomXMLGenerator(self.output, encoding='utf-8')
        parser = HTMLGenerator(convert_charrefs=False)
        parser.parse_errors = []
        filter = PythonExpressionFilter(
            parser, self.rewrite_action, filename=self.filename)
        filter.setContentHandler(output_gen)
        filter.setErrorHandler(handler.ErrorHandler())
        filter.parse(input_)
        for err in parser.parse_errors:
            log.error(
                'Parsing error in %s:%d \n\t%s',
                self.filename,
                err['lineno'],
                err['tag'],
                exc_info=False,
            )
        if len(parser.parse_errors):
            raise PTParseError

        self.output.seek(0)
        return self.output.read()

    def __call__(self):
        """Return the rewrite of the parsed input."""
        if self._is_tal_content:
            return self.rewrite_zpt(self.raw)
        return self.raw
