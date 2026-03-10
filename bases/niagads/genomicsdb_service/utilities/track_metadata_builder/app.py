"""Streamlit application for track metadata form intake and serialization."""

import inspect
import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import get_args, get_origin

import streamlit as st
from niagads.api.common.models.datasets.track import Track
from niagads.common.models.ontologies import OntologyTerm
from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomics.sequence.assembly import Assembly
from niagads.genomicsdb_service.utilities.track_metadata_builder.forms import (
    PydanticFormGenerator,
)
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import ValidationError
from pydantic.fields import PydanticUndefined


# Load ontology reference into memory
@st.cache_resource
def load_ontology_reference():
    """Load ontology reference table into memory.

    Returns:
        dict mapping field_name -> list of dicts with keys: term, curie
    """
    reference_file = Path(__file__).parent / "ontology_reference.txt"
    reference_by_field = {}

    with open(reference_file) as f:
        # Skip header
        next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            term, curie, field = parts[0], parts[1], parts[2]

            if field not in reference_by_field:
                reference_by_field[field] = []
            reference_by_field[field].append({"term": term, "curie": curie})

    return reference_by_field


ONTOLOGY_REFERENCE = load_ontology_reference()


def validate_ontology_term(input_value: str, field_name: str) -> dict:
    """Validate and convert user input to OntologyTerm dict.

    Handles term names, CURIEs, and creates placeholder terms as needed.

    Args:
        input_value: User input (term name or CURIE).
        field_name: Field name for reference table lookup.

    Returns:
        Dictionary with term and curie ready for OntologyTerm instantiation.

    Raises:
        ValueError: If validation fails.
    """
    input_value = input_value.strip()

    # Step 1: Detect term vs CURIE
    is_curie = matches(input_value, RegularExpressions.ONTOLOGY_TERM_CURIE)

    # Step 2: Lookup in reference table (only if it's a term, not a CURIE)
    if not is_curie:
        # Get reference terms for this field
        ref_terms = ONTOLOGY_REFERENCE.get(field_name, [])
        for ref_term in ref_terms:
            if ref_term["term"].lower() == input_value.lower():
                # Found in reference - return term and curie
                return {
                    "term": ref_term["term"],
                    "curie": ref_term["curie"],
                }

    # Step 3: Handle not-in-reference
    if is_curie:
        # Input is a CURIE - create OntologyTerm with curie only
        try:
            ontology_term = OntologyTerm(curie=input_value)
            return ontology_term.model_dump()
        except ValidationError as e:
            raise ValueError(f"Invalid CURIE '{input_value}': {str(e)}")
    else:
        # Input is a term not in reference - create placeholder entry
        return {
            "term": input_value,
            "curie": "INTAKE:needs_review",
            "is_placeholder": True,
        }


def get_enum_values(enum_type):
    try:
        return enum_type.list(to_lower=True)
    except:
        return enum_type.list()


def get_enum_type(field_type) -> type | None:
    """Extract CaseInsensitiveEnum type from field annotation.

    Recursively unwraps nested generics like Optional[Set[Enum]] to find the enum.

    Args:
        field_type: The field type annotation to check.

    Returns:
        The enum type if found, None otherwise.
    """
    # Check if it's a direct enum type
    if inspect.isclass(field_type) and issubclass(field_type, CaseInsensitiveEnum):
        return field_type

    # Recursively check nested generics
    origin = get_origin(field_type)
    args = get_args(field_type)

    for arg in args:
        if arg is type(None):
            continue

        # If arg is a direct enum class, return it
        if inspect.isclass(arg):
            try:
                if issubclass(arg, CaseInsensitiveEnum):
                    return arg
            except TypeError:
                pass

        # If arg is another generic type (e.g., Set[Enum]), recurse into it
        if get_origin(arg) is not None:
            result = get_enum_type(arg)
            if result is not None:
                return result

    return None


