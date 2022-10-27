# Scrapers

Scrapers are used to provide a stream of existing posts.
They define a source of posts, and a way to retrieve them.
All implemented scrapers are described below.

## `BasicScraper`

This is the only implemented scraper.
It simply retrieves the latest posts from a channel.
It also excludes posts created by bots (including itself).
