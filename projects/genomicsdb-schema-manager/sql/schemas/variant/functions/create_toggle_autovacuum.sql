
CREATE OR REPLACE FUNCTION "variant"."toggle_variant_autovacuum" (status BOOLEAN)  RETURNS integer
  VOLATILE
  AS $body$
DECLARE
      partition TEXT;
      chr TEXT;
    BEGIN

      FOR chr IN
        SELECT UNNEST(string_to_array('chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY chrM', ' '))
      LOOP   
        partition := 'Variant.Variant' || '_' || chr::text;
        RAISE NOTICE 'Altering partition % -- autovacuum status: % ', partition, status;
	EXECUTE 'ALTER TABLE ' || partition || ' SET (autovacuum_enabled=' || status::text || ', toast.autovacuum_enabled=' || status::text || ')';
      END LOOP; 
      RETURN NULL;
    END;
$body$ LANGUAGE plpgsql;
