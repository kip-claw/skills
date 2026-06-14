---
name: chartbeat
description: Pulls real-time top headlines and traffic data from Chartbeat for reuters.com.
tag: Work
---

# Chartbeat

Fetches real-time top pages and headline data from the Chartbeat API.
All operations go through `{{HOME}}/bin/chartbeat-top-stories.sh`.

The default site is reuters.com. A different host can be specified as
a second argument to any command.

## Commands

**Fetch top Reuters stories by concurrent visitors, excluding the homepage and section fronts:**
```
{{HOME}}/bin/chartbeat-top-stories.sh stories [limit] [host]
```

- `limit` — number of pages to return (default: 10)
- `host` — site domain (default: reuters.com)

Output includes ranking, concurrent reader count, page title, clickable Reuters
URL, authors, and sections.

When you return the results to Ben, keep the ranking and reader count in each
list item and separate each story with a blank line so it is easy to scan on
mobile.

Use `stories` by default for requests about Reuters top stories or chartbeat
headlines. It filters out homepage and section-front pages.

Use `top` only when you explicitly want all top pages, including the homepage
and section fronts.

## Examples

```
# Top 10 Reuters stories
{{HOME}}/bin/chartbeat-top-stories.sh stories

# Top 5 Reuters stories
{{HOME}}/bin/chartbeat-top-stories.sh stories 5

# Top 10 on a different site
{{HOME}}/bin/chartbeat-top-stories.sh stories 10 otherdomain.com
```

## Notes

- Requires `CHARTBEAT_API_KEY` in `{{HOME}}/.openclaw/.env`
- Data is real-time — results change constantly
- The API returns concurrent visitors ("people"), not pageviews
- If the API returns no pages, the site may not be tracked by Chartbeat
