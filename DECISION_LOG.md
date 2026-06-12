# Decision Log

## 2026-02-18
- Enforced a global notes-append throttle for `home.md`: append at most one new habit line every 3 hours, tracked via `.last_notes_append`.
- Stopped rewriting/removing existing note lines during append; now only appends genuinely new habit lines to avoid batch inserts.
- Added persistent queueing in `.pending_notes_habits` so all eligible habits are eventually appended one-by-one every 3 hours instead of dropping extras.

## 2026-04-10
- Replaced the notes append throttle/queue with a persisted daily trigger schedule. Each due habit trigger gets a random local time from 06:00 through 12:00, and notes are appended only after that trigger time passes.
- Added `dailyTriggerCount` for habits that need multiple note triggers per due day without changing the meaning of existing numeric `goal` habits.
- Generalized due habit outputs with `dueOutputs.writeToMd` and `dueOutputs.desktopNotification`, and renamed the daily schedule file to `.habit_trigger_schedule` because it now drives both notes and desktop notifications.

## 2026-06-12
- Added `dueOutputs.textToSpeech`, backed by ElevenLabs MP3 generation and a local `.tts_cache/` so repeated habit prompts do not spend API credits.
- Text-to-speech is a gating output: if a trigger has TTS enabled but the default audio sink is not Bluetooth, the trigger stays pending and is retried by a later cron run.
- Added a process lock for the every-minute cron job so long sequential audio playback cannot overlap with the next invocation.
