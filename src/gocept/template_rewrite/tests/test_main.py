from ..dtml import DTMLRegexRewriter
from ..main import main
from ..pagetemplates import PTParseError
from ..pagetemplates import PTParserRewriter
import pathlib
import pkg_resources
import pytest
import shutil


FIXTURE_DIR = pkg_resources.resource_filename(
    'gocept.template_rewrite.tests', 'fixture')


@pytest.fixture(scope='function')
def files(tmpdir):
    """Create a copy of the fixture directory in a temporary directory."""
    dir = str(tmpdir.join('fixture'))
    shutil.copytree(FIXTURE_DIR, dir)
    yield pathlib.Path(dir)


def test_main__main__1(files, caplog):
    """It converts all files in the given directory."""
    testfiles = files / 'sane'
    main([str(testfiles)])
    res_files = [x.name for x in testfiles.iterdir()]
    assert ['README.txt',
            'broken.html',
            'one.pt',
            'three.xpt',
            'two.dtml'] == sorted(res_files)
    assert caplog.text.count('Processing') == 4


def test_main__main__2(files):
    """It does not touch the original files on `--keep-files`."""
    testfiles = files / 'sane'
    main([str(testfiles), '--keep-files'])
    res_files = [x.name for x in testfiles.iterdir()]
    assert [
        'README.txt',
        'broken.html',
        'broken.html.out',
        'one.pt',
        'one.pt.out',
        'three.xpt',
        'three.xpt.out',
        'two.dtml',
        'two.dtml.out',
    ] == sorted(res_files)
    # Source files are not changed:
    orig_path = pathlib.Path(FIXTURE_DIR) / 'sane'
    for file in orig_path.iterdir():
        source = file.read_text()
        dest = testfiles.joinpath(file.name).read_text()
        assert dest == source


def test_main__main__3a(files, caplog):
    """It stops if encountering a parsing error."""
    with pytest.raises(PTParseError):
        assert main([str(files)])


def test_main__main__3b(files, caplog):
    """It reports parsing errors on `--collect-errors`."""
    main([str(files), '--collect-errors'])
    res_files = [x.name for x in files.rglob('*.*')]
    assert ['README.txt',
            'broken.html',
            'broken.html.out',
            'broken.pt',
            'broken2.pt',
            'broken3.pt',
            'one.pt',
            'one.pt.out',
            'three.xpt',
            'three.xpt.out',
            'two.dtml',
            'two.dtml.out',
            ] == sorted(res_files)
    assert caplog.text.count('Processing') == 7
    assert caplog.text.count('Parsing error') == 4
    # Source files are not changed:
    for file in pathlib.Path(FIXTURE_DIR).rglob('*.*'):
        source = file.read_text()
        dest = files.joinpath(str(file)).read_text()
        assert dest == source


def test_main__main__4(files, caplog):
    """It accepts a list of files as argument."""
    main([str(files / 'sane/one.pt'), str(files / 'sane/two.dtml')])
    assert caplog.text.count('Processing') == 2


def test_main__main__5(files, mocker):
    """It treats all files as PageTemplate on `--force=pt`."""
    mocker.spy(DTMLRegexRewriter, '__call__')
    mocker.spy(PTParserRewriter, '__call__')
    main([str(files / 'sane'), '--force=pt'])
    assert DTMLRegexRewriter.__call__.call_count == 0
    assert PTParserRewriter.__call__.call_count == 5


def test_main__main__6(files, mocker):
    """It treats all files as DocumentTemplate on `--force=dtml`."""
    mocker.spy(DTMLRegexRewriter, '__call__')
    mocker.spy(PTParserRewriter, '__call__')
    main([str(files / 'sane'), '--force=dtml'])
    assert DTMLRegexRewriter.__call__.call_count == 5
    assert PTParserRewriter.__call__.call_count == 0


def test_main__PTParserRewriter__1(files, mocker):
    """It skips rewrite of a file without `tal:` in content."""
    mocker.spy(PTParserRewriter, 'rewrite_zpt')
    main([str(files / 'sane/broken.html'), str(files / 'sane/one.pt')])
    # broken.html is not rewritten
    assert PTParserRewriter.rewrite_zpt.call_count == 1
