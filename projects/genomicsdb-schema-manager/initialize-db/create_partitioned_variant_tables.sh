COMMIT_FLAG=""
if [[ "$1" == "--commit" ]]; then
	COMMIT_FLAG="--commit"
fi

poetry -C $PROJECT_ROOT run gdb_run_sql --file $PROJECT_ROOT/sql/schemas/variant/create_schema.sql $COMMIT_FLAG && \
poetry -C $PROJECT_ROOT run gdb_run_sql --file $PROJECT_ROOT/sql/schemas/variant/functions/create_chrm_partitions.sql $COMMIT_FLAG && \
poetry -C $PROJECT_ROOT run gdb_run_sql --file $PROJECT_ROOT/sql/schemas/variant/tables/create_variant_table.sql $COMMIT_FLAG