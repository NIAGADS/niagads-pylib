COMMIT_FLAG=""
if [[ "$1" == "--commit" ]]; then
	COMMIT_FLAG="--commit"
fi

poetry -C $PROJECT_ROOT run gdb_run_sql --file $PROJECT_ROOT/sql/bootstrap/create_extensions.sql $COMMIT_FLAG
poetry -C $PROJECT_ROOT run gdb_run_sql --file $PROJECT_ROOT/sql/bootstrap/create_roles.sql $COMMIT_FLAG