def get_ontology_term_enum_type(field_type) -> type | None:
    """Extract OntologyTerm enum type from field annotation.

    Recursively unwraps nested generics to find OntologyTerm enums specifically.
    Filters out CaseInsensitiveEnum and other non-OntologyTerm enums.

    Args:
        field_type: The field type annotation to check.

    Returns:
        The OntologyTerm enum type if found, None otherwise.
    """
    # Check if it's a direct enum type
    if inspect.isclass(field_type):
        try:
            if issubclass(field_type, Enum) and not issubclass(
                field_type, CaseInsensitiveEnum
            ):
                # Check if it's an OntologyTerm enum by verifying values have .term attribute
                if len(list(field_type)) > 0 and hasattr(
                    list(field_type)[0].value, "term"
                ):
                    return field_type
        except TypeError:
            pass

    # Recursively check nested generics
    origin = get_origin(field_type)
    args = get_args(field_type)

    for arg in args:
        if arg is type(None):
            continue

        # If arg is a direct enum class, return it
        if inspect.isclass(arg):
            try:
                if issubclass(arg, Enum) and not issubclass(arg, CaseInsensitiveEnum):
                    # Check if it's an OntologyTerm enum
                    if len(list(arg)) > 0 and hasattr(list(arg)[0].value, "term"):
                        return arg
            except TypeError:
                pass

        # If arg is another generic type, recurse into it
        if get_origin(arg) is not None:
            result = get_ontology_term_enum_type(arg)
            if result is not None:
                return result

    return None


def is_ontology_term_list(field_type) -> bool:
    """Check if a field type is List[OntologyTerm], Optional[List[OntologyTerm]], etc.

    Args:
        field_type: The field type annotation to check.

    Returns:
        True if the field is a list of OntologyTerm objects, False otherwise.
    """
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Handle Optional[List[OntologyTerm]] - origin is Union, args are (List[OntologyTerm], type(None))
    if origin is not None:
        # For Union types (e.g., Optional), check each arg
        for arg in args:
            if arg is type(None):
                continue
            # Recursively check if this arg is a List[OntologyTerm]
            if is_ontology_term_list(arg):
                return True

    # Handle direct List[OntologyTerm]
    if origin is list:
        for arg in args:
            if arg is type(None):
                continue
            if "OntologyTerm" in str(arg):
                return True

    return False


def render_composite_field(
    field_name: str, field_info, composite_form_class, model_class
) -> dict:
    """Render a composite Pydantic model field as an expandable section.

    Args:
        field_name: Name of the composite field.
        field_info: Pydantic FieldInfo object.
        composite_form_class: WTForms form class for the nested model.
        model_class: The Pydantic model class for the composite field.

    Returns:
        Dictionary with nested field data.
    """
    label = field_info.title or field_name.replace("_", " ").title()
    is_required = field_info.default is PydanticUndefined
    if is_required:
        label = f"{label} *"

    nested_data = {}

    # Create an expandable section for the composite field
    with st.expander(label, expanded=is_required):
        if field_info.description:
            st.caption(field_info.description)

        # Render nested form fields
        nested_form_instance = composite_form_class()
        for nested_field_name in nested_form_instance._fields:
            nested_field_info = model_class.model_fields[nested_field_name]
            nested_field_type = nested_field_info.annotation

            nested_field_result, nested_value = get_widget_for_field(
                nested_field_name, nested_field_info, str(nested_field_type)
            )
            nested_data[nested_field_result] = nested_value

    return {field_name: nested_data}


def render_repeatable_composite_field(
    field_name: str, field_info, composite_form_class, model_class
) -> dict:
    """Render a repeatable composite field (List[Model]) with add/remove buttons.

    Uses st.session_state to manage list of entries.

    Args:
        field_name: Name of the composite field (e.g., 'curation_history').
        field_info: Pydantic FieldInfo object.
        composite_form_class: WTForms form class for individual items.
        model_class: The Pydantic model class for list items.

    Returns:
        Dictionary with field_name mapped to list of nested dicts.
    """
    label = field_info.title or field_name.replace("_", " ").title()
    is_required = field_info.default is PydanticUndefined
    if is_required:
        label = f"{label} *"

    # Initialize session state for this list field if not exists
    session_key = f"_list_{field_name}_entries"
    if session_key not in st.session_state:
        # Start with one empty entry by default
        st.session_state[session_key] = [{}]
        st.session_state[f"_list_{field_name}_counter"] = 0

    # Create an expandable section for the repeatable field
    with st.expander(label, expanded=is_required):
        if field_info.description:
            st.caption(field_info.description)

        # Display each entry
        entries_data = []
        for idx, entry in enumerate(st.session_state[session_key]):
            with st.container(border=True):
                # Render fields for this entry (no remove button here - handled outside form)
                entry_data = {}
                nested_form_instance = composite_form_class()
                for nested_field_name in nested_form_instance._fields:
                    nested_field_info = model_class.model_fields[nested_field_name]
                    nested_field_type = nested_field_info.annotation

                    # Get default value from existing entry if available
                    default_val = entry.get(nested_field_name)

                    nested_field_result, nested_value = get_widget_for_field(
                        nested_field_name,
                        nested_field_info,
                        str(nested_field_type),
                        default_value=default_val,
                        widget_key=f"_{field_name}_{idx}",
                    )
                    entry_data[nested_field_result] = nested_value

                entries_data.append(entry_data)

        # Return collected entries
        return {field_name: entries_data}


