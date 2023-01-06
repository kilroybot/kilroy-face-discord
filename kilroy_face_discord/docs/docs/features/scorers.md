# Scorers

Scorers are a way to evaluate posts.
You give them a message, and they return a single number representing the score.
All implemented scorers are described below.

## `RelativeReactionsScorer`

This is probably the simplest scorer imaginable and the only one implemented.
It simply counts the number of reactions on a message
and divides it by the number of members in the server.
So if a message has 10 reactions with sad emoji
and 10 reactions with fire emoji, the score will be 20.
