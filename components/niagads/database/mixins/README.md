# Developers Guide: Database Mixins

## Name Collision

When a mixin is used by multiple tables in the same schema, name collision with occur with hardcoded index and constraint names.  Set the name argument (first argument in `Index` instantiation, `name` parameter in the `Constraint` instantiation) to `None` to allow SQLAlchemy to autogenerate the index or constraint name.  
