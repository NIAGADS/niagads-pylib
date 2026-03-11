"""Dynamic WTForms form generator for Pydantic models.

Inspects a Pydantic model and generates a WTForms form class with fields
dynamically mapped from the model's type hints.
"""

from datetime import date
from enum import Enum
from typing import Any, Optional, Type, get_args, get_origin, Annotated

from niagads.common.core import ComponentBaseMixin
from pydantic import BaseModel
from wtforms import (
    BooleanField,
    FloatField,
    IntegerField,
    StringField,
    validators,
    DateField,
)
from wtforms.form import Form


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
    ):
        """Initialize the form generator.

        Args:
            debug: Enable debug logging.
            verbose: Enable verbose output.
            exclude_pydantic_models: If True, exclude fields typed as Pydantic
                models by default. Defaults to True.
        """
        super().__init__(debug=debug, verbose=verbose)
        self.__exclude_pydantic_models = exclude_pydantic_models
        self.__exclude_filer_annotations = exclude_filer_annotations

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(debug={self._debug}, "
            f"verbose={self._verbose}, "
            f"exclude_pydantic_models={self.__exclude_pydantic_models})"
        )

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
            A tuple of (form_class, composite_fields_metadata).
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

    def __is_list_of_pydantic_model(self, pydantic_type: Any, base_type: Any) -> bool:
        """Check if a type is a list of Pydantic models (excluding OntologyTerm).

        Args:
            model: The model class to check for list origin.
            base_type: The already-unwrapped type to check (a Pydantic model).

        Returns:
            True if model is List[PydanticModel] and base_type is not OntologyTerm,
            False otherwise.
        """

        if isinstance(base_type, type) and base_type.__name__ == "OntologyTerm":
            return False

        unwrapped_type = self.__get_base_type(pydantic_type, recurse=False)

        origin = get_origin(unwrapped_type)
        if origin is list or (
            hasattr(pydantic_type, "__origin__") and pydantic_type.__origin__ is list
        ):
            return True

        return False

    def __map_pydantic_type_to_wtforms(self, pydantic_type: Any) -> Optional[Type]:
        """Map a Pydantic field type to a WTForms field type."""
        # Extract base type once
        base_type = PydanticFormGenerator.__get_base_type(pydantic_type)

        if base_type is None:
            raise ValueError(f"base type is `None` {pydantic_type}")

        # Check for Pydantic models - return CompositeField marker
        if isinstance(base_type, type) and issubclass(base_type, BaseModel):
            # Check if it's a list of Pydantic models (excludes OntologyTerm)
            if self.__is_list_of_pydantic_model(pydantic_type, base_type):
                return RepeatableCompositeField
            else:
                return CompositeField

        # Handle basic typesm
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

        # Handle Enum types (including str-based enums)
        try:
            if isinstance(base_type, type) and issubclass(base_type, Enum):
                return StringField
        except TypeError:
            pass

        # Check if it's a list or set of basic types - treat as StringField, parse later
        origin = get_origin(base_type)
        if origin in (list, set):
            args = get_args(base_type)
            if args:
                arg_type = args[0]
                # Unwrap Annotated if present
                if get_origin(arg_type) is Annotated:
                    arg_type = get_args(arg_type)[0]
                # Handle basic types and enums in lists/sets
                if arg_type in (str, int, float):
                    return StringField
                # Handle enum types in lists/sets
                try:
                    if isinstance(arg_type, type) and issubclass(arg_type, Enum):
                        return StringField
                except TypeError:
                    pass

        return None

    def generate_form_class(
        self,
        model_class: Type[BaseModel],
        form_name: Optional[str] = None,
    ) -> tuple:
        """Dynamically generate a WTForms Form class from a Pydantic model.

        Inspects the Pydantic model's fields and creates corresponding WTForms
        fields. Pydantic models as field types can optionally be excluded.

        Args:
            model_class: The Pydantic model class to generate forms from.
            exclude_pydantic_models: If True, exclude fields typed as Pydantic
                models. If None, uses the instance default. Defaults to None.
            form_name: Optional custom name for the generated form class.
                Defaults to "{ModelName}Form".

        Returns:
            A tuple of (form_class, composite_fields_metadata) where
            composite_fields_metadata is a dict mapping field names to their
            composite model and form class.
        """

        if form_name is None:
            form_name = f"{model_class.__name__}Form"

        form_fields = {}
        composite_fields_metadata = {}

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

            # For composite fields, generate nested form and store metadata
            if wtforms_field_type is CompositeField:
                base_type = self.__get_base_type(field_type)
                nested_form_class, nested_composite_metadata = (
                    self.generate_nested_form(
                        base_type,
                        form_name=f"{field_name.title()}Form",
                    )
                )
                form_fields[field_name] = wtforms_field_type(
                    label=label,
                    render_kw={"placeholder": field_info.description or ""},
                    validators=field_validators,
                )
                # Store composite metadata separately
                composite_fields_metadata[field_name] = {
                    "model": base_type,
                    "form_class": nested_form_class,
                }
            # For repeatable composite fields (List[Model]), store item model metadata
            elif wtforms_field_type is RepeatableCompositeField:
                # unwrapped is already List[Model] from __map_pydantic_type_to_wtforms
                args = get_args(self.__get_base_type(field_type, recurse=False))
                if args:
                    item_model_type = args[0]
                    nested_form_class, nested_composite_metadata = (
                        self.generate_nested_form(
                            item_model_type,
                            form_name=f"{field_name.title()}ItemForm",
                        )
                    )
                    form_fields[field_name] = wtforms_field_type(
                        label=label,
                        render_kw={"placeholder": field_info.description or ""},
                        validators=field_validators,
                    )
                    # Store repeatable field metadata with item model
                    composite_fields_metadata[field_name] = {
                        "model": item_model_type,
                        "form_class": nested_form_class,
                        "is_repeatable": True,
                    }
            else:
                # Create field with metadata
                form_fields[field_name] = wtforms_field_type(
                    label=label,
                    render_kw={"placeholder": field_info.description or ""},
                    validators=field_validators,
                )

        # Dynamically create the Form class
        form_class = type(form_name, (Form,), form_fields)
        return form_class, composite_fields_metadata
