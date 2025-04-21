from niagads.utils import string
from niagads.utils.string import reverse


def test_sample():
    assert string is not None


def test_reverse():
    assert reverse("abc")
