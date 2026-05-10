-- CREATE PARTITIONS
CREATE OR REPLACE FUNCTION "variant"."create_variant_partitions" (p_table_name TEXT) RETURNS INTEGER 
VOLATILE AS $ body $ 
    DECLARE 
    partition TEXT;
    CHR TEXT;

BEGIN 
    FOR CHR IN
        SELECT UNNEST( string_to_array 
            ('chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY chrM' , ' ' )
        )
    LOOP partition := p_table_name || '_' || CHR :: TEXT;
        IF NOT EXISTS (SELECT relname FROM pg_class WHERE relname = partition ) 
            THEN EXECUTE 'CREATE TABLE ' || partition || ' PARTITION OF ' ||  p_table_name || ' FOR VALUES IN (''' || CHR || ''')';
            RAISE NOTICE 'A partition has been created %', partition;
        END IF;
    END LOOP;
    RETURN NULL;
END;
$ body $ LANGUAGE plpgsql;