ALTER TABLE "public"."sound_reports"
  DROP COLUMN "description";

ALTER TABLE "public"."sounds"
  ADD COLUMN "storage_path" text NOT NULL;

CREATE TYPE "public"."report_reason" AS ENUM (
  'Inappropriate content',
  'Copyright concern',
  'Spam or misleading'
);

ALTER TABLE "public"."sound_reports"
  ADD COLUMN "reason" public.report_reason;

CREATE POLICY "Private bucket: owner full access" ON "storage"."objects"
  FOR ALL
  TO "authenticated"
  USING (((bucket_id = 'sounds-private'::text) AND ((storage.foldername(name))[1] = (auth.uid())::text)))
  WITH CHECK (((bucket_id = 'sounds-private'::text) AND ((storage.foldername(name))[1] = (auth.uid())::text)));

CREATE POLICY "Public bucket: owner delete" ON "storage"."objects"
  FOR DELETE
  TO "authenticated"
  USING (((bucket_id = 'sounds-public'::text) AND ((storage.foldername(name))[1] = (auth.uid())::text)));

CREATE POLICY "Public bucket: owner insert" ON "storage"."objects"
  FOR INSERT
  TO "authenticated"
  WITH CHECK (((bucket_id = 'sounds-public'::text) AND ((storage.foldername(name))[1] = (auth.uid())::text)));

CREATE POLICY "Public bucket: owner update" ON "storage"."objects"
  FOR UPDATE
  TO "authenticated"
  USING (((bucket_id = 'sounds-public'::text) AND ((storage.foldername(name))[1] = (auth.uid())::text)))
  WITH CHECK (((bucket_id = 'sounds-public'::text) AND ((storage.foldername(name))[1] = (auth.uid())::text)));

CREATE POLICY "Public bucket: public select" ON "storage"."objects"
  FOR SELECT
  TO "authenticated"
  USING ((bucket_id = 'sounds-public'::text));

