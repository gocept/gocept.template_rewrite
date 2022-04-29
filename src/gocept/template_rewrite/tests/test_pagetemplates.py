from gocept.template_rewrite.lib2to3 import rewrite_using_2to3
from gocept.template_rewrite.pagetemplates import PTParseError
from gocept.template_rewrite.pagetemplates import PTParserRewriter
import logging
import pytest


@pytest.fixture(scope='module', autouse=True)
def rewriter():
    """We want to parse all the strings in tests.

    The parser makes an optimization for files without `tal:` in reality.
    """
    old_prop = PTParserRewriter._is_tal_content
    PTParserRewriter._is_tal_content = True
    yield
    PTParserRewriter._is_tal_content = old_prop


@pytest.mark.parametrize('input, expected', [
    ('<p tal:define="x d; y python: str(234); z python: 5; a d"></p>',
     '<p tal:define="x d; y python:rewritten; z python:rewritten; a d"></p>'),
    ('<tal:t define="x d; y python: str(234); z python: 5; a d"></tal:t>',
     '<tal:t define="x d; y python:rewritten; z python:rewritten; a d">'
     '</tal:t>'),
    # Double hyphen gets removed.
    ('<!-- Comment with double hyphen -- in the middle -->',
     '<!-- Comment with double hyphen  in the middle -->'),
    ('<!-- Comment with triple hyphen --- in the middle -->',
     '<!-- Comment with triple hyphen - in the middle -->'),
    ('<!-- Comment with quadruple hyphen ---- in the middle -->',
     '<!-- Comment with quadruple hyphen  in the middle -->'),
    # Invalid single-quotes get correctly converted to double-quotes
    ('<p class=\'test\'></p>', '<p class="test"></p>'),
])
def test_pagetemplates__PTParserRewriter____call____1(
        input, expected):
    """It rewrites the expression values of the pagetemplate."""
    rw = PTParserRewriter(input, lambda x, lineno, tag, filename: "rewritten")
    assert rw() == expected


@pytest.mark.parametrize('input, expected', [
    ('<p tal:content="python: str(234)" class="python:script"></p>',
     '<p tal:content="python:rewritten" class="python:script"></p>'),
    ('''<p tal:define="x d; y python: str(';;'); z python: 5"></p>''',
     '<p tal:define="x d; y python:rewritten; z python:rewritten"></p>'),
    ('<tal:t content="python: str(234)" class="python:script"></tal:t>',
     '<tal:t content="python:rewritten" class="python:rewritten"></tal:t>'),
    ('''<tal:t define="x d; y python: str(';;'); z python: 5"></tal:t>''',
     '<tal:t define="x d; y python:rewritten; z python:rewritten"></tal:t>'),
])
def test_pagetemplates__PTParserRewriter____call____1_2(
        input, expected):
    """It rewrites the expression values of the pagetemplate.

    (working well with PTParserRewriter)
    """
    rw = PTParserRewriter(input, lambda x, lineno, tag, filename: "rewritten")
    assert rw() == expected


@pytest.mark.parametrize('input, expected', [
    ('''<p tal:define="y python: str(';;')"></p>''',
     '''<p tal:define="y python: unicode(';;')"></p>'''),
    ('''<tal:t define="y python: str(';;')"></tal:t>''',
     '''<tal:t define="y python: unicode(';;')"></tal:t>'''),
    ('''<p tal:define="y python: str(';;;;')"></p>''',
     '''<p tal:define="y python: unicode(';;;;')"></p>'''),
    ('''<tal:t define="y python: str(';;;;')"></tal:t>''',
     '''<tal:t define="y python: unicode(';;;;')"></tal:t>'''),
])
def test_pagetemplates__PTParserRewriter____call____2(
        input, expected):
    """It can work with double semicolon (escape for a single one)."""
    rw = PTParserRewriter(
        input, lambda x, lineno, tag, filename: x.replace('str', 'unicode'))
    assert rw() == expected


