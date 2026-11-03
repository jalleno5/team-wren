ALTER TABLE "public"."users"
  ADD CONSTRAINT "users_id_fkey" FOREIGN KEY (id) REFERENCES auth.users(id) ON UPDATE CASCADE ON DELETE CASCADE;

CREATE POLICY "Users can create own beats" ON "public"."beats"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((auth.uid() = id));

CREATE POLICY "Users can delete own beats" ON "public"."beats"
  FOR DELETE
  TO "authenticated"
  USING ((auth.uid() = id));

CREATE POLICY "Users can update own beats" ON "public"."beats"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = id));

CREATE POLICY "Users can view own or public beats" ON "public"."beats"
  FOR SELECT
  TO "anon", "authenticated"
  USING (((auth.uid() = id) OR (visibility = 'public'::public.visibility_status)));

CREATE POLICY "Users can create own sounds reports" ON "public"."sound_reports"
  FOR INSERT
  TO "anon", "authenticated"
  WITH CHECK (((auth.uid() = reporter_id) AND (EXISTS ( SELECT 1
   FROM public.sounds s
  WHERE ((s.id = sound_reports.sound_id) AND ((s.user_id = auth.uid()) OR (s.visibility = 'public'::public.visibility_status)))))));

CREATE POLICY "Users can create own sounds" ON "public"."sounds"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((auth.uid() = id));

CREATE POLICY "Users can delete own sounds" ON "public"."sounds"
  FOR DELETE
  TO "authenticated"
  USING ((auth.uid() = id));

CREATE POLICY "Users can update own sounds" ON "public"."sounds"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = id));

CREATE POLICY "Users can view own or public sounds" ON "public"."sounds"
  FOR SELECT
  TO "anon", "authenticated"
  USING (((auth.uid() = id) OR (visibility = 'public'::public.visibility_status)));

CREATE POLICY "Users can delete own sound beat relationship" ON "public"."sounds_beats"
  FOR DELETE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM public.beats b
  WHERE ((b.id = sounds_beats.beat_id) AND (b.user_id = auth.uid())))));

CREATE POLICY "Users can insert sounds into beats" ON "public"."sounds_beats"
  FOR INSERT
  TO "authenticated"
  WITH CHECK (((EXISTS ( SELECT 1
   FROM public.sounds s
  WHERE ((s.id = sounds_beats.sound_id) AND (s.user_id = auth.uid())))) AND (EXISTS ( SELECT 1
   FROM public.beats b
  WHERE ((b.id = sounds_beats.beat_id) AND ((b.user_id = auth.uid()) OR (b.visibility = 'public'::public.visibility_status)))))));

CREATE POLICY "Users can update sounds in own beats" ON "public"."sounds_beats"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM public.beats b
  WHERE ((b.id = sounds_beats.beat_id) AND (b.user_id = auth.uid())))))
  WITH CHECK (((EXISTS ( SELECT 1
   FROM public.sounds s
  WHERE ((s.id = sounds_beats.sound_id) AND ((s.user_id = auth.uid()) OR (s.visibility = 'public'::public.visibility_status))))) AND (EXISTS ( SELECT 1
   FROM public.beats b
  WHERE ((b.id = sounds_beats.beat_id) AND (b.user_id = auth.uid()))))));

CREATE POLICY "Users can view sound beat relationships" ON "public"."sounds_beats"
  FOR SELECT
  TO "anon", "authenticated"
  USING (((EXISTS ( SELECT 1
   FROM public.sounds s
  WHERE ((s.id = sounds_beats.sound_id) AND ((s.user_id = auth.uid()) OR (s.visibility = 'public'::public.visibility_status))))) AND (EXISTS ( SELECT 1
   FROM public.beats b
  WHERE ((b.id = sounds_beats.beat_id) AND ((b.user_id = auth.uid()) OR (b.visibility = 'public'::public.visibility_status)))))));

CREATE POLICY "Users can create own profile" ON "public"."users"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((auth.uid() = id));

CREATE POLICY "Users can delete own profile" ON "public"."users"
  FOR DELETE
  TO "authenticated"
  USING ((auth.uid() = id));

CREATE POLICY "Users can update own profile" ON "public"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = id));

CREATE POLICY "Users can view own profile" ON "public"."users"
  FOR SELECT
  TO "anon", "authenticated"
  USING ((auth.uid() = id));

REVOKE ALL ON TABLE "public"."beats" FROM "anon";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."beats" TO "anon";

REVOKE ALL ON TABLE "public"."beats" FROM "authenticated";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."beats" TO "authenticated";

REVOKE ALL ON TABLE "public"."beats" FROM "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."beats" TO "service_role";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "anon";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sound_reports" TO "anon";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "authenticated";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sound_reports" TO "authenticated";

REVOKE ALL ON TABLE "public"."sound_reports" FROM "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sound_reports" TO "service_role";

REVOKE ALL ON TABLE "public"."sounds" FROM "anon";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds" TO "anon";

REVOKE ALL ON TABLE "public"."sounds" FROM "authenticated";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds" TO "authenticated";

REVOKE ALL ON TABLE "public"."sounds" FROM "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds" TO "service_role";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "anon";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds_beats" TO "anon";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "authenticated";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds_beats" TO "authenticated";

REVOKE ALL ON TABLE "public"."sounds_beats" FROM "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."sounds_beats" TO "service_role";

REVOKE ALL ON TABLE "public"."users" FROM "anon";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."users" TO "anon";

REVOKE ALL ON TABLE "public"."users" FROM "authenticated";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."users" TO "authenticated";

REVOKE ALL ON TABLE "public"."users" FROM "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."users" TO "service_role";

