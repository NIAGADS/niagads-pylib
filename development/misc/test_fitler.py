from pyparsing import Word, alphas, alphanums, oneOf, Keyword, Group, infixNotation, opAssoc

# Define grammar components
identifier = Word(alphas, alphanums + "_")  # Matches words like "datasource", "feature"
operator = oneOf("eq neq like")  # Matches operators: eq, neq, like
logical_and = Keyword("and")  # Matches the logical AND keyword
value = Word(alphas + "_ ")  # Matches values like "encode", "histone modification"

# Define a single condition (e.g., "datasource eq encode")
condition = Group(identifier + operator + value)

# Define the full expression with infix notation (e.g., "datasource eq encode and feature neq histone modification")
logical_expression = infixNotation(
    condition,
    [
        (logical_and, 2, opAssoc.LEFT),  # Logical AND has left-to-right associativity
    ],
)

# Example phrases
examples = [
    "datasource eq encode",
    "feature neq histone modification",
    "datasource eq encode and feature neq histone modification",
]

# Parse the examples
for example in examples:
    parsed = logical_expression.parseString(example)
    print(f"Input: {example}")
    print(f"Parsed: {parsed.asList()}")
    print()