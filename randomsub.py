import asyncio, aiohttp, logging, logging.config, os, random
from aiohttp import web
from aiohttp_index import IndexMiddleware

logging.config.dictConfig({
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "standard": {
      "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
      "datefmt": "%I:%M:%S"
    }
  },
  "handlers": {
    "default": {
      "level": "DEBUG",
      "formatter": "standard",
      "class": "logging.StreamHandler"
    }
  },
  "loggers": {
    "": {
      "handlers": ["default"],
      "level": "DEBUG",
      "propagate": True
    }
  }
})

log = logging.getLogger(__name__)

ALL_NAME = "all-name.txt"
DIRTY_NAME = "dirty-name.txt"

def random_sub(filename):
  st = os.stat(filename)
  offset = random.randint(0, st.st_size)
  with open(filename, "rt") as f:
    f.seek(offset)
    f.readline()
    s = f.readline().split(", ")[-1].split()[0]
    return "https://reddit.com/r/" + s

async def get_random(req):
  return web.HTTPTemporaryRedirect(random_sub(ALL_NAME))

async def get_randnsfw(req):
  return web.HTTPTemporaryRedirect(random_sub(DIRTY_NAME))

async def init():
  """
  Download subreddit database. Only ran once a day at max on Heroku.
  """
  async with aiohttp.ClientSession() as session:
    async with session.get("https://api.github.com/repos/voussoir/reddit/releases") as res:
      res.raise_for_status()
      data = await res.json()

    for asset in data[0]["assets"]:
      if asset["name"] == ALL_NAME or asset["name"] == DIRTY_NAME:
        log.info("Downloading %s", asset["name"])
        async with session.get(asset["browser_download_url"]) as res:
          with open(asset["name"], "wb") as f:
            while True:
              chunk = await res.content.read(1024)
              if not chunk:
                break
              f.write(chunk)
          res.release()

if __name__ == "__main__":
  loop = asyncio.get_event_loop()
  loop.run_until_complete(init())

  app = web.Application(
    middlewares=[
      IndexMiddleware()
    ],
    loop=loop
  )
  app.router.add_route("GET", "/random", get_random)
  app.router.add_route("GET", "/randnsfw", get_randnsfw)
  app.router.add_static("/", os.path.join(os.path.dirname(__file__), "static"))
  web.run_app(
    app,
    port=os.environ.get("PORT", 8000),
    host=os.environ.get("HOST", "0.0.0.0")
  )
