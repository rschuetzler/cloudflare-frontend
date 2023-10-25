# A very simple Cloudflare DNS frontend

I need a way to give students access to edit my Cloudflare DNS zone, without letting them log into my account.

Create an API key that has read access for the Zone, and edit access for DNS on the zone, then set the environment variables: CLOUDFLARE_TOKEN and CLOUDFLARE_ZONE

Then you're off to the races.
