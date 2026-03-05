DO $$
DECLARE
  role_names text[] := ARRAY['etl_runner', 'app_readonly'];
  role_name text;
BEGIN
  FOREACH role_name IN ARRAY role_names LOOP
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('CREATE ROLE %I', role_name);
    END IF;
  END LOOP;
END
$$;

