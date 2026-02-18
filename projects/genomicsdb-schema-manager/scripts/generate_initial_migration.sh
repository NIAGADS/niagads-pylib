# generate migrations for key referenced schemas (for foreign keys):  admin, reference, ragdoc

# uncomment and run the following one at a time, reviewing the migration ops file before running
# alembic revision -m "extensions" # then edit to add extensions
# source generate_migration.sh --schema ADMIN --message "initialize admin schema"


source generate_migration --schema REFERENCE --messge "initial reference schema"