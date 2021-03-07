from . import BaseAction
from ..db.controllers import ServerController


class UserVoteCountAction(BaseAction):
    action_name = "user_vote_count"
    admin = True
    controller = ServerController()

    async def action(self, msg):
        num_votes_per_user = int(self.get_message_data(msg))
        num_votes_per_user = int(num_votes_per_user)
        if num_votes_per_user < 1:
            return (
                msg.channel,
                "Failed: Number of votes per user must be greater than zero.",
            )
        with self.controller.transaction():
            server_row = self.controller.get_by_id(msg.guild.id)
            if num_votes_per_user < server_row.num_votes_per_user:
                return (
                    msg.channel,
                    f"Failed to update: Number of votes per user must be >= {server_row.num_votes_per_user}",
                )
            server_row.num_votes_per_user = int(num_votes_per_user)
            self.controller.update(server_row)
            return (
                msg.channel,
                f"Number of votes per user updated to {num_votes_per_user}",
            )

    @property
    def help_text(self):
        return (
            "Selects a number of random movie suggestions to be voted on. "
            "Must be >= number of movies listed"
        )

    @property
    def help_options(self):
        return ["#"]
