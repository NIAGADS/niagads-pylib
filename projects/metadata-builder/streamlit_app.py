from pathlib import Path
import sys

try:
    from niagads.common.track.models.record import TrackRecord
    from niagads.metadata_serializer.app import MetadataSerializationApp
except ModuleNotFoundError:
    # expose monorepo components for Streamlit common cloud deployment
    ROOT = Path(__file__).resolve().parents[2]  # niagads-pylib
    sys.path.append(str(ROOT / "components"))

    from niagads.common.track.models.record import TrackRecord
    from niagads.metadata_serializer.app import MetadataSerializationApp


def main():
    ontology_reference_file = Path(__file__).resolve().parent / "ontology_reference.txt"
    app = MetadataSerializationApp(
        pydantic_model=TrackRecord,
        application_name="GenomicsDB Track Metadata Builder",
        ontology_reference_file=ontology_reference_file,
        download_qualifier="track-metadata",
        debug=False,
    )
    app.run()


if __name__ == "__main__":
    main()
