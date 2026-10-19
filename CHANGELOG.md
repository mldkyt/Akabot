# Changelog

## Akabot 0.2.0 is out!

big things:

- **premium**: per-module free limits with premium unlocks, redeemable codes (timed and unlimited) and usage bars in the dashboard
- **timezones**: per-server timezone so streaks, summaries and daily features follow your local day
- **reaction roles**: brand new button/reaction role system
- **anti raid**: lots of new detection methods - message floods, duplicate messages, mention spam, invite spam, excessive caps, emoji and sticker spam, join bursts and scam detection, each toggleable
- **tasks**: a background task queue with retries, so scheduled actions survive restarts
- **dashboard redesign**: refreshed settings UI

small things:

- chat streaks can require a minimum streak, and streak DMs now default to off
- chat summary shows more and no longer reports the wrong day
- removed saves (Discord now has native message bookmarking)
- fixed economy bugs where pay checked the wrong balance and gambling never debited the wager
- many dashboard, migration and permission fixes

## Akabot 0.2.0 is out!

big things:

- **web ui**: fully featured (not pretty tho) web ui for controlling the bot, solving the whole complicated settings commands
- **chat streak reminders**: get reminded when your chat streak is close to ending
- **multiple logging channels**: set up per-channel event logging instead of one logging channel
- **saves**: message bookmarking
- **suggestions**: spice up your discord suggestion channel with voting, threads etc.
- **sticky message**: add a sticky message to the bottom of a channel
- **periodic messages**: send a message periodically in a channel
- **markov**: markov chain bot (requires message intent, not available in the main instance)
- **tag**: bot will respond with a message to any chat message with a keyword (message intent only, not available in the main instance)
- **anti raid**: detect non-pfp users and young accounts (for now)
- **top.gg integration**: upload commands, bot stats and receive votes from top.gg for leveling bonuses and voting credits
- **voting credits**: get rewards for voting for the bot, revive your chat streak

small things:

- improved sorting of chat streaks by last message sent
- fixed an error when the welcome or goodbye channel didn't exist
- fixed an error where the bot tried to reply into a channel that it didn't have permission to send messages into
