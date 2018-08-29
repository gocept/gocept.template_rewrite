from ..lib2to3 import rewrite_using_2to3


def test_lib2to3__rewrite_using_2to3__1():
    """It makes code python 3 ready."""
    res = rewrite_using_2to3('print "Hello world"', None, None, None)
    assert res == 'print("Hello world")'


def test_lib2to3__rewrite_using_2to3__2():
    """It does not rewrite `.next()`, i.e. omits fixer `fix_next`."""
    res = rewrite_using_2to3('iter.next()', None, None, None)
    assert res == 'iter.next()'
