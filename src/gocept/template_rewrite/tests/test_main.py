from ..dtml import DTMLRegexRewriter
from ..main import main
from ..pagetemplates import PTParserRewriter
import pathlib
import pkg_resources
import pytest
import shutil

FIXTURE_DIR = pkg_resources.resource_filename(
    'gocept.template_rewrite.tests', 'fixture')


@pytest.fixture('function')
def files(tmpdir):
    """Create a copy of the fixture directory in a temporary directory."""
    dir = str(tmpdir.join('fixture'))
    shutil.copytree(FIXTURE_DIR, dir)
    yield pathlib.Path(dir)


def test_main__main__1(files, caplog):
    """It converts all files in the given directory."""
    main([str(files)])
    res_files = [x.name for x in files.iterdir()]
    assert ['README.txt',
            'broken.html',
            'broken.pt',
            'one.pt',
            'two.dtml'] == sorted(res_files)
    assert caplog.text.count('Processing') == 4
    assert caplog.text.count('Parsing error') == 1


def test_main__main__2(files):
    """It does not touch the original files on `--keep-files`."""
    main([str(files), '--keep-files'])
    res_files = [x.name for x in files.iterdir()]
    assert [
        'README.txt',
        'broken.html',
        'broken.html.out',
        'broken.pt',
        'broken.pt.out',
        'one.pt',
        'one.pt.out',
        'two.dtml',
        'two.dtml.out',
    ] == sorted(res_files)
    # Source files are not changed:
    for file in pathlib.Path(FIXTURE_DIR).iterdir():
        source = file.read_text()
        dest = files.joinpath(file.name).read_text()
        assert dest == source


def test_main__main__3(files, caplog):
    """It reports parsing errors on `--only-check-syntax`."""
    main([str(files), '--only-check-syntax'])
    res_files = [x.name for x in files.iterdir()]
    assert ['README.txt',
            'broken.html',
            'broken.pt',
            'one.pt',
            'two.dtml'] == sorted(res_files)
    assert caplog.text.count('Processing') == 4
    assert caplog.text.count('Parsing error') == 1
    # Source files are not changed:
    for file in pathlib.Path(FIXTURE_DIR).iterdir():
        source = file.read_text()
        dest = files.joinpath(file.name).read_text()
        assert dest == source


def test_main__main__4(files, caplog):
    """It accepts a list of files as argument."""
    main([str(files / 'broken.pt'), str(files / 'one.pt')])
    assert caplog.text.count('Processing') == 2
    assert caplog.text.count('Parsing error') == 1


def test_main__main__5(files, mocker):
    """It treats all files as PageTemplate on `--force=pt`."""
    mocker.spy(DTMLRegexRewriter, '__call__')
    mocker.spy(PTParserRewriter, '__call__')
    main([str(files), '--force=pt'])
    assert DTMLRegexRewriter.__call__.call_count == 0
    assert PTParserRewriter.__call__.call_count == 5


def test_main__main__6(files, mocker):
    """It treats all files as DocumentTemplate on `--force=dtml`."""
    mocker.spy(DTMLRegexRewriter, '__call__')
    mocker.spy(PTParserRewriter, '__call__')
    main([str(files), '--force=dtml'])
    assert DTMLRegexRewriter.__call__.call_count == 5
    assert PTParserRewriter.__call__.call_count == 0


def test_main__PTParserRewriter__1(files, mocker):
    """It skips rewrite of a file without `tal:` in content."""
    mocker.spy(PTParserRewriter, 'rewrite_zpt')
    main([str(files / 'broken.html'), str(files / 'one.pt')])
    # broken.html is not rewritten
    assert PTParserRewriter.rewrite_zpt.call_count == 1
