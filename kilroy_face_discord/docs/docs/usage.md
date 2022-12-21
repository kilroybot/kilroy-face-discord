# Usage

This package provides an interface to a Discord channel
that complies with the **kilroy** face API.

It assumes that you only want to use a single Discord channel.

## Prerequisites

You need to create a Discord bot and invite it to a posting channel.
You also need a second scraping channel (or the same as the posting one) 
where real people post messages.
The bot needs to be able to read all messages in the scraping channel
and send new messages to the posting channel.
It also needs to be able to view the reactions for messages in both channels.

After you are done, you should have a bot token and one or two channel IDs.
You need to pass these to the server,
either as environment variables, command line arguments
or entries in a configuration file.

For example, you can do this:

```sh
export KILROY_FACE_DISCORD_FACE__TOKEN="Paste your bot token here"
export KILROY_FACE_DISCORD_FACE__SCRAPING_CHANNEL_ID="Paste your scraping channel ID here"
export KILROY_FACE_DISCORD_FACE__POSTING_CHANNEL_ID="Paste your posting channel ID here"
```

## Running the server

To run the server, install the package and run the following command:

```sh
kilroy-face-discord
```

This will start the face server on port 10000 by default.
Then you can communicate with the server, for example by using
[this package](https://github.com/kilroybot/kilroy-face-client-py-sdk).
