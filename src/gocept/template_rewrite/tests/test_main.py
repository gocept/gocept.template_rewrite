from ..main import main
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
    assert ['README.txt',
            'broken.pt',
            'one.pt',
            'two.dtml'] == sorted(x.name for x in files.iterdir())
    assert caplog.text.count('Processing') == 3
    assert caplog.text.count('Parsing error') == 1


def test_main__main__2(files):
    """It does not touch the original files on `--keep-files`."""
    main([str(files), '--keep-files'])
    assert [
        'README.txt',
        'broken.pt',
        'broken.pt.out',
        'one.pt',
        'one.pt.out',
        'two.dtml',
        'two.dtml.out',
    ] == sorted(x.name for x in files.iterdir())
    # Source files are not changed:
    for file in pathlib.Path(FIXTURE_DIR).iterdir():
        source = file.read_text()
        dest = files.joinpath(file.name).read_text()
        assert dest == source


def test_main__main__3(files, caplog):
    """It does only report errors on `--only-check-syntax`."""
    main([str(files), '--only-check-syntax'])
    assert ['README.txt',
            'broken.pt',
            'one.pt',
            'two.dtml'] == sorted([x.name for x in files.iterdir()])
    assert caplog.text.count('Processing') == 0
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
