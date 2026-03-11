"""Dynamic WTForms form generator for Pydantic models.

Inspects a Pydantic model and generates a WTForms form class with fields
dynamically mapped from the model's type hints.
"""

from datetime import date
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    get_args,
    get_origin,
    Annotated,
    Union,
)

from niagads.common.core import ComponentBaseMixin
from niagads.common.models.ontologies import OntologyTerm
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from wtforms import (
    BooleanField,
    FloatField,
    IntegerField,
    StringField,
    validators,
    DateField,
)
from wtforms.form import Form


class FormMetadata(BaseModel):
    """Metadata for a repeatable composite field in a generated WTForms form.

    Represents a list of nested Pydantic models rendered as repeatable form sections.
    """

    field_name: str
    model_type: type
    is_list: bool = True
    is_set: bool = False
    is_repeatable: bool = True
    is_composite: bool = True
    is_enum: bool = False
    is_ontology_term: bool = False
    is_required: bool
    default: Any = None
    title: str
    description: Optional[str] = None
    deserializer: Optional[Callable] = None
    child_form_class: Optional[type] = None
    child_form_metadata: Optional[Dict[str, "FormMetadata"]] = None


class CompositeField(StringField):
    """Marker field type for Pydantic composite models.

    This field type indicates that the field represents a nested Pydantic model
    that should be rendered as a composite form section, not a simple input.
    The actual model class is stored in field metadata.
    """

    pass


class RepeatableCompositeField(StringField):
    """Marker field type for lists of Pydantic composite models.

    This field type indicates that the field represents a list of nested
    Pydantic models (e.g., List[CurationEvent]) that should be rendered as
    a repeatable form section with add/remove buttons.
    The item model class is stored in field metadata.
    """

    pass


