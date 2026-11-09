[← Back to README](../README.md)

# Known limitations: do not put this on the public internet
- The demo sign-in is a plain cookie: anyone can pick any member. It is not authentication.
- There is no rate limit, and each chat question costs a little money.
- There is no overall time limit per question: normally 1 to 4 seconds, but a stuck model API could hold a request for minutes.
- Prompts go to OpenRouter and the model's host. That is fine for fake data only.
- Each question is answered on its own (the server keeps no conversation history), and answers arrive whole rather than streamed.
- Store pictures are the brands' logos (original illustrations are the fallback, and the six original stores use them); there are no photos until you add licensed ones. The logos belong to their owners (see the Disclaimer in the [README](../README.md)) and a brand can ask for one to be removed.
- The demo data ages with the real calendar. The brand offers have no future end date, but members' verifications expire: Avery's nurse verification on 2027-03-01, Riley's military one 2027-05-10, Morgan's teacher one 2027-09-01 (Sam's student verification has already expired). In the original-store mode, offer o9 (Lumen Laptops 12%) also ends 2026-12-31. Set `CONCIERGE_TODAY` to keep a demo or an eval still.
- "Best deals" are ordered by percentage, not by money saved (a 30% discount and a 4% cash back are different kinds of saving); the concierge says so and offers to work out a cart total. Asked with no store chosen, it lists up to five at once (40 of 40 live runs).

## Not built (on purpose)
Real login, a database, cloud deployment, streaming, rate limiting, real store data.
