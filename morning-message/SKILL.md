---
name: morning-message
description: Generate Ben's daily good-morning message for the Reuters News Applications Desk Teams channel. Combines location, time, Chartbeat top story, news pegs, schedule, and optional run info.
metadata:
  openclaw:
    emoji: "🌅"
    tags: ["daily", "teams", "routine"]
---

# Morning Message

Generates Ben's daily good-morning message for the Reuters News Applications Desk Teams channel. The message follows a strict format with four or five lines. The message is them shared with Ben via Telegram. He will tidy it up and post it to Teams himself.

## Message Format

```
☀️ Good morning from <LOCATION>. It is <DAY_OF_WEEK>, <MONTH> <DAY>. The news time is <TIME>.
📰 The top story on Chartbeat is "<HEADLINE>"
🗓️ <NEWS_PEGS>
🪿 <SCHEDULE>
🏃 <RUN_LINE>  (only if Ben ran that morning)
```

### Line-by-line rules

1. **Greeting & location** — Always starts with "Good morning from". The
   location is usually one of:
   - `the Thomson Reuters Building at 3 Times Square` (the office)
   - `Studio 4D in moneymaking Manhattan` (home studio)
   - A train, plane, or conference venue when traveling
   Ask Ben where he is if not obvious. Include the day of week, full date
   (e.g. "Wednesday, May 14"), and current time formatted as `H:MM a.m.` or
   `H:MM p.m.` (AP style — lowercase, periods, no leading zero).

2. **Chartbeat top story** — Fetch the #1 story using the chartbeat skill:
   ```bash
   {{HOME}}/bin/kip-chartbeat.sh stories 1
   ```
   Extract just the headline and wrap it in quotes with a hyperlink over the entire headline text.

3. **News pegs** — Mention any known news pegs for the day (economic data
   releases, scheduled events, team member assignments like "Grant has a
   forecast"). If none are known, use: `I don't know of any pegs today.`
   Ask Ben if you are unsure.

4. **Schedule** — Lead with the gaggle (daily 11 a.m. meeting). Default is
   `We gaggle at 11.` Then append any other meetings Ben mentions. If Ben
   cannot make gaggle, note that instead.

5. **Run line** (optional) — If Ben ran that morning, add a line describing
   the distance and route. Check the runs log for today's date:
   ```bash
   gog --no-input -a "$GOG_ACCOUNT" sheets get 1ybViNc3uJp9Be7Os5Cryu6E83VTxB0ZqWPRYYiQAMfA "Sheet1!A1:D5" --json
   ```
   Use natural phrasing like "I ran 10k over the Queensborough Bridge and back."
   If no run is logged for today, omit this line entirely.

## Workflow

1. Ask Ben for anything you don't already know:
   - Where is he today? (office, home, traveling)
   - Any news pegs or special schedule items?
2. Fetch the Chartbeat top story.
3. Check the runs log for today.
4. Check today's calendar for meetings:
   ```bash
   vdirsyncer sync && khal list today
   ```
5. Assemble the message and share it here in Telegram by default.

## Style Notes

- Use AP style for times: `8:42 a.m.`, not `8:42 AM` or `08:42`
- Day of week and month are spelled out: `Wednesday, May 14`
- The Chartbeat headline is wrapped in straight double quotes with a hyperlink over it
- Emoji go at the start of each line with a space after
- Keep the tone casual and direct — this is a team chat, not a memo
- The gaggle emoji is always 🪿 (goose)
- Do not add sign-offs or pleasantries beyond the format

## Examples

### Typical office day

```
☀️ Good morning from the Thomson Reuters Building at 3 Times Square. It is Wednesday, May 14. The news time is 8:35 a.m.
📰 The top story on Chartbeat is "Fed signals rate decision is approaching as inflation cools"
🗓️  Grant has a forecast this morning.
🪿  We gaggle at 11. I have my regular meeting with Simon at 12.
```

### Home day with a run

```
☀️ Good morning from Studio 4D in moneymaking Manhattan. It is Thursday, May 7. The news time is 9:02 a.m.
📰 The top story on Chartbeat is "US and Iran explore short-term deal to end fighting"
🗓️  I don't know of any pegs today.
🪿  We gaggle at 11. I have a GitHub tech meeting at 1. I'll walk into the office shortly.
🏃 I ran 10k over the Queensborough Bridge and back.
```

### Travel day

```
☀️ Good morning from Acela 2910, which left New York Penn Station this morning at 5:27 a.m. It is Tuesday, May 5. The news time is 7:58 a.m.
📰 The top story on Chartbeat is "Middle East truce in doubt as US and Iran fight for control of Strait of Hormuz"
🗓️  Grant has some forecasts this morning.
🪿  I'll be presenting at RESPONSIBLE BUSINESS USA 2026 this morning in Boston, so I can't make gaggle. You should go on without me.
```

## Notes

- This skill only **generates** the message. Ben reviews, tweaks, and posts it
  himself.
- In a direct Telegram chat with Ben, share the assembled morning message in
  the chat by default after drafting it. Do not make him ask twice.
- The Chartbeat headline changes constantly — fetch it right before assembling.
- If the chartbeat script fails, ask Ben to supply the headline manually.
- News pegs and schedule details beyond the calendar often require Ben's input.
  Don't guess — ask.