def get_widget_for_field(
    field_name: str,
    field_info,
    field_type: str,
    default_value=None,
    widget_key: str = "",
) -> tuple:
    """Get Streamlit widget and return user input for a given field.

    Args:
        field_name: Name of the field.
        field_info: Pydantic FieldInfo object.
        field_type: String representation of the field type.
        default_value: Default value for the widget.
        widget_key: Optional unique key suffix for widgets (e.g., for repeatable fields).

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
    # Use passed default_value if provided, otherwise use field_info.default
    if default_value is None:
        default_value = (
            None if field_info.default is PydanticUndefined else field_info.default
        )

    if field_name == "description":
        value = st.text_area(
            label,
            value="",
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    # Check for List[OntologyTerm] fields - multiselect with ontology reference
    if is_ontology_term_list(field_info.annotation):
        # Get reference terms for this field
        ref_terms = ONTOLOGY_REFERENCE.get(field_name, [])
        options = [term["term"] for term in ref_terms]

        value = st.multiselect(
            label,
            options=options,
            default=default_value or [],
            help=help_text,
            accept_new_options=True,
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    # Check for Set types first (before generic enum check)
    if "Set" in field_type or "set" in field_type:
        # Check if this is a Set[EnumType]
        enum_type = get_enum_type(field_info.annotation)
        if enum_type is not None:
            # Checkboxes for enum sets
            options = get_enum_values(enum_type)
            default_selected = set()
            if default_value and isinstance(default_value, set):
                default_selected = default_value

            # Render checkboxes with label
            st.markdown(
                f"<p style='font-size: 14px;'>{label}</p>",
                unsafe_allow_html=True,
            )

            selected = []
            for option in options:
                if st.checkbox(
                    option,
                    value=option in default_selected,
                    key=f"{field_name}_{option}{widget_key}",
                ):
                    selected.append(option)

            return field_name, selected
        else:
            # Text area for non-enum sets
            value = st.text_area(
                label,
                value=default_value or "",
                help=(
                    f"{help_text} - enter as comma or newline separated values"
                    if help_text
                    else "enter as comma or newline separated values"
                ),
                key=f"{field_name}{widget_key}" if widget_key else None,
            )
            return field_name, value

    # Check for CaseInsensitiveEnum fields first
    case_insensitive_enum_type = get_enum_type(field_info.annotation)
    if case_insensitive_enum_type is not None:
        options = get_enum_values(case_insensitive_enum_type)
        default_index = None
        if default_value is not None:
            try:

                if case_insensitive_enum_type is Assembly:
                    # Assembly values are already the correct case
                    default_index = options.index(default_value.value)
                else:
                    # Other CaseInsensitiveEnum types may use lowercase
                    default_index = options.index(default_value.value.lower())
            except (ValueError, IndexError, AttributeError):
                pass

        value = st.selectbox(
            label,
            options=options,
            index=default_index,
            help=help_text,
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    # Check for OntologyTerm Enum types
    ontology_term_enum_type = get_ontology_term_enum_type(field_info.annotation)
    if ontology_term_enum_type is not None:
        # Get the options from the enum's list() method
        options = ontology_term_enum_type.list()

        # Find the default option if value exists
        default_index = None
        if default_value is not None:
            # Check if this is an OntologyTerm enum (has .term attribute)
            if hasattr(default_value, "term"):
                try:
                    default_index = options.index(default_value.term)
                except (ValueError, IndexError):
                    pass

        value = st.selectbox(
            label,
            options=options,
            index=default_index,
            help=help_text,
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    if "bool" in field_type:
        value = st.checkbox(
            label,
            value=default_value or False,
            help=help_text,
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    if "int" in field_type:
        value = st.number_input(
            label,
            value=default_value,
            step=1,
            help=help_text,
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    if "float" in field_type:
        value = st.number_input(
            label,
            value=default_value,
            step=None,
            help=help_text,
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    if "date" in field_type.lower():
        value = st.date_input(
            label,
            value=default_value,
            help=help_text,
            key=f"{field_name}{widget_key}" if widget_key else None,
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
            key=f"{field_name}{widget_key}" if widget_key else None,
        )
        return field_name, value

    # Default: StringField
    value = st.text_input(
        label,
        value=default_value or "",
        help=help_text,
        key=f"{field_name}{widget_key}" if widget_key else None,
    )
    return field_name, value


def is_nested_form_empty(nested_data: dict, nested_model_class) -> bool:
    """Check if a nested form has all null or default values.

    Args:
        nested_data: Dictionary of processed nested field values.
        nested_model_class: Pydantic model class for the nested structure.

    Returns:
        True if all fields are None or only contain default values, False otherwise.
    """
    if not nested_data:
        return True

    for field_name, field_info in nested_model_class.model_fields.items():
        if field_name not in nested_data:
            continue

        value = nested_data[field_name]

        # Check if value is not None and not empty
        if value is not None and value != "" and value != []:
            return False

    return True


def get_list_model_type(field_type) -> type | None:
    """Extract the model type from a List[Model] annotation.

    Args:
        field_type: The field type annotation.

    Returns:
        The model class if field is List[Model], None otherwise.
    """
    origin = get_origin(field_type)
    if origin is list:
        args = get_args(field_type)
        if args and hasattr(args[0], "model_fields"):
            return args[0]
    return None


def process_form_data(data: dict, model_class=Track) -> dict:
    """Process form data to convert string values to appropriate types.

    Recursively processes nested dicts by passing the appropriate model class context.

    Args:
        data: Dictionary of form field names to values.
        model_class: Pydantic model class to validate fields against (defaults to Track).

    Returns:
        Dictionary with values converted to appropriate types for the model.
    """

    processed = {}

    for field_name, field_info in model_class.model_fields.items():
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

        # Handle nested dicts (composite fields) - recursively process them
        if isinstance(value, dict):
            # Get the nested model class from the field type
            nested_model_class = None
            origin = get_origin(field_type)

            # Handle Optional[Model] or Model directly
            if origin is not None:
                # For Optional[Model], get the non-None type
                args = get_args(field_type)
                for arg in args:
                    if arg is not type(None) and hasattr(arg, "model_fields"):
                        nested_model_class = arg
                        break
            elif hasattr(field_type, "model_fields"):
                # Direct model type
                nested_model_class = field_type

            if nested_model_class:
                processed_nested = process_form_data(value, nested_model_class)
                # For optional nested forms, check if empty and set to None
                if is_nested_form_empty(processed_nested, nested_model_class):
                    # Only set to None if this is an optional field (provenance is required)
                    if field_name != "provenance":
                        processed[field_name] = None
                    else:
                        processed[field_name] = processed_nested
                else:
                    processed[field_name] = processed_nested
            else:
                # Fallback: just pass through the dict
                processed[field_name] = value
            continue

        # Handle List[Model] types (e.g., curation_history: List[CurationEvent])
        list_model_type = get_list_model_type(field_type)
        if list_model_type is not None and isinstance(value, list):
            if not value or len(value) == 0:
                processed[field_name] = None
                continue

            # Process each item in the list
            processed_items = []
            for item in value:
                if isinstance(item, dict):
                    processed_item = process_form_data(item, list_model_type)
                    # Only include non-empty items
                    if not is_nested_form_empty(processed_item, list_model_type):
                        processed_items.append(processed_item)

            # Set to None if no valid items remain, otherwise keep the list
            processed[field_name] = processed_items if processed_items else None
            continue

        # Handle OntologyTerm Enum types - convert term string to enum member
        ontology_term_enum_type = get_ontology_term_enum_type(field_type)
        if ontology_term_enum_type is not None:
            # Find the enum member with the matching term value
            for member in ontology_term_enum_type:
                if member.value.term == value:
                    processed[field_name] = member.value
                    break
            continue

        # Handle int
        if "int" in str(field_type):
            processed[field_name] = int(value)
            continue

        # Handle float
        if "float" in str(field_type):
            processed[field_name] = float(value)
            continue

        # Handle List[OntologyTerm] - convert each term/CURIE to OntologyTerm dict
        if is_ontology_term_list(field_type):
            # Value should be a list from multiselect or empty
            if not value or (isinstance(value, list) and len(value) == 0):
                processed[field_name] = None
                continue

            ontology_terms = []
            for item in value:
                try:
                    term_dict = validate_ontology_term(item, field_name)
                    ontology_terms.append(term_dict)
                except ValueError as e:
                    raise ValueError(f"Field '{field_name}', item '{item}': {str(e)}")

            processed[field_name] = ontology_terms
            continue

        # Handle list - parse comma or newline separated
        if "List" in str(field_type):
            processed[field_name] = [
                v.strip() for v in value.replace("\n", ",").split(",") if v.strip()
            ]
            continue

        # Handle set - can be list from multiselect or string from text area
        if "Set" in str(field_type):
            # If value is already a list (from multiselect), use it directly
            if isinstance(value, list):
                items = value
            else:
                # Parse comma or newline separated string
                items = [
                    v.strip() for v in value.replace("\n", ",").split(",") if v.strip()
                ]

            # Check if set contains enum types
            origin = get_origin(field_type)
            if origin is set:
                args = get_args(field_type)
                if args:
                    item_type = args[0]
                    # Try to convert to enum if the contained type is an enum
                    try:
                        if isinstance(item_type, type) and issubclass(item_type, Enum):
                            items = [item_type(item.upper()) for item in items]
                    except (ValueError, TypeError):
                        # If conversion fails, keep as strings
                        pass
            processed[field_name] = set(items)
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
    generator = PydanticFormGenerator()
    form_class, composite_fields_metadata = generator.generate_form_class(
        Track
    )  # Create form
    with st.form("track_metadata_form", enter_to_submit=False):
        st.subheader("Metadata Fields")

        # Dynamically render fields - use form_class._fields to get filtered fields
        form_data = {}
        form_instance = form_class()
        for field_name in form_instance._fields:
            form_field = form_instance._fields[field_name]
            field_info = Track.model_fields[field_name]
            field_type = field_info.annotation

            # Check if this is a composite field
            if field_name in composite_fields_metadata:
                composite_info = composite_fields_metadata[field_name]
                composite_model = composite_info["model"]
                composite_form_class = composite_info["form_class"]

                # Check if this is a repeatable field (List[Model])
                if composite_info.get("is_repeatable", False):
                    nested_data = render_repeatable_composite_field(
                        field_name, field_info, composite_form_class, composite_model
                    )
                else:
                    nested_data = render_composite_field(
                        field_name, field_info, composite_form_class, composite_model
                    )
                form_data.update(nested_data)
            else:
                field_name_result, value = get_widget_for_field(
                    field_name, field_info, str(field_type)
                )
                form_data[field_name_result] = value

        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("Submit", type="primary")
        with col2:
            st.form_submit_button("Reset", type="secondary")

    # Render "Add" and "Remove" buttons for repeatable fields outside form context
    st.divider()
    for field_name, composite_info in composite_fields_metadata.items():
        if composite_info.get("is_repeatable", False):
            composite_model = composite_info["model"]
            session_key = f"_list_{field_name}_entries"
            field_info = Track.model_fields[field_name]
            field_label = field_info.title or field_name.replace("_", " ").title()

            # Create a section for this repeatable field's controls
            with st.expander(
                f"🛠️ Manage {field_label}",
                expanded=False,
            ):
                # Add button
                if st.button(
                    f"➕ Add {composite_model.__name__}",
                    key=f"add_{field_name}",
                    help=f"Add a new {composite_model.__name__}",
                ):
                    st.session_state[session_key].append({})
                    st.rerun()

                # Render remove buttons for each entry in this field
                if st.session_state[session_key]:
                    st.markdown(f"**Remove {composite_model.__name__}:**")
                    for idx in range(len(st.session_state[session_key])):
                        if st.button(
                            f"🗑️ Remove entry #{idx + 1}",
                            key=f"remove_{field_name}_{idx}",
                            help=f"Remove {composite_model.__name__} entry #{idx + 1}",
                        ):
                            st.session_state[session_key].pop(idx)
                            st.rerun()

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
                field_path = ".".join(str(loc) for loc in error["loc"])
                st.error(f"  - **{field_path}**: {error['msg']}")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
