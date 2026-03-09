"""Streamlit application for track metadata form intake and serialization."""

import json
import inspect
from typing import get_args

from niagads.genomics.sequence.assembly import Assembly
import streamlit as st
from pydantic import ValidationError
from pydantic.fields import PydanticUndefined

from niagads.api.common.models.datasets.track import Track
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomicsdb_service.utilities.track_metadata_builder.forms import (
    PydanticFormGenerator,
)


def get_enum_values(enum_type):
    try:
        return enum_type.list(to_lower=True)
    except:
        return enum_type.list()


def get_enum_type(field_type) -> type | None:
    """Extract CaseInsensitiveEnum type from field annotation.

    Args:
        field_type: The field type annotation to check.

    Returns:
        The enum type if found, None otherwise.
    """
    # Check if it's a direct enum type
    if inspect.isclass(field_type) and issubclass(field_type, CaseInsensitiveEnum):
        return field_type

    # Check if it's Optional[EnumType]
    args = get_args(field_type)
    for arg in args:
        if (
            arg is not type(None)
            and inspect.isclass(arg)
            and issubclass(arg, CaseInsensitiveEnum)
        ):
            return arg

    return None


def get_widget_for_field(field_name: str, field_info, field_type: str) -> tuple:
    """Get Streamlit widget and return user input for a given field.

    Args:
        field_name: Name of the field.
        field_info: Pydantic FieldInfo object.
        field_type: String representation of the field type.

    Returns:
        Tuple of (field_name, user_input_value).
    """
    label = field_info.title or field_name.replace("_", " ").title()
    help_text = field_info.description or None

    # Field is required only if it has no default (PydanticUndefined)
    is_required = field_info.default is PydanticUndefined
    if is_required:
        label = f"{label} *"

    # Get default value, avoiding PydanticUndefined
    default_value = (
        None if field_info.default is PydanticUndefined else field_info.default
    )

    if field_name == "description":
        value = st.text_area(
            label,
            value="",
        )
        return field_name, value

    # Check for enum fields
    enum_type = get_enum_type(field_info.annotation)
    if enum_type is not None:
        options = get_enum_values(enum_type)
        value = st.selectbox(
            label,
            options=options,
            index=(
                None
                if default_value is None
                else options.index(default_value) if default_value in options else None
            ),
            help=help_text,
        )
        return field_name, value

    if "bool" in field_type:
        value = st.checkbox(label, value=default_value or False, help=help_text)
        return field_name, value

    if "int" in field_type:
        value = st.number_input(
            label,
            value=default_value,
            step=1,
            help=help_text,
        )
        return field_name, value

    if "float" in field_type:
        value = st.number_input(
            label,
            value=default_value,
            step=0.01,
            help=help_text,
        )
        return field_name, value

    if "List" in field_type or "list" in field_type:
        value = st.text_area(
            label,
            value=default_value or "",
            help=(
                f"{help_text} - enter as comma or newline separated list"
                if help_text
                else "enter as comma or newline separated list"
            ),
        )
        return field_name, value

    # Default: StringField
    value = st.text_input(label, value=default_value or "", help=help_text)
    return field_name, value


def process_form_data(data: dict) -> dict:
    """Process form data to convert string values to appropriate types.

    Args:
        data: Dictionary of form field names to values.

    Returns:
        Dictionary with values converted to appropriate types for Track model.
    """
    processed = {}

    for field_name, field_info in Track.model_fields.items():
        field_type = field_info.annotation

        if field_name not in data:
            continue

        value = data[field_name]

        # Handle bool - just use the value as-is
        if "bool" in str(field_type):
            processed[field_name] = value
            continue

        # Skip empty/None values
        if value is None or value == "":
            processed[field_name] = None
            continue

        # Handle int
        if "int" in str(field_type):
            processed[field_name] = int(value)
            continue

        # Handle float
        if "float" in str(field_type):
            processed[field_name] = float(value)
            continue

        # Handle list - parse comma or newline separated
        if "List" in str(field_type):
            processed[field_name] = [
                v.strip() for v in value.replace("\n", ",").split(",") if v.strip()
            ]
            continue

        # Default: keep as string
        processed[field_name] = value

    return processed


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Track Metadata Builder",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Track Metadata Builder")
    st.markdown("Enter track metadata below.")

    # Center and style the form
    st.markdown(
        """
        <style>
            [data-testid="stForm"] {
                max-width: 600px;
                margin: 0 auto;
                padding: 0 20px 20px 20px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Generate form from Track model
    generator = PydanticFormGenerator(exclude_pydantic_models=True)
    form_class = generator.generate_form_class(Track)

    # Create form
    with st.form("track_metadata_form", clear_on_submit=True):
        st.subheader("Metadata Fields")

        # Dynamically render fields - use form_class._fields to get filtered fields
        form_data = {}
        form_instance = form_class()
        for field_name in form_instance._fields:
            field_info = Track.model_fields[field_name]
            field_type = field_info.annotation

            field_name_result, value = get_widget_for_field(
                field_name, field_info, str(field_type)
            )
            form_data[field_name_result] = value

        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("Submit", type="primary")
        with col2:
            st.form_submit_button("Reset", type="secondary")

    # Handle form submission
    if submitted:
        try:
            # Validate required fields first
            validation_errors = []
            for field_name, field_info in Track.model_fields.items():
                if field_info.default is PydanticUndefined:
                    # This is a required field
                    if (
                        field_name not in form_data
                        or form_data[field_name] is None
                        or form_data[field_name] == ""
                    ):
                        validation_errors.append(
                            f"**{field_name}**: This field is required."
                        )

            if validation_errors:
                st.error("❌ Validation failed:")
                for error in validation_errors:
                    st.error(f"  - {error}")
            else:
                # Process and validate
                processed_data = process_form_data(form_data)
                track = Track(**processed_data)

                # Success
                st.success("✓ Track metadata validated successfully!")

                # Show JSON preview
                st.subheader("Generated JSON")
                json_output = track.model_dump(mode="json")
                st.json(json_output)

                # Download button
                file_name = f"{json_output.get('track_id', 'track')}-metadata.json"
                st.download_button(
                    label="Download as JSON",
                    data=json.dumps(json_output, indent=2),
                    file_name=file_name,
                    mime="application/json",
                )

        except ValidationError as e:
            st.error("❌ Validation failed:")
            for error in e.errors():
                st.error(f"  - **{error['loc'][0]}**: {error['msg']}")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
