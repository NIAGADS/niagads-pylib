COMMIT_FLAG=""
if [[ "$1" == "--commit" ]]; then
	COMMIT_FLAG="--commit"
fi

for sql_file in "$PROJECT_ROOT"/sql/schemas/admin/views/*.sql; do
	poetry -C $PROJECT_ROOT run gdb_run_sql --file "$sql_file" $COMMIT_FLAG
done