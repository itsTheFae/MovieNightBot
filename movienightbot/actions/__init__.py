from abc import ABC, abstractmethod
from typing import Dict, Tuple, Union, List
from pathlib import Path
from importlib import import_module
import ast
import logging

import discord

from movienightbot.db.controllers import ServerController
from ..util import cleanup_messages

__ALL__ = ["KNOWN_ACTIONS", "unknown_default_action"]
logger = logging.getLogger("movienightbot")


async def unknown_default_action(msg: discord.message, command: str) -> None:
    await msg.channel.send(
        f"Unknown command {command} given, try reading the tutorial at `m!help` "
        f"to see what commands are available!"
    )


class ActionSendingError(Exception):
    pass


class BaseAction(ABC):
    # action name is what the action will be called on discord
    action_name = None
    admin = False
    guild_only = True

    async def _check_proceed(self, msg: discord.message) -> bool:
        if self.guild_only and msg.guild is None:
            logging.debug(f"User {msg.author.name} trying non-DM action in a DM")
            await msg.author.send("You can't do this command from a DM!")
            return False

        server_settings = ServerController().get_by_id(msg.guild.id)
        if msg.channel.id != server_settings.channel:
            logging.debug(
                f"User {msg.author.name} using non-permitted channel {msg.channel.name} "
                f"instead of {server_settings.channel}"
            )
            return False
        if not msg.author.guild_permissions.administrator and (
            self.admin
            and server_settings.admin_role not in {r.name for r in msg.author.roles}
        ):
            logging.debug(f"User {msg.author.name} does not have admin")
            await msg.channel.send("Hey now, you're not an admin on this server!")
            return False
        return True

    async def __call__(self, msg: discord.message) -> None:
        error_message = (
            "OOPSIE WOOPSIE!! UwU We made a fucky wucky!! A wittle fucko boingo! The code "
            "monkeys at our headquarters are working VEWY HAWD to fix this!"
        )
        try:
            if not await self._check_proceed(msg):
                return
        except Exception as e:
            logger.error(e, exc_info=e)
            await msg.channel.send(error_message)

        server_settings = ServerController().get_by_id(msg.guild.id)
        guild = msg.guild.name if msg.guild is not None else "DM"
        logger.info(
            f"Running action {self.action_name} on {guild} from user {msg.author.name}"
        )
        target = None
        args = None

        try:
            rt = await self.action(msg)
            if type(rt) is tuple and len(rt) == 2:
                target, args = rt

                if (
                    server_settings.message_timeout > 0
                    and type(args) is dict
                    and "also_delete" in args
                ):
                    await cleanup_messages(
                        args["also_delete"], sec_delay=server_settings.message_timeout
                    )

                if type(args) is str:
                    await target.send(args)
                elif type(args) is tuple:
                    await target.send(*args)
                elif type(args) is dict:
                    await target.send(**args)
            else:
                logger.error("Action did not return a two-member tuple!")
        except discord.Forbidden as e:
            if e.code == 50007:
                if target is msg.author:
                    if type(args) is str:
                        await msg.channel.send(args)
                    elif type(args) is tuple:
                        await msg.channel.send(*args)
                    elif type(args) is dict:
                        await msg.channel.send(**args)
                else:
                    await msg.channel.send(f"I can't DM you {msg.author.name}!")
                return
            else:
                logger.error(e, exc_info=e)
                await msg.channel.send(error_message)
        except Exception as e:
            logger.error(e, exc_info=e)
            await msg.channel.send(error_message)

    @staticmethod
    def get_message_data(
        msg: discord.message, data_parts: int = 1
    ) -> Union[str, Tuple[str]]:
        """Gets and sanitizes the message data associated with the command

        Parameters
        ----------
        msg
            The discord message object
        data_parts
            The number of pieces of information expected, space separated. Default 1.
            For example, if the message text is "m!suggest Some Movie Name" and we set to 1,
            this will return "Some Movie Name". Set to 2, it will return ("Some", "Movie Name")

        Notes
        -----
        Will return an empty string if the data_parts is set to 1 but no data is given. Will return an empty tuple
        if data_parts is > 1 and no data given.
        """
        data = msg.content.strip().split(" ", data_parts)[1:]
        # sanitize the input to only have one space in case multiple put in
        data = tuple(" ".join(s.split()) for s in data)
        if data_parts == 1:
            return "" if not data else data[0]
        return data

    @property
    @abstractmethod
    def help_text(self) -> str:
        return

    @property
    def help_options(self) -> List[str]:
        return []

    @abstractmethod
    async def action(self, msg: discord.message) -> None:
        return


def _get_actions() -> Dict[str, BaseAction]:
    """Loads all actions in the submodule to a dict

    Returns
    -------
    dict of str
        The actions, with class name as key and an instantiated class as value

    Notes
    -----
    Any Action class must be a child of the BaseAction ABC to be added to this dict.
    Done this way so you can create a new file in the actions submodule and it will auto-import and register.
    """
    base_dir = Path(__file__).parent
    actions = {}
    for file in base_dir.iterdir():
        if file.is_dir() or file.name.startswith("__") or not file.name.endswith(".py"):
            continue
        with file.open() as f:
            parsed = ast.parse(f.read())
        classes = [
            node.name for node in ast.walk(parsed) if isinstance(node, ast.ClassDef)
        ]
        rc = import_module(f"movienightbot.actions.{file.stem}")
        for class_name in classes:
            class_def = rc.__dict__[class_name]
            if not issubclass(class_def, BaseAction):
                continue
            actions[class_def.action_name] = class_def()
    return actions


KNOWN_ACTIONS = _get_actions()