@pytest.mark.parametrize('input', [
    ('''
<button tal:attributes="onclick string:go('view?id=${item/is}&re_url=redir')">
        </button>'''),
    ('''
<tal:x condition="item/desc"
       replace="structure python:item.replace('\n','<br/>')"/>'''),
    # We have the name of an attribute occurring after it in the tag.
    ('''
<input type="hidden"
       id="selector"
       name="id"
       tal:attributes="value request/id|nothing">'''),
    ('''
<input type="hidden"
       id="selector"
       name="id"
       disabled
       tal:attributes="disabled view/disabled">'''),
    ('<!-- Support for an on-screen keyboard -->'),
    ('''
<!-- Support for an
        on-screen keyboard -->'''),
    '''<!DOCTYPE html>''',
    ('''
<p>Documents with multiple document root tags</p>
<p>are not valid XML.</p>
'''),
    ('''
<p>Can we parse entities</p>
&nbsp;
<p>between tags</p>
'''),
    ('''<p>Can we parse character references &#x34;</p> '''),
    # Processing instruction
    '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>''',
    # It does not change string expressions
    '''<a tal:content="string:${view/b};;3">a</a>''',
    # It keeps the escapable characters in script tags.
    '''<script> a <> 2 & 4 </script>''',
    # But also keeps entity references.
    '''<p> a &lt;&gt; 2 &amp; 4</p>''',
    '''<p tal:content="&quot;'"> a </p>''',
    '''<p tal:content="&quot;"> a </p>''',
    # Weird casing of attributes
    '''<a href="#" onClick="window.open('ttwidget_html')">New window</a>''',
    '''<a href="#" disAbled>New window</a>''',
    # semicolons are not touched in tal:content.
    '''<span tal:content="python: 'abd;adb'" />''',
    '''<span tal:content="python: 'abd;;adb'" />''',
    '''<span tal:content="python: 'abd\\';;adb'" />''',
    # Whitespaces at the end of a tag
    '''<td tal:attributes="class item/class" >asdf</td>''',
    '''<input tal:attributes="value python:test(e_id=e_id)" id="info">''',
    # Whitespaces between tags
    '''<td valign="top" align="right" width="20">''',
])
def test_pagetemplates__PTParserRewriter____call____3(
        input):
    """It can handle some edge cases in pagetemplates."""
    rw = PTParserRewriter(input, lambda x, lineno, tag, filename: x)
    assert rw() == input


@pytest.mark.parametrize('input, expected', [
    ('<p tal:content="python: long(a)"></p>',
     '<p tal:content="python:int(a)"></p>',),
    ('''<span tal:content="python: 'abd;adb'" />''',
     '''<span tal:content="python: 'abd;adb'" />'''),
])
def test_pagetemplates__PTParserRewriter____call____4(
        input, expected):
    """It can be used with a preconfigured 2to3 rewrite_action."""
    rw = PTParserRewriter(input, rewrite_using_2to3)
    assert rw() == expected


@pytest.mark.parametrize('input', [
    '''<span tal:attributes="color python: 'green';
                             bg_color 'red'" />''',
    '''<span tal:define="color python: 'green';
                         bg_color 'red'" />''',
    # semicolons are not touched in tal:content.
    '''<span tal:content="python: 'abd;adb'" />''',
    '''<span tal:content="python: 'abd;;adb'" />''',
    '''<span tal:content="python: 'abd\\';;adb'" />''',
    # We allow newlines within brackets
    ('''<tal:x condition="python:(a
                  or b)">'''),
    '''<span>&amp;</span>''',
    '''<input type="hidden" name="test" value="&amp;">''',
    ('''<button tal:attributes="'''
     '''onclick string:window.location = 'test?foo=bar&bar=foo'">'''),
    '''<button type="button" onclick="text_insert('&amp;')">asdf</button>''',
    ('''<button onclick="go('page/launch?table=gendocument&id='+current_id())\
">Ext. Editor</button>'''),
])
def test_pagetemplates__PTParserRewriter____call____5(
        input):
    """It is not changed by the preconfigured 2to3 rewrite_action."""
    rw = PTParserRewriter(input, rewrite_using_2to3)
    assert rw() == input


def test_pagetemplates__PTParserRewriter____call____6(caplog):
    """It raises an error when reaching a parsing error, but provides
    information about it."""
    broken = """\
<span> everything is fine here </span>
<p tal:attributes="color python: a
                                  or b.has_key('test')"></p>
<span> everything is fine here again </span>
<p tal:attributes="color python: or or"></p>
"""
    with pytest.raises(PTParseError):
        assert PTParserRewriter(broken, rewrite_using_2to3,
                                filename='broken.pt')()
    assert [
        ('gocept.template_rewrite.pagetemplates', logging.ERROR,
         'Parsing error in broken.pt:2 \n\t'
         '<p tal:attributes="color python: a\n'
         '                                  or b.has_key(\'test\')">'),
        ('gocept.template_rewrite.pagetemplates', logging.ERROR,
         'Parsing error in broken.pt:5 \n\t'
         '<p tal:attributes="color python: or or">'),
    ] == caplog.record_tuples
