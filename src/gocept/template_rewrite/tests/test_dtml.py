import gocept.template_rewrite.dtml
import pytest


DTML_VAR_EXPRESSION = """
//  Use some dthml-var without expression
#proc yaxis:
  label: <dtml-var xaxis>
  labeldetails: adjust=-0.1
  stubs: datafields 1
  tics: none
  axisline: none

<dtml-in yaxis_parts prefix="a">

//  ... an some with expression
#proc bars
  horizontalbars: yes
  color: <dtml-var expr="plot_colors[a_index]">
  lenfield: <dtml-var expr="a_index+2">
  cluster: <dtml-var expr="a_index+1"> / <dtml-var expr="len(yaxis_cols)">
  barwidth: 0.1
  legendlabel: <dtml-var a_item>

</dtml-in>"""


dtml_elif_expression = r"""
<dtml-var tex_header>
<dtml-in data mapping><dtml-in codedata mapping>

\begin{document}

\vspace*{5mm}

\begin{center}
\textbf{\Large{Header}} \\
\end{center}

%%Some code generation
<dtml-var expr="esc_tex(title)">
\par\nobreak\medskip\nobreak
<dtml-var expr="tex_code(code, lwmm=.4, heightmm=16, coding=coding)">
\par\nobreak
<dtml-var expr="esc_tex(code)">

\begin{center}
<dtml-if expr="foto == None">
 Kein Foto hinzugefügt
<dtml-elif expr="foto == 'Kein Foto erzeugt'">
 Kein Foto hinzugefügt
<dtml-else>
\begin{center}
Something else
\end{center}
</dtml-if>
\end{center}

\end{document}
</dtml-in>
</dtml-in>"""

dtml_elif_expectation = r"""
<dtml-var tex_header>
<dtml-in data mapping><dtml-in codedata mapping>

\begin{document}

\vspace*{5mm}

\begin{center}
\textbf{\Large{Header}} \\
\end{center}

%%Some code generation
<dtml-var expr="rewritten">
\par\nobreak\medskip\nobreak
<dtml-var expr="rewritten">
\par\nobreak
<dtml-var expr="rewritten">

\begin{center}
<dtml-if expr="rewritten">
 Kein Foto hinzugefügt
<dtml-elif expr="rewritten">
 Kein Foto hinzugefügt
<dtml-else>
\begin{center}
Something else
\end{center}
</dtml-if>
\end{center}

\end{document}
</dtml-in>
</dtml-in>"""


let_expression = r"""
<dtml-let foo="foo.replace(';','')"
          bar="bar.replace(';','')"
          baz="baz.replace(';','')">
"""

let_expectation = r"""
<dtml-let foo="rewritten"
          bar="rewritten"
          baz="rewritten">
"""


def test_dtml__DTMLRegexRewriter____call____1():
    """It returns the initial template from the identity function."""
    rw = gocept.template_rewrite.dtml.DTMLRegexRewriter(
        DTML_VAR_EXPRESSION, lambda x, **kw: x)
    result = rw()

    assert result == DTML_VAR_EXPRESSION


def test_dtml__DTMLRegexRewriter____call____2():
    """It rewrites the expression values of the dtml."""
    rw = gocept.template_rewrite.dtml.DTMLRegexRewriter(
        DTML_VAR_EXPRESSION, lambda x, **kw: "rewritten")
    result = rw()

    expected = """
//  Use some dthml-var without expression
#proc yaxis:
  label: <dtml-var xaxis>
  labeldetails: adjust=-0.1
  stubs: datafields 1
  tics: none
  axisline: none

<dtml-in yaxis_parts prefix="a">

//  ... an some with expression
#proc bars
  horizontalbars: yes
  color: <dtml-var expr="rewritten">
  lenfield: <dtml-var expr="rewritten">
  cluster: <dtml-var expr="rewritten"> / <dtml-var expr="rewritten">
  barwidth: 0.1
  legendlabel: <dtml-var a_item>

</dtml-in>"""

    assert result == expected


@pytest.mark.parametrize('input, expected', [
    ('<dtml-var expr="plot_colors[a_index]">', '<dtml-var expr="rewritten">'),
    ('<dtml-var expr="a_index+1"> / <dtml-var expr="len(yaxis_cols)">',
     '<dtml-var expr="rewritten"> / <dtml-var expr="rewritten">'),
    (dtml_elif_expression, dtml_elif_expectation),
    ('<dtml-let letvar="plot_colo[rs]">', '<dtml-let letvar="rewritten">'),
    (let_expression, let_expectation),
])
def test_dtml__DTMLRegexRewriter____call____3(input, expected):
    """It rewrites the expression values of the dtml."""
    rw = gocept.template_rewrite.dtml.DTMLRegexRewriter(
        input, lambda x, **kw: "rewritten")
    assert rw() == expected
