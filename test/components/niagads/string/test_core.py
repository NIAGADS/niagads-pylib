from niagads.string import core
from niagads.string.core import reverse


def test_sample():
    assert core is not None


def test_reverse():
    assert reverse('abc')