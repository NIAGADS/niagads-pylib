from niagads.string_utils import core
from niagads.string_utils.core import reverse


def test_sample():
    assert core is not None


def test_reverse():
    assert reverse('abc')