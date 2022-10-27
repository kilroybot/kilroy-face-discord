# Usage

This package provides an interface to a Discord channel
that complies with the **kilroy** face API.

It assumes that you only want to use a single Discord channel.

## Prerequisites

You need to create a Discord bot and invite it to a channel.
The bot needs to be able to read all messages in the channel
and view all reactions to them.
It also needs to be able to send new messages to the channel.

After you are done, you should have a bot token and a channel ID.
You need to pass these to the server,
either as environment variables, command line arguments
or entries in a configuration file.

For example, you can do this:

```sh
export KILROY_FACE_DISCORD_FACE__TOKEN="Paste your bot token here"
export KILROY_FACE_DISCORD_FACE__CHANNEL_ID="Paste your channel ID here"
```

## Running the server

To run the server, install the package and run the following command:

```sh
kilroy-face-discord
```

This will start the face server on port 10000 by default.
Then you can communicate with the server, for example by using
[this package](https://github.com/kilroybot/kilroy-face-client-py-sdk).
