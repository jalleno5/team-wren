SET local check_function_bodies = off;

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON SEQUENCES FROM "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON SEQUENCES FROM "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON SEQUENCES FROM "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON FUNCTIONS FROM "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON FUNCTIONS FROM "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON FUNCTIONS FROM "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON TABLES FROM "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON TABLES FROM "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON TABLES FROM "service_role";

CREATE TABLE "public"."beats" (
  "id"      uuid              NOT NULL DEFAULT gen_random_uuid(),
  "user_id" uuid              NOT NULL,
  "title"   character varying NOT NULL,
  "speed"   integer           NOT NULL,
  "genre"   character varying,
  CONSTRAINT "tracks_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."beats"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."sound_reports" (
  "id"          uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "sound_id"    uuid                     NOT NULL,
  "reporter_id" uuid                     NOT NULL,
  "description" character varying,
  "created_at"  timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "sound_reports_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."sound_reports"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."sounds_beats" (
  "id"         uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "sound_id"   uuid                     NOT NULL,
  "beat_id"    uuid                     NOT NULL,
  "created_at" timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "sounds_tracks_pkey" PRIMARY KEY (id),
  CONSTRAINT "sounds_tracks_sound_id_track_id_key" UNIQUE (sound_id, beat_id)
);

ALTER TABLE "public"."sounds_beats"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."sounds" (
  "id"      uuid              NOT NULL DEFAULT gen_random_uuid(),
  "user_id" uuid              NOT NULL,
  "title"   character varying NOT NULL,
  CONSTRAINT "sounds_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."sounds"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."users" (
  "id"         uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "username"   character varying        NOT NULL,
  "avatar_url" character varying,
  "email"      character varying        NOT NULL,
  "created_at" timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "users_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."users"
  ENABLE ROW LEVEL SECURITY;

CREATE TYPE "public"."source_type" AS ENUM (
  'uploaded',
  'recorded'
);

ALTER TABLE "public"."sounds"
  ADD COLUMN "source_type" public.source_type NOT NULL;

ALTER TABLE "public"."sounds"
  ADD COLUMN "duration_in_ms" integer NOT NULL;

CREATE TYPE "public"."visibility_status" AS ENUM (
  'public',
  'private'
);

ALTER TABLE "public"."beats"
  ADD COLUMN "visibility" public.visibility_status NOT NULL DEFAULT 'private'::public.visibility_status;

ALTER TABLE "public"."beats"
  ADD COLUMN "created_at" timestamp WITH time zone NOT NULL DEFAULT now();

ALTER TABLE "public"."sounds"
  ADD COLUMN "visibility" public.visibility_status NOT NULL DEFAULT 'private'::public.visibility_status;

ALTER TABLE "public"."sounds"
  ADD COLUMN "created_at" timestamp WITH time zone NOT NULL DEFAULT now();

CREATE OR REPLACE FUNCTION public.rls_auto_enable()
  RETURNS event_trigger
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'pg_catalog'
  AS $function$
DECLARE
  cmd record;
  tbl name;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        SELECT c.relname INTO tbl FROM pg_catalog.pg_class c WHERE c.oid = cmd.objid;
        EXECUTE format('alter table if exists %I.%I enable row level security', cmd.schema_name, tbl);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$;

REVOKE ALL ON FUNCTION "public"."rls_auto_enable"() FROM "anon", "authenticated", "service_role";

ALTER TABLE "public"."sound_reports"
  ADD CONSTRAINT "sound_reports_sound_id_fkey" FOREIGN KEY (sound_id) REFERENCES public.sounds(id) ON DELETE CASCADE;

ALTER TABLE "public"."sounds_beats"
  ADD CONSTRAINT "sounds_tracks_sound_id_fkey" FOREIGN KEY (sound_id) REFERENCES public.sounds(id) ON DELETE CASCADE;

ALTER TABLE "public"."sounds_beats"
  ADD CONSTRAINT "sounds_tracks_track_id_fkey" FOREIGN KEY (beat_id) REFERENCES public.beats(id) ON DELETE CASCADE;

ALTER TABLE "public"."beats"
  ADD CONSTRAINT "tracks_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."sound_reports"
  ADD CONSTRAINT "sound_reports_reporter_id_fkey" FOREIGN KEY (reporter_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE "public"."sounds"
  ADD CONSTRAINT "sounds_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

CREATE EVENT TRIGGER "ensure_rls"
  ON ddl_command_end
  WHEN TAG IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
  EXECUTE FUNCTION "public"."rls_auto_enable"();

GRANT EXECUTE ON FUNCTION "public"."rls_auto_enable"() TO PUBLIC;

REVOKE ALL ON FUNCTION "public"."rls_auto_enable"() FROM "postgres";

GRANT EXECUTE ON FUNCTION "public"."rls_auto_enable"() TO "postgres";

REVOKE ALL ON TABLE "public"."beats" FROM "anon";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."beats" TO "anon";

REVOKE ALL ON TABLE "public"."beats" FROM "authenticated";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."beats" TO "authenticated";

REVOKE ALL ON TABLE "public"."beats" FROM "postgres";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."beats" TO "postgres";

REVOKE ALL ON TABLE "public"."beats" FROM "service_role";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."beats" TO "service_role";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "anon";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sound_reports" TO "anon";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "authenticated";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sound_reports" TO "authenticated";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "postgres";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sound_reports" TO "postgres";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "service_role";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sound_reports" TO "service_role";

REVOKE ALL ON TABLE "public"."sounds" FROM "anon";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sounds" TO "anon";

REVOKE ALL ON TABLE "public"."sounds" FROM "authenticated";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sounds" TO "authenticated";

REVOKE ALL ON TABLE "public"."sounds" FROM "postgres";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds" TO "postgres";

REVOKE ALL ON TABLE "public"."sounds" FROM "service_role";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sounds" TO "service_role";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "anon";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sounds_beats" TO "anon";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "authenticated";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sounds_beats" TO "authenticated";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "postgres";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds_beats" TO "postgres";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "service_role";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."sounds_beats" TO "service_role";

REVOKE ALL ON TABLE "public"."users" FROM "anon";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."users" TO "anon";

REVOKE ALL ON TABLE "public"."users" FROM "authenticated";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."users" TO "authenticated";

REVOKE ALL ON TABLE "public"."users" FROM "postgres";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."users" TO "postgres";

REVOKE ALL ON TABLE "public"."users" FROM "service_role";

GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLE "public"."users" TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT MAINTAIN, REFERENCES, TRIGGER, TRUNCATE ON TABLES TO "service_role";

