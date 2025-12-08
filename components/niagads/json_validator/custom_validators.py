from jsonschema import (
    exceptions as jsExceptions,
    validators as jsValidators,
)


def __resolve_oneof_enum(validator, allowed, instance, schema):
    """
    Helper to extract allowed string values from a schema's oneOf section, 
    or yield from the default oneOf validator if not a controlled vocabulary.

    Returns:
        values (list or None): List of allowed string values if extracted, else None.

    Yields:
        ValidationError: If the value does not match any allowed value and fallback is triggered.
    """
    section = schema['oneOf'] # assuming got here b/c of custom validation assignment, want to raise the KeyError
    if section and all(isinstance(s, dict) and "const" in s and isinstance(s["const"], str) for s in section):
        return [item["const"] for item in section]
    return None

def one_of_enum_validator(validator, allowed, instance, schema):
    """ custom validator to yield appropriate error message when using a oneOf to
    define an enum
    
    Args:
        validator: The validator instance from jsonschema.
        enum (list): List of allowed values from the schema's enum.
        instance: The value from the JSON data being validated.
        schema (dict): The JSON schema for the property being validated.

    Yields:
        ValidationError: If the value does not match any enum value.

    Notes:
        - For non-string types, falls back to the default validation logic.
        - For string types, performs a comparison against allowed enum values.
    """
    values = __resolve_oneof_enum(validator, allowed, instance, schema) 
    if values is None or not validator.is_type(instance, "string"):
        yield from jsValidators.Draft7Validator.VALIDATORS["oneOf"](validator, allowed, instance, schema)
        return
    
    else:
        if not any(instance == str(v) for v in values):
            yield jsExceptions.ValidationError(
                f"{instance!r} is not one of {values!r}"
            )

def case_insensitive_enum_validator(validator, allowed, instance, schema):
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
        if not validator.is_type(instance, "string"):
            yield from jsValidators.Draft7Validator.VALIDATORS["enum"](validator, allowed, instance, schema)
            return
        
        values = schema["enum"]
        
    elif "oneOf" in schema:
        values = __resolve_oneof_enum(validator, allowed, instance, schema)
        
        if values is None or not validator.is_type(instance, "string"):
            yield from jsValidators.Draft7Validator.VALIDATORS["oneOf"](validator, allowed, instance, schema)
            return
        
    if values: 
        if not any(instance.lower() == str(v).lower() for v in values):
            yield jsExceptions.ValidationError(
                f"{instance!r} is not one of (case-insensitive) {values!r}"
            )
