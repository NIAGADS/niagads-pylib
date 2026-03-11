"""Streamlit application for track metadata form intake and serialization."""

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable, Union
from niagads.common.models.ontologies import OntologyTerm
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
import streamlit as st
from niagads.api.common.models.datasets.track import Track
from niagads.common.core import ComponentBaseMixin
from niagads.genomicsdb_service.utilities.track_metadata_builder.forms import (
    FormMetadata,
    PydanticFormGenerator,
)
from pydantic import ValidationError


class OntologyMap(ComponentBaseMixin):
    def __init__(
        self,
        ontology_reference_file: str,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__map = {}
        self.load_ontology_map(ontology_reference_file)

    # Load ontology reference into memory
    def load_ontology_map(self, reference_file: str):
        """Load ontology reference table into memory.

        Returns:
            dict mapping field_name -> list of dicts with keys: term, curie
        """

        self.__map = {}

        with open(reference_file) as f:
            fields = next(f).strip().split("\t")
            for line in f:
                line = line.strip()
                if not line:
                    continue
                values = line.split("\t")
                entry = dict(zip(fields, values))
                field = entry["field"]
                if field not in self.__map:
                    self.__map[field] = []
                self.__map[field].append(entry)

    def get_field_terms(self, field_name: str, terms_only: bool = False) -> list:
        """Get reference ontology terms for a field."""
        if field_name == "phenotype":
            complete_reference = []
            for field in self.__map.keys():
                complete_reference.extend(self.__map.get(field, {}))
            reference = [v for v in complete_reference if v["is_phenotype"]]

        else:
            reference = self.__map.get(field_name, {})

        if terms_only:
            return [item["term"] for item in reference]
        else:
            return reference

    def get_ontology_term(self, value: str):
        for field_grouped_terms in self.__map.values():
            for t in field_grouped_terms:
                if value == t["term"] or value == t["curie"]:
                    return OntologyTerm(term=t["value"], curie=t["curie"])
        return None


class MetadataBuilderApp(ComponentBaseMixin):
    """Streamlit application for track metadata form intake and serialization."""

    def __init__(
        self,
        pydantic_model: Any,
        application_name: str,
        ontology_reference_file: str,
        debug: bool = False,
        verbose: bool = False,
    ):

        super().__init__(debug=debug, verbose=verbose)
        self.__app_name: str = application_name
        self.__ontology_map: OntologyMap = OntologyMap(ontology_reference_file)
        self.__pydantic_model: Any = pydantic_model
        self.__form_metadata: dict = None
        self.__form_class = None
        self.__renderer: FormRenderer = None

        self.__deserializers: dict = {
            date: self._deserialize_date,
            OntologyTerm: self._deserialize_ontology_term,
        }
        self.__initialize_renderer()

    def __initialize_renderer(self):
        generator = PydanticFormGenerator(
            exclude_pydantic_models=False,
            deserializers=self.__deserializers,
        )
        fc, fm = generator.generate_form_class(self.__pydantic_model)
        self.__form_class = fc
        self.__form_metadata = fm
        # Create renderer
        self.__renderer = FormRenderer(
            self.__form_class,
            self.__form_metadata,
            self.__ontology_map,
            debug=self._debug,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(debug={self._debug}, "
            f"verbose={self._verbose})"
        )

    @staticmethod
    def __remove_entry(idx: int, session_key: str):
        """Callback to remove an entry at the specified index."""
        st.session_state[session_key].pop(idx)

    @staticmethod
    def generate_session_keys(field_name: str) -> tuple[str, str]:
        return (
            f"_list_{field_name}_entries",
            f"_list_{field_name}_counter",
        )

    @staticmethod
    def ensure_repeatable_entries(field_name: str):
        """Ensure repeatable entries are initialized with stable IDs."""
        session_key, counter_key = MetadataBuilderApp.generate_session_keys(field_name)

        if session_key not in st.session_state:
            st.session_state[session_key] = [{"_entry_id": 0}]
            st.session_state[counter_key] = 1
            return

        if counter_key not in st.session_state:
            existing_ids = [
                entry.get("_entry_id", index)
                for index, entry in enumerate(st.session_state[session_key])
            ]
            st.session_state[counter_key] = (
                (max(existing_ids) + 1) if existing_ids else 0
            )

        for entry in st.session_state[session_key]:
            if "_entry_id" not in entry:
                entry["_entry_id"] = st.session_state[counter_key]
                st.session_state[counter_key] += 1

    def __append_repeatable_entry(self, field_name: str):
        """Append a repeatable entry with a stable ID."""
        session_key, counter_key = self.generate_session_keys(field_name)
        self.ensure_repeatable_entries(field_name)
        st.session_state[session_key].append(
            {"_entry_id": st.session_state[counter_key]}
        )
        st.session_state[counter_key] += 1

    def _deserialize_date(self, value: date) -> str:
        """Deserialize a date object to MM-DD-YYYY format."""
        if value is None:
            return None
        if isinstance(value, date):
            return value.strftime("%m-%d-%Y")
        return value

    def _deserialize_ontology_term(self, value: str) -> OntologyTerm:
        """Deserialize a value to an OntologyTerm."""
        if value is None:
            return None
        if matches(value, RegularExpressions.ONTOLOGY_TERM_CURIE):
            return OntologyTerm(value)
        else:
            matched_term = self.__ontology_map.get_field_terms(value)
            if matched_term is not None:
                return matched_term

        return OntologyTerm(term=value, curie="NIAGADS:needs_review")

    def _deserialize_list(
        self,
        values: Union[str, list[str]],
        deserializer: Callable = None,
        is_set: bool = False,
    ) -> Union[list, set]:
        """Deserialize values into a list or set."""
        list_values = (
            [v.strip() for v in values.replace("\n", ",").split(",") if v.strip()]
            if isinstance(values, str)
            else values
        )
        if deserializer is not None:
            list_values = [deserializer(lv) for lv in list_values]
        return set(list_values) if is_set else list_values

    def _deserialize_set(
        self,
        values: Union[str, list[str]],
        deserializer: Callable = None,
    ) -> set:
        return self._deserialize_list(values, deserializer, is_set=True)

    def _is_nested_form_empty(
        self, nested_data: dict, child_form_metadata: dict
    ) -> bool:
        """Check if a nested form has all null or default values."""
        if not nested_data:
            return True
        field_meta: FormMetadata
        for field_name, field_meta in child_form_metadata.items():
            if field_name not in nested_data:
                continue

            value = nested_data[field_name]

            # Check if value is not None and not empty
            if value is not None and value != "" and value != []:
                if field_meta.default:
                    if field_meta.is_enum:
                        default = str(field_meta.default)
                    if field_meta.is_ontology_term:
                        default = field_meta.default.term
                    else:
                        default = field_meta.default
                    # If value matches the default, it's still considered empty
                    if value == default:
                        continue
                return False

        return True

    def __process_form_data(
        self,
        form_data: dict,
        form_metadata: dict[str, FormMetadata],
        parent_field: str = "",
    ) -> tuple[dict, list[str]]:
        """Process and deserialize form data using deserializers from metadata.

        Recursively applies deserializers to fields and validates required fields.
        Handles nested composite fields and repeatable fields.

        Args:
            form_data: Dictionary of raw form field values from render_form().
            form_metadata: Form metadata dict containing field info and deserializers.
            parent_field: Parent field name for error messages (e.g., "file_properties").

        Returns:
            Tuple of (processed_data_dict, validation_errors_list).
            processed_data_dict contains deserialized values (may have None for failed fields).
            validation_errors_list contains all validation error messages with parent.field paths.
        """
        processed = {}
        validation_errors = []

        for field_name, field_meta in form_metadata.items():
            value = form_data.get(field_name)

            # Build full field path for error messages
            full_field_path = (
                f"{parent_field}.{field_name}" if parent_field else field_name
            )

            # Check required fields
            if field_meta.is_required and (value is None or value == ""):
                validation_errors.append(f"Required field missing: {full_field_path}")

            # Skip None/empty values for optional fields
            elif value is None or value == "":
                processed[field_name] = None

            # Handle composite (nested) fields
            elif field_meta.is_composite:
                if field_meta.is_repeatable:
                    processed_list = []
                    processed_errors = []
                    for idx, item in enumerate(value):
                        if not self._is_nested_form_empty(
                            item, field_meta.child_form_metadata
                        ):
                            processed_item, nested_errors = self.__process_form_data(
                                item,
                                field_meta.child_form_metadata,
                                parent_field=f"{full_field_path}[{idx}]",
                            )
                            if nested_errors:
                                processed_errors.extend(nested_errors)
                            processed_list.append(processed_item)
                    if len(processed_list) == 0:
                        processed[field_name] = None
                    else:
                        processed[field_name] = processed_list
                        if len(processed_errors) > 0:
                            validation_errors.extend(processed_errors)

                else:
                    if self._is_nested_form_empty(
                        value, field_meta.child_form_metadata
                    ):
                        processed[field_name] = None
                    else:
                        processed_item, nested_errors = self.__process_form_data(
                            value,
                            field_meta.child_form_metadata,
                            parent_field=full_field_path,
                        )
                        processed[field_name] = processed_item
                        if nested_errors:
                            validation_errors.extend(nested_errors)

            elif field_meta.is_list:
                processed[field_name] = self._deserialize_list(
                    value, field_meta.deserializer
                )
            elif field_meta.is_set:
                processed[field_name] = self._deserialize_list(
                    value, field_meta.deserializer, is_set=True
                )
            # Handle regular fields - apply deserializer if available
            elif field_meta.deserializer is not None:
                try:
                    processed[field_name] = field_meta.deserializer(value)
                except Exception as e:
                    validation_errors.append(
                        f"Failed to deserialize {full_field_path}: {str(e)}"
                    )
                    processed[field_name] = None
            else:
                # No deserializer - pass through as-is
                processed[field_name] = value

        return processed, validation_errors

    def run(self):
        """Run the Streamlit application."""
        st.set_page_config(
            page_title=self.__app_name,
            layout="centered",
            initial_sidebar_state="collapsed",
        )

        # Add custom CSS to center content and style buttons
        st.markdown(
            """
            <style>
            .main {
                max-width: 900px;
                margin: 0 auto;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.title("Track Metadata Builder")
        st.markdown("Enter track metadata below.")

        # Define deserializers for form fields

        with st.form("track_metadata_form", enter_to_submit=False):
            form_data = self.__renderer.render_form()
            col1, col2 = st.columns([1, 4])
            with col1:
                submitted = st.form_submit_button("Submit", type="primary")
            with col2:
                st.form_submit_button("Reset", type="secondary")

        # Render "Add" and "Remove" buttons for repeatable fields outside form context
        st.divider()
        field_metadata: FormMetadata
        for field_name, field_metadata in self.__form_metadata.items():
            if field_metadata.is_repeatable:
                form_model = field_metadata.child_form_class
                session_key, _ = self.generate_session_keys(field_name)
                field_label = field_metadata.title
                self.ensure_repeatable_entries(field_name)

                # Create a section for this repeatable field's controls
                with st.expander(
                    f"🛠️ Manage {field_label}",
                    expanded=False,
                ):
                    # Add button
                    if st.button(
                        f"➕ Add {field_label}",
                        key=f"add_{field_name}",
                        help=f"Add a new {field_label}",
                    ):
                        self.__append_repeatable_entry(field_name)
                        st.rerun()

                    # Render remove buttons for each entry in this field
                    if st.session_state[session_key]:
                        st.markdown(f"**Remove {form_model.__name__}:**")

                        for idx, entry in enumerate(st.session_state[session_key]):
                            st.button(
                                f"🗑️ Remove entry #{idx + 1}",
                                key=f"remove_{field_name}_{entry['_entry_id']}",
                                help=f"Remove {form_model.__name__} entry #{idx + 1}",
                                on_click=self.__remove_entry,
                                args=(idx, session_key),
                            )

        # Handle form submission
        if submitted:
            try:
                # Process and deserialize form data using metadata
                processed_data, validation_errors = self.__process_form_data(
                    form_data, self.__form_metadata
                )

                # Check for validation errors
                if validation_errors:
                    st.error("❌ Validation failed:")
                    for error in validation_errors:
                        st.error(error)
                else:
                    # Validate by instantiating the Track model
                    result = self.__pydantic_model(**processed_data)

                    # Success
                    st.success("✓ Metadata validated successfully!")

                    json_output = result.model_dump(
                        mode="json",
                        exclude=None,
                        encoder=lambda v: (
                            str(v) if isinstance(v, CaseInsensitiveEnum) else v
                        ),
                    )

                    # Download button
                    file_name = f"{json_output.get('track_id', 'track')}-metadata.json"
                    st.download_button(
                        label="Download as JSON",
                        data=json.dumps(json_output, indent=2),
                        file_name=file_name,
                        mime="application/json",
                    )

                    # Show JSON preview
                    st.subheader("Generated JSON")
                    st.json(json_output)

            except ValidationError as e:
                st.error("❌ Validation failed:")
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    st.error(f"  - **{field_path}**: {error['msg']}")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                raise


class FormRenderer(ComponentBaseMixin):
    """Renders form widgets based on field metadata."""

    def __init__(
        self,
        form_class: any,
        form_metadata: dict,
        ontology_map: OntologyMap,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__instance = form_class()
        self.__metadata = form_metadata
        self.__ontology_map = ontology_map

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(debug={self._debug}, "
            f"verbose={self._verbose})"
        )

    def __render_ontology_term_field(
        self, field_name: str, field_meta: FormMetadata, key: int = 0
    ) -> tuple:
        # print(field_name)
        label = field_meta.title
        help_text = field_meta.description
        is_required: bool = field_meta.is_required
        default_value: OntologyTerm = (
            field_meta.default.term if field_meta.default else None
        )

        if is_required:
            label = f"{label} *"

        options = self.__ontology_map.get_field_terms(field_name, terms_only=True)
        if field_meta.is_list:
            value = st.multiselect(
                label,
                options=options,
                default=default_value or [],
                help=help_text,
                accept_new_options=True,
                key=f"{field_name}_{key}",
            )
        else:
            default_index = None
            if default_value:
                try:
                    default_index = options.index(default_value)
                except (ValueError, IndexError):
                    pass

            value = st.selectbox(
                label,
                options=options,
                index=default_index,
                help=help_text,
                key=f"{field_name}_{key}",
            )
        return field_name, value

    def __render_enum_field(
        self, field_name: str, field_meta: FormMetadata, key: int = 0
    ) -> tuple:
        label = field_meta.title
        help_text = field_meta.description
        is_required: bool = field_meta.is_required
        default_value = field_meta.default
        enum_type = field_meta.model_type
        is_set: bool = field_meta.is_set

        if is_required:
            label = f"{label} *"

        options = enum_type.list()

        # Checkboxes for enum sets
        if is_set:
            options = enum_type.list()
            default_selected = set()
            if default_value and isinstance(default_value, set):
                default_selected = default_value

            # Render checkboxes with label
            st.markdown(
                f"<p style='font-size: 14px;'>{label}</p>",
                unsafe_allow_html=True,
            )

            selected = []
            for index, option in enumerate(options):
                if st.checkbox(
                    option,
                    value=option in default_selected,
                    key=f"{field_name}_{key}_{index}",
                ):
                    selected.append(option)

            return field_name, selected

        else:
            default_index = None
            if default_value is not None:
                default_index = options.index(default_value.value)

            value = st.selectbox(
                label,
                options=options,
                index=default_index,
                help=help_text,
                key=f"{field_name}_{key}",
            )
            return field_name, value

    def __render_repeatable_composite_field(
        self, field_name: str, field_meta: FormMetadata
    ) -> tuple:
        """ """
        label = field_meta.title
        help_text = field_meta.description
        is_required: bool = field_meta.is_required

        if is_required:
            label = f"{label} *"

        # Initialize session state for this list field if not exists
        session_key, _ = MetadataBuilderApp.generate_session_keys(field_name)
        MetadataBuilderApp.ensure_repeatable_entries(field_name)

        with st.expander(label, expanded=is_required):
            if help_text:
                st.caption(help_text)

            entries_data = []
            for idx, entry in enumerate(st.session_state[session_key]):
                with st.container(border=True):
                    nested_renderer = FormRenderer(
                        field_meta.child_form_class,
                        field_meta.child_form_metadata,
                        ontology_map=self.__ontology_map,
                    )
                    nested_data = nested_renderer.render_form(key=entry["_entry_id"])
                    entries_data.append(nested_data)

            # Return collected entries as tuple (field_name, value)
            return field_name, entries_data

    def render_field(
        self, field_name: str, field_meta: FormMetadata, key: int = 0
    ) -> tuple:
        """Render appropriate Streamlit widget based on field metadata.

        Args:
            field_name (str): Name of the field.
            field_meta (FormMetadata): Field metadata from form generator

        Returns:
            Tuple of (field_name, user_input_value).
        """
        if self._debug:
            print(f"{field_meta}")

        if field_meta.is_ontology_term:
            return self.__render_ontology_term_field(field_name, field_meta, key=key)

        if field_meta.is_enum:
            return self.__render_enum_field(field_name, field_meta, key=key)

        label = field_meta.title
        is_required = field_meta.is_required
        help_text = field_meta.description
        if is_required:
            label = f"{label} *"

        # Handle composite fields with expander
        if field_meta.is_composite:
            if field_meta.is_repeatable:
                return self.__render_repeatable_composite_field(field_name, field_meta)
            with st.expander(label, expanded=is_required):
                if help_text:
                    st.caption(help_text)
                nested_renderer = FormRenderer(
                    field_meta.child_form_class,
                    field_meta.child_form_metadata,
                    ontology_map=self.__ontology_map,
                )
                nested_data = nested_renderer.render_form(key=key)
            return field_name, nested_data

        default_value = field_meta.default
        model_type = field_meta.model_type
        is_list = field_meta.is_list or field_meta.is_set

        # Handle basic types based on model_type

        if model_type is date:
            value = st.date_input(
                label,
                value=default_value,
                help=help_text,
                key=f"{field_name}_{key}",
            )
            return field_name, value

        if model_type is bool:
            value = st.checkbox(
                label,
                value=default_value or False,
                help=help_text,
                key=f"{field_name}_{key}",
            )
            return field_name, value

        if model_type is int:
            value = st.number_input(
                label,
                value=default_value,
                step=1,
                help=help_text,
                key=f"{field_name}_{key}",
            )
            return field_name, value

        if model_type is float:
            value = st.number_input(
                label,
                value=default_value,
                step=None,
                help=help_text,
                key=f"{field_name}_{key}",
            )
            return field_name, value

        if is_list:
            list_label = f"{label} (L)"
            value = st.text_area(
                list_label,
                value=default_value or "",
                help=(
                    f"{help_text} - can enter one or more values as comma or newline separated values"
                    if help_text
                    else "can enter one or more values as comma or newline separated values"
                ),
                key=f"{field_name}_{key}",
            )
            return field_name, value

        if field_name == "description":
            value = st.text_area(
                label, value="", help=help_text, key=f"{field_name}_{key}"
            )
            return field_name, value

        # Default: text input for strings and other types
        value = st.text_input(
            label,
            value=default_value or "",
            help=help_text,
            key=f"{field_name}_{key}",
        )
        return field_name, value

    def render_form(self, key: int = 0) -> dict:
        """Render all fields from form metadata.

        Args:
            form_metadata: Metadata dict from form generator.
            form_instance: WTForms form instance.

        Returns:
            Dictionary of field_name -> user_input_value.
        """
        form_data = {}
        for field_name in self.__instance._fields:
            field_meta: FormMetadata = self.__metadata[field_name]
            field_name_result, value = self.render_field(
                field_name, field_meta, key=key
            )
            form_data[field_name_result] = value

        return form_data


def main():
    ontology_reference_file = Path(__file__).parent / "ontology_reference.txt"
    app = MetadataBuilderApp(
        pydantic_model=Track,
        application_name="GenomicsDB Track Metadata Builder",
        ontology_reference_file=ontology_reference_file,
        debug=False,
    )
    app.run()


if __name__ == "__main__":
    main()
