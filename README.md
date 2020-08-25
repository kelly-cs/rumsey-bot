# rumsey-bot
A simple discord bot meant to handle web scraping, movie nights, and more.

**Current Modules:**

**Bank**
- Allows admins to create a "bill" for every user on the server, and bill/deduct from it as needed.

**Stock Watch**
- Allows admins to create a stock watch alert, daily threshold or long term % change, to which users can subscribe to if interested. 
- Stock alerts post their respective alerts to the channel that they were made in


**WIP:**
- A movie watching bot was being worked on, but due to the processing required, too many resources are required to allocate to it in order for it to be very practical. Raspberry Pi's and Google/AWS micro instances don't have enough oomph to watch a video at 30 fps and also stream at that speed. While I could just allocate more resources to this, it will never approach the convenience/utility of simply sharing one's own screen in discord and streaming a video themselves. 

- A web scraper is still planned, ideally to watch for items coming in stock that are currently unavailable. However, this might not match the utility of receiving e-mail alerts of when items come back in stock. A web scraper could still be useful for other things, like sharing breaking news however.
