# import runpy
# import sys
# import pytest

from niagads.metadata_validator_tool import core


def test_sample():
    assert core is not None


# @pytest.mark.parametrize("template", ["file_manifest"])
# @pytest.mark.parametrize("metadataFileType", ["file_manifest"])
# def test_templated_file_manifest(capsys, monkeypatch, template, metadataFileType):
#     with monkeypatch.context() as m:
#         m.setattr(
#             sys,
#             "argv",
#             [
#                 sys.argv[0],
#                 "--template",
#                 template,
#                 "--metadataFileType",
#                 metadataFileType,
#             ],
#         )
#         runpy.run_module("niagads.metadata_validator_tool.core", run_name="__main__")
#         captured = capsys.readouterr()
#         assert captured.out != ""
