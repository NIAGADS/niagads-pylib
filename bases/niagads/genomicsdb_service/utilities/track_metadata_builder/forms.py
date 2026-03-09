"""Dynamic WTForms form generator for Pydantic models.

Inspects a Pydantic model and generates a WTForms form class with fields
dynamically mapped from the model's type hints.
"""

from enum import Enum
from typing import Any, Optional, Type, get_args, get_origin

from niagads.common.core import ComponentBaseMixin
from pydantic import BaseModel
from wtforms import BooleanField, FloatField, IntegerField, StringField, validators
from wtforms.form import Form


class CompositeField(StringField):
    """Marker field type for Pydantic composite models.

    This field type indicates that the field represents a nested Pydantic model
    that should be rendered as a composite form section, not a simple input.
    The actual model class is stored in field metadata.
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
    def __get_base_type(field_type: Any) -> Optional[Any]:
        """Extract base type from Optional or Union wrappers."""
        origin = get_origin(field_type)

        # Handle Optional[T] which is Union[T, None]
        if origin is type(None):  # type: ignore
            return None

        if origin is type(Optional):  # type: ignore
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None):  # type: ignore
                    return arg
            return None

        # Union types - try first non-None arg
        if hasattr(field_type, "__origin__"):
            if field_type.__origin__ is not type(None):  # type: ignore
                args = get_args(field_type)
                for arg in args:
                    if arg is not type(None):  # type: ignore
                        return arg

        return field_type

    @staticmethod
    def __map_pydantic_type_to_wtforms(pydantic_type: Any) -> Optional[Type]:
        """Map a Pydantic field type to a WTForms field type."""
        base_type = PydanticFormGenerator.__get_base_type(pydantic_type)

        if base_type is None:
            return None

        # Check for Pydantic models - return CompositeField marker
        if isinstance(base_type, type) and issubclass(base_type, BaseModel):
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