class PydanticFormGenerator(ComponentBaseMixin):
    """Generate WTForms form classes dynamically from Pydantic models."""

    def __init__(
        self,
        debug: bool = False,
        verbose: bool = False,
        exclude_pydantic_models: bool = False,
        exclude_filer_annotations: bool = True,
        deserializers: Optional[Dict[str, Callable]] = None,
    ):
        """Initialize the form generator.

        Args:
            debug: Enable debug logging.
            verbose: Enable verbose output.
            exclude_pydantic_models: If True, exclude fields typed as Pydantic
                models by default. Defaults to True.
            deserializers: Dictionary mapping deserializer names to deserializer
                functions. Used to build form_metadata for processing.
        """
        super().__init__(debug=debug, verbose=verbose)
        self.__exclude_pydantic_models = exclude_pydantic_models
        self.__exclude_filer_annotations = exclude_filer_annotations
        self.__deserializers = deserializers or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(debug={self._debug}, "
            f"verbose={self._verbose}, "
            f"exclude_pydantic_models={self.__exclude_pydantic_models}, "
            f"deserializers={bool(self.__deserializers)})"
        )

    @staticmethod
    def __normalize_default_value(default_value: Any) -> Any:
        """Convert PydanticUndefined to None for form metadata.

        Args:
            default_value: The default value from Pydantic field_info.default.

        Returns:
            None if default_value is PydanticUndefined, otherwise the value.
        """
        return None if default_value is PydanticUndefined else default_value

    def generate_nested_form(
        self,
        model_class: Type[BaseModel],
        form_name: Optional[str] = None,
    ) -> tuple:
        """Generate a nested form for a composite Pydantic model.

        Recursively calls generate_form_class to create forms for nested models.

        Args:
            model_class: The Pydantic model class to generate a form for.
            form_name: Optional custom name for the generated form class.

        Returns:
            A tuple of (form_class, form_metadata).
        """
        return self.generate_form_class(model_class, form_name)

    @staticmethod
    def __is_pydantic_model(field_type: Any) -> bool:
        """Check if a type is a Pydantic model."""
        try:
            return isinstance(field_type, type) and issubclass(field_type, BaseModel)
        except TypeError:
            return False

    @staticmethod
    def __is_type_safe(type_to_check: Any, target_class: Type) -> bool:
        """Safely check if type_to_check is a subclass of target_class.

        Args:
            type_to_check: The type to check.
            target_class: The class to check against.

        Returns:
            True if type_to_check is a type and subclass of target_class, False otherwise.
        """
        try:
            return isinstance(type_to_check, type) and issubclass(
                type_to_check, target_class
            )
        except TypeError:
            return False

    @staticmethod
    def __check_origin_or_union_args(
        field_type: Any, check_func: Callable[[Any], bool]
    ) -> bool:
        """Check field_type directly, then check each non-None arg of Union/Optional.

        Args:
            field_type: The field type to check.
            check_func: A function that takes a type and returns bool.

        Returns:
            True if check_func returns True for field_type or any Union arg.
        """
        if check_func(field_type):
            return True

        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None) and check_func(arg):  # type: ignore
                    return True

        return False

    @staticmethod
    def __is_list(field_type) -> bool:
        """Returns true if the field type is a list."""
        return PydanticFormGenerator.__check_origin_or_union_args(
            field_type, lambda t: get_origin(t) is list
        )

    @staticmethod
    def __is_set(field_type) -> bool:
        """Returns true if the field type is a set."""
        return PydanticFormGenerator.__check_origin_or_union_args(
            field_type, lambda t: get_origin(t) is set
        )

    @staticmethod
    def __is_enum(field_type) -> bool:
        """Returns true if the field type is an Enum."""
        base_type = PydanticFormGenerator.__get_base_type(field_type)
        if base_type is not None and PydanticFormGenerator.__is_type_safe(
            base_type, Enum
        ):
            return True

        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None) and PydanticFormGenerator.__is_type_safe(arg, Enum):  # type: ignore
                    return True

        return False

    @staticmethod
    def __is_ontology_term(field_type) -> bool:
        """Returns true if the field type is OntologyTerm."""
        base_type = PydanticFormGenerator.__get_base_type(field_type)
        if base_type is not None and PydanticFormGenerator.__is_type_safe(
            base_type, OntologyTerm
        ):
            return True

        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None) and PydanticFormGenerator.__is_type_safe(arg, OntologyTerm):  # type: ignore
                    return True

        return False

    @staticmethod
    def __get_base_type(field_type: Any, recurse: bool = True) -> Optional[Any]:
        """Extract base type from Optional, Union, and Annotated wrappers.

        Recursively unwraps Annotated, Optional, and Union types to reach the
        innermost type.
        """
        # First unwrap Annotated if present
        origin = get_origin(field_type)
        if origin is Annotated:
            args = get_args(field_type)
            # First arg is the actual type, recurse to unwrap further
            if args:
                if not recurse:
                    return args[0]
                return PydanticFormGenerator.__get_base_type(args[0])
            return None

        # Handle Optional[T] which is Union[T, None]
        if origin is type(None):  # type: ignore
            return None

        if origin is type(Optional):  # type: ignore
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None):  # type: ignore
                    if not recurse:
                        return args[0]
                    # Recurse to unwrap further
                    return PydanticFormGenerator.__get_base_type(arg)
            return None

        # Union types - try first non-None arg
        if hasattr(field_type, "__origin__"):
            if field_type.__origin__ is not type(None):  # type: ignore
                args = get_args(field_type)
                for arg in args:
                    if arg is not type(None):  # type: ignore
                        # Recurse to unwrap further
                        if not recurse:
                            return args[0]
                        return PydanticFormGenerator.__get_base_type(arg)

        return field_type

    def __is_repeated(self, pydantic_type: Any, base_type: Any) -> bool:
        """Check if a type is a list of Pydantic models (excluding OntologyTerm).

        Args:
            pydantic_type: The Pydantic field type annotation.
            base_type: The already-unwrapped type to check (a Pydantic model).

        Returns:
            True if pydantic_type is List[PydanticModel] and base_type is not
            OntologyTerm, False otherwise.
        """

        try:
            if isinstance(base_type, type) and issubclass(base_type, OntologyTerm):
                return False
        except TypeError:
            pass

        unwrapped_type = self.__get_base_type(pydantic_type, recurse=False)
        origin = get_origin(unwrapped_type)
        if origin is list or (
            hasattr(pydantic_type, "__origin__") and pydantic_type.__origin__ is list
        ):
            return True

        return False

    def __determine_deserializer(self, base_type: Any) -> Optional[Callable]:
        """Determine the appropriate deserializer function for a base type.

        Args:
            base_type: The extracted base type (not wrapped in Optional/Union).

        Returns:
            A deserializer function, or None if no deserializer is registered.
        """
        if base_type is not None and base_type in self.__deserializers:
            return self.__deserializers[base_type]
        return None

    def __map_pydantic_type_to_wtforms(self, pydantic_type: Any) -> Optional[Type]:
        """Map a Pydantic field type to a WTForms field type."""
        # Extract base type once
        base_type = PydanticFormGenerator.__get_base_type(pydantic_type)

        if base_type is None:
            raise ValueError(f"base type is `None` {pydantic_type}")

        # Handle OntologyTerm as a string field (before checking for Pydantic models)
        if self.__is_type_safe(base_type, OntologyTerm):
            return StringField

        # Check for Pydantic models - return CompositeField marker
        if self.__is_type_safe(base_type, BaseModel):
            # Check if it's a list of Pydantic models (excludes OntologyTerm)
            if self.__is_repeated(pydantic_type, base_type):
                return RepeatableCompositeField
            else:
                return CompositeField

        # Handle basic types
        if base_type is str:
            return StringField
        elif base_type is bool:
            return BooleanField
        elif base_type is int:
            return IntegerField
        elif base_type is float:
            return FloatField
        elif base_type is date:
            return DateField

        # Handle Enum types
        if self.__is_type_safe(base_type, Enum):
            return StringField

        # Check if it's a list or set of basic types - treat as StringField, parse later
        if self.__is_list(pydantic_type) or self.__is_set(pydantic_type):
            args = get_args(base_type)
            if args:
                arg_type = args[0]
                # Handle basic types and enums in lists/sets
                if arg_type in (str, int, float) or self.__is_type_safe(arg_type, Enum):
                    return StringField

        return None

    def generate_form_class(
        self,
        model_class: Type[BaseModel],
        form_name: Optional[str] = None,
    ) -> tuple:
        """Dynamically generate a WTForms Form class from a Pydantic model.

        Inspects the Pydantic model's fields and creates corresponding WTForms
        fields. Pydantic models as field types can optionally be excluded.
        Also builds form_metadata containing all information needed for processing.

        Args:
            model_class: The Pydantic model class to generate forms from.
            form_name: Optional custom name for the generated form class.
                Defaults to "{ModelName}Form".

        Returns:
            A tuple of (form_class, form_metadata) where form_metadata is a dict
            mapping field names to complete field metadata including deserializers.
        """

        if form_name is None:
            form_name = f"{model_class.__name__}Form"

        form_fields = {}
        form_metadata: Dict[str, FormMetadata] = {}

        for field_name, field_info in model_class.model_fields.items():
            field_type = field_info.annotation

            # Skip Pydantic model fields if requested
            if self.__exclude_pydantic_models and self.__is_pydantic_model(
                self.__get_base_type(field_type)
            ):
                continue

            # Skip fields with json_schema_extra['is_filer_annotation'] if requested
            if self.__exclude_filer_annotations:
                extra = getattr(field_info, "json_schema_extra", None)
                if extra and extra.get("is_filer_annotation", False):
                    continue

            # Map Pydantic type to WTForms field type
            wtforms_field_type = self.__map_pydantic_type_to_wtforms(field_type)
            if wtforms_field_type is None:
                continue

            # Build validators
            field_validators = []
            if field_info.is_required():
                field_validators.append(validators.DataRequired())

            # Create field label from field metadata
            label = field_info.title or field_name.replace("_", " ").title()

            # Get base type for model_type in metadata
            base_type = self.__get_base_type(field_type)
            if field_name.endswith("_date") and base_type is str:
                base_type = date
                wtforms_field_type = DateField

            deserializer = self.__determine_deserializer(base_type)

            # Check if this is a list or set
            is_list_field = self.__is_list(field_type)
            is_set_field = self.__is_set(field_type)
            is_enum_field = self.__is_enum(field_type)
            is_ontology_term_field = self.__is_ontology_term(field_type)

            # For composite fields, generate nested form and store metadata
            if wtforms_field_type is CompositeField:
                child_form_class, child_form_metadata = self.generate_nested_form(
                    base_type,
                    form_name=f"{field_name.title()}Form",
                )
                form_fields[field_name] = wtforms_field_type(
                    label=label,
                    render_kw={"placeholder": field_info.description or ""},
                    validators=field_validators,
                )
                # Build complete field metadata using FormMetadata model
                form_metadata[field_name] = FormMetadata(
                    field_name=field_name,
                    model_type=base_type,
                    is_list=False,
                    is_set=False,
                    is_repeatable=False,
                    is_composite=True,
                    is_enum=False,
                    is_ontology_term=False,
                    is_required=field_info.is_required(),
                    default=self.__normalize_default_value(field_info.default),
                    title=label,
                    description=field_info.description,
                    deserializer=deserializer,
                    child_form_class=child_form_class,
                    child_form_metadata=child_form_metadata,
                )

            # For repeatable composite fields (List[Model]), store item model metadata
            elif wtforms_field_type is RepeatableCompositeField:
                # unwrapped is already List[Model] from __map_pydantic_type_to_wtforms
                args = get_args(self.__get_base_type(field_type, recurse=False))
                if args:
                    item_model_type = args[0]
                    child_form_class, child_form_metadata = self.generate_nested_form(
                        item_model_type,
                        form_name=f"{field_name.title()}ItemForm",
                    )
                    form_fields[field_name] = wtforms_field_type(
                        label=label,
                        render_kw={"placeholder": field_info.description or ""},
                        validators=field_validators,
                    )
                    # Build complete field metadata for repeatable field using FormMetadata model
                    form_metadata[field_name] = FormMetadata(
                        field_name=field_name,
                        model_type=item_model_type,
                        is_list=True,
                        is_set=False,
                        is_repeatable=True,
                        is_composite=True,
                        is_enum=False,
                        is_ontology_term=False,
                        is_required=field_info.is_required(),
                        default=None,
                        title=label,
                        description=field_info.description,
                        deserializer=deserializer,
                        child_form_class=child_form_class,
                        child_form_metadata=child_form_metadata,
                    )

            else:
                # Regular field (not composite)
                form_fields[field_name] = wtforms_field_type(
                    label=label,
                    render_kw={"placeholder": field_info.description or ""},
                    validators=field_validators,
                )
                # Build complete field metadata for regular field using FormMetadata model
                form_metadata[field_name] = FormMetadata(
                    field_name=field_name,
                    model_type=base_type,
                    is_list=is_list_field,
                    is_set=is_set_field,
                    is_repeatable=False,
                    is_composite=False,
                    is_enum=is_enum_field,
                    is_ontology_term=is_ontology_term_field,
                    is_required=field_info.is_required(),
                    default=self.__normalize_default_value(field_info.default),
                    title=label,
                    description=field_info.description,
                    deserializer=deserializer,
                    child_form_class=None,
                    child_form_metadata=None,
                )

        # Dynamically create the Form class
        form_class = type(form_name, (Form,), form_fields)
        return form_class, form_metadata
