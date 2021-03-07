import discord
import peewee as pw

from . import BaseAction
from ..db.controllers import VoteController, ServerController
from ..util import build_vote_embed, add_vote_emojis


class CancelVoteAction(BaseAction):
    action_name = "cancel_vote"
    admin = True
    controller = VoteController()

    def break_tie(self):
        raise NotImplementedError()

    async def action(self, msg):
        server_id = msg.guild.id
        with self.controller.transaction():
            try:
                vote_msg_id = self.controller.get_by_id(server_id).message_id
            except pw.DoesNotExist:
                await msg.channel.send("No vote started!")
                return
            self.controller.cancel_vote(server_id)
        # TODO: Make more robust so we don't assume the end message and vote message are in same channel
        # probably safe for now, only happens if admin changes bot channel in the middle of a vote
        vote_msg = await msg.channel.fetch_message(vote_msg_id)
        await vote_msg.clear_reactions()
        await vote_msg.edit(content="The movie vote has been cancelled.", embed=None)

    @property
    def help_text(self):
        return (
            "Cancels the currently running vote without selecting a winner."
        )
