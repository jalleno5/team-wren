DROP POLICY "Users can create own beats" ON "public"."beats";

DROP POLICY "Users can delete own beats" ON "public"."beats";

DROP POLICY "Users can update own beats" ON "public"."beats";

DROP POLICY "Users can view own or public beats" ON "public"."beats";

DROP POLICY "Users can create own sounds" ON "public"."sounds";

DROP POLICY "Users can delete own sounds" ON "public"."sounds";

DROP POLICY "Users can update own sounds" ON "public"."sounds";

DROP POLICY "Users can view own or public sounds" ON "public"."sounds";

CREATE POLICY "Users can create own beats" ON "public"."beats"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((auth.uid() = user_id));

CREATE POLICY "Users can delete own beats" ON "public"."beats"
  FOR DELETE
  TO "authenticated"
  USING ((auth.uid() = user_id));

CREATE POLICY "Users can update own beats" ON "public"."beats"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = user_id));

CREATE POLICY "Users can view own or public beats" ON "public"."beats"
  FOR SELECT
  TO "anon", "authenticated"
  USING (((auth.uid() = user_id) OR (visibility = 'public'::public.visibility_status)));

CREATE POLICY "Users can create own sounds" ON "public"."sounds"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((auth.uid() = user_id));

CREATE POLICY "Users can delete own sounds" ON "public"."sounds"
  FOR DELETE
  TO "authenticated"
  USING ((auth.uid() = user_id));

CREATE POLICY "Users can update own sounds" ON "public"."sounds"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = user_id));

CREATE POLICY "Users can view own or public sounds" ON "public"."sounds"
  FOR SELECT
  TO "anon", "authenticated"
  USING (((auth.uid() = user_id) OR (visibility = 'public'::public.visibility_status)));

