import html.parser
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

    def startElement(self, name, attrs, ws_dict, is_short_tag):
        """Rewrite the attributes at the start of an element."""
        attrs = collections.OrderedDict(attrs)
        for attr, value in attrs.items():
            if name.startswith('tal:') or attr.startswith('tal:'):
                value = value.replace(';;', DOUBLE_SEMICOLON_REPLACEMENT)
                attrs[attr] = re.sub(
                    zpt_regex, self._rewrite_expression, value)

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
            mo = re.search(leading_whitespace.format(attr) + '(?==)', full_tag)
            if not mo:
                # We seem to have a attribute without `=` so we ensure
                # whitespaces around it and hope that the will not be another
                # occurrence of it.
                mo = re.search(
                    leading_whitespace.format(attr) + '(\s*)', full_tag)
            ws_dict[attr] = mo.group(1)

        if is_short_tag:
            short_tag = '/>'
            mo = re.search(leading_whitespace.format(short_tag), full_tag)
            ws_dict[short_tag] = mo.group()

        # XXX We are deeply coupling to our generator here, as we change the
        # signature wrt the base class.
        self._cont_handler.startElement(
            tag, attrs, ws_dict, is_short_tag=is_short_tag)

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
        self._cont_handler.characters(data)

    # Overridable -- handle comment
    def handle_comment(self, data):
        self._write_raw(f'<!--{data}-->')

    # Overridable -- handle declaration
    def handle_decl(self, decl):
        self._cont_handler.startElement('!' + decl, {}, {}, is_short_tag=False)

    # Overridable -- handle processing instruction
    def handle_pi(self, data):
        raise NotImplementedError

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


class CustomXMLGenerator(saxutils.XMLGenerator):
    """XMLGenerator with escape tweaks."""

    def startElement(self, name, attrs, ws_dict, is_short_tag):
        self._write(u'<' + name)
        for (attr, value) in attrs.items():
            if name.startswith('tal:') or attr.startswith('tal:'):
                # Do not insert additional quoting for tales expressions
                self._write(u'%s=%s' % (ws_dict[attr], quoteattr(value)))
            else:
                # Keep the quoting for the other cases.
                if value is None:
                    self._write(u'%s' % ws_dict[attr])
                else:
                    self._write(u'%s=%s' % (ws_dict[attr],
                                            saxutils.quoteattr(value)))

        if is_short_tag:
            # if we have a short_tag we want to render it with whitespaces.
            self._write(ws_dict['/>'])
        else:
            self._write(u'>')



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
        output_gen = CustomXMLGenerator(self.output, encoding='utf-8')
        parser = HTMLGenerator(convert_charrefs=False)
        filter = PythonExpressionFilter(parser, self.rewrite_action)
        filter.setContentHandler(output_gen)
        filter.setErrorHandler(handler.ErrorHandler())
        # for feature in handler.all_features:
        #     filter.setFeature(feature, False)
        # inpsrc = xmlreader.InputSource()
        # inpsrc.setCharacterStream(io.StringIO(input_))
        filter.parse(input_)

        self.output.seek(0)
        return self.output.read()

    def __call__(self):
        """Return the rewrite of the parsed input."""
        res = self.rewrite_zpt(self.raw)

        return res
