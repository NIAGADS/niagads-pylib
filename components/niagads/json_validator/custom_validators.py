from jsonschema import (
    exceptions as jsExceptions,
    validators as jsValidators,
)


def case_insensitive_value_validator(validator, allowed, instance, schema):
    """
    Custom validator for jsonschema that allows case-insensitive matching for string values
    captured in either "enum" or "oneOf" (w/"const") values.

    Args:
        validator: The validator instance from jsonschema.
        enum (list): List of allowed values from the schema's enum.
        instance: The value from the JSON data being validated.
        schema (dict): The JSON schema for the property being validated.

    Yields:
        ValidationError: If the value does not match any enum value (case-insensitive for strings).

    Notes:
        - For non-string types, falls back to the default enum validation logic.
        - For string types, performs a case-insensitive comparison against allowed enum values.
    """
    values = []
    if "enum" in schema:
        values = schema["enum"]
    elif "oneOf" in schema:
        section = schema["oneOf"]
        # Only handle oneOf if all subschemas have const string values
        if all(
            isinstance(s, dict) and "const" in s and isinstance(s["const"], str)
            for s in section
        ):
            values = [item["const"] for item in section]
        else:
            # Not a controlled vocab; use default oneOf validator
            yield from jsValidators.Draft7Validator.VALIDATORS["oneOf"](
                validator, allowed, instance, schema
            )
            return

    if values and validator.is_type(instance, "string"):
        if not any(instance.lower() == str(v).lower() for v in values):
            yield jsExceptions.ValidationError(
                f"{instance!r} is not one of (case-insensitive) {values!r}"
            )
