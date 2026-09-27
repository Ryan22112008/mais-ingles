from src.config import Settings
from src.bot import MaisInglesBot


def main() -> None:
    settings = Settings.from_env()
    bot = MaisInglesBot(settings)
    bot.run()


if __name__ == "__main__":
    main()
