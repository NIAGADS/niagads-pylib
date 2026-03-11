"""Streamlit application for track metadata form intake and serialization."""

from datetime import date
from pathlib import Path
from niagads.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
import streamlit as st
from niagads.api.common.models.datasets.track import Track
from niagads.common.core import ComponentBaseMixin
from niagads.genomicsdb_service.utilities.track_metadata_builder.forms import (
    FormMetadata,
    PydanticFormGenerator,
)


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
        fields = next(f).strip().split("\t")
        for line in f:
            line = line.strip()
            if not line:
                continue
            values = line.split("\t")
            entry = dict(zip(fields, values))
            field = entry["field"]
            if field not in reference_by_field:
                reference_by_field[field] = []
            reference_by_field[field].append(entry)

    return reference_by_field


ONTOLOGY_REFERENCE = load_ontology_reference()


def get_reference_ontology_terms(
    ontology_map, field_name: str, terms_only: bool = False
):
    """get reference ontology terms for a field"""
    if field_name == "phenotype":
        complete_reference = []
        for field in ontology_map.keys():
            complete_reference.extend(ontology_map.get(field, {}))
        reference = [v for v in complete_reference if v["is_phenotype"]]

    else:
        reference = ontology_map.get(field_name, {})

    if terms_only:
        return [item["term"] for item in reference]
    else:
        return reference


def deserialize_date(value: date) -> str:
    """Deserialize a date object to MM-DD-YYYY format.

    Args:
        value: A date object to deserialize.

    Returns:
        A string representation of the date in MM-DD-YYYY format.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value.strftime("%m-%d-%Y")
    return value


def deserialize_ontology_term(value: str) -> str:
    if value is None:
        return None
    if matches(value, RegularExpressions.ONTOLOGY_TERM_CURIE):
        return OntologyTerm(value)
    else:
        for k, v in ONTOLOGY_REFERENCE.items():
            if value == v["term"]:
                return OntologyTerm(term=value, curie=v["curie"])

    return OntologyTerm(term=value, curie="NIAGADS:needs_review")


class FormRenderer(ComponentBaseMixin):
    """Renders form widgets based on field metadata."""

    def __init__(
        self,
        form_class: any,
        form_metadata: dict,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__instance = form_class()
        self.__metadata = form_metadata
        self.__ontology_map = load_ontology_reference()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(debug={self._debug}, "
            f"verbose={self._verbose})"
        )

    def get_reference_terms(self, field_name: str, terms_only: bool = False):
        return get_reference_ontology_terms(self.__ontology_map, field_name, terms_only)

    @staticmethod
    def _generate_session_keys(field_name: str) -> tuple[str, str]:
        return (
            f"_list_{field_name}_entries",
            f"_list_{field_name}_counter",
        )

    @staticmethod
    def ensure_repeatable_entries(field_name: str):
        """Ensure repeatable entries are initialized with stable IDs."""
        session_key, counter_key = FormRenderer._generate_session_keys(field_name)

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

    @staticmethod
    def append_repeatable_entry(field_name: str):
        """Append a repeatable entry with a stable ID."""
        session_key, counter_key = FormRenderer._generate_session_keys(field_name)
        FormRenderer.ensure_repeatable_entries(field_name)
        st.session_state[session_key].append(
            {"_entry_id": st.session_state[counter_key]}
        )
        st.session_state[counter_key] += 1

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

        options = self.get_reference_terms(field_name, terms_only=True)
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
        session_key, _ = self._generate_session_keys(field_name)
        self.ensure_repeatable_entries(field_name)

        with st.expander(label, expanded=is_required):
            if help_text:
                st.caption(help_text)

            entries_data = []
            for idx, entry in enumerate(st.session_state[session_key]):
                with st.container(border=True):
                    nested_renderer = FormRenderer(
                        field_meta.child_form_class,
                        field_meta.child_form_metadata,
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
        if field_meta.field_name.endswith("_date"):
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


def remove_entry(idx: int, session_key: str):
    """Callback to remove an entry at the specified index."""
    st.session_state[session_key].pop(idx)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Track Metadata Builder",
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
    deserializers = {date: deserialize_date, OntologyTerm: deserialize_ontology_term}

    # Generate form from Track model (exclude composite fields for now)
    generator = PydanticFormGenerator(
        exclude_pydantic_models=False,
        deserializers=deserializers,
    )
    form_metadata: dict[str, FormMetadata]
    form_class, form_metadata = generator.generate_form_class(Track)
    # Create renderer
    renderer = FormRenderer(form_class, form_metadata, debug=False)

    with st.form("track_metadata_form", enter_to_submit=False):
        form_data = renderer.render_form()
        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("Submit", type="primary")
        with col2:
            st.form_submit_button("Reset", type="secondary")

    # Render "Add" and "Remove" buttons for repeatable fields outside form context
    st.divider()
    field_metadata: FormMetadata
    for field_name, field_metadata in form_metadata.items():
        if field_metadata.is_repeatable:
            form_model = field_metadata.child_form_class
            session_key, _ = renderer._generate_session_keys(field_name)
            field_label = field_metadata.title
            renderer.ensure_repeatable_entries(field_name)

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
                    renderer.append_repeatable_entry(field_name)
                    st.rerun()

                # Render remove buttons for each entry in this field
                if st.session_state[session_key]:
                    st.markdown(f"**Remove {form_model.__name__}:**")

                    for idx, entry in enumerate(st.session_state[session_key]):
                        st.button(
                            f"🗑️ Remove entry #{idx + 1}",
                            key=f"remove_{field_name}_{entry['_entry_id']}",
                            help=f"Remove {form_model.__name__} entry #{idx + 1}",
                            on_click=remove_entry,
                            args=(idx, session_key),
                        )

    # Handle form submission
    if submitted:
        st.write("Form data received:")
        st.json(form_data)


if __name__ == "__main__":
    main()
