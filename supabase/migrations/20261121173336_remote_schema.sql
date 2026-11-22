REVOKE ALL ("duration_in_ms") ON TABLE "public"."sounds" FROM "authenticated";

REVOKE ALL ("source_type") ON TABLE "public"."sounds" FROM "authenticated";

REVOKE ALL ("storage_path") ON TABLE "public"."sounds" FROM "authenticated";

REVOKE ALL ("title") ON TABLE "public"."sounds" FROM "authenticated";

REVOKE ALL ("user_id") ON TABLE "public"."sounds" FROM "authenticated";

REVOKE ALL ("visibility") ON TABLE "public"."sounds" FROM "authenticated";

REVOKE ALL ("avatar_url") ON TABLE "public"."users" FROM "anon";

REVOKE ALL ("created_at") ON TABLE "public"."users" FROM "anon";

REVOKE ALL ("id") ON TABLE "public"."users" FROM "anon";

REVOKE ALL ("username") ON TABLE "public"."users" FROM "anon";

REVOKE ALL ("avatar_url") ON TABLE "public"."users" FROM "authenticated";

REVOKE ALL ("created_at") ON TABLE "public"."users" FROM "authenticated";

REVOKE ALL ("id") ON TABLE "public"."users" FROM "authenticated";

REVOKE ALL ("username") ON TABLE "public"."users" FROM "authenticated";

ALTER TABLE "public"."users"
  DROP COLUMN "email";

ALTER TABLE "public"."beats"
  ALTER COLUMN "genre" DROP DEFAULT;

ALTER TABLE "public"."beats"
  ALTER COLUMN "genre" TYPE text USING "genre"::text;

ALTER TABLE "public"."beats"
  ALTER COLUMN "title" DROP DEFAULT;

ALTER TABLE "public"."beats"
  ALTER COLUMN "title" TYPE text USING "title"::text;

ALTER TABLE "public"."sounds"
  ALTER COLUMN "title" DROP DEFAULT;

ALTER TABLE "public"."sounds"
  ALTER COLUMN "title" TYPE text USING "title"::text;

ALTER TABLE "public"."users"
  ALTER COLUMN "avatar_url" DROP DEFAULT;

ALTER TABLE "public"."users"
  ALTER COLUMN "avatar_url" TYPE text USING "avatar_url"::text;

ALTER TABLE "public"."users"
  ALTER COLUMN "username" DROP DEFAULT;

ALTER TABLE "public"."users"
  ALTER COLUMN "username" TYPE text USING "username"::text;

CREATE TYPE "public"."classification_category" AS ENUM (
  'Percussion',
  'Rhythmic',
  'Melodic',
  'Ambient',
  'Transition'
);

ALTER TABLE "public"."sounds"
  ADD COLUMN "classification" public.classification_category;

