    :"timer.second":

        :description: timer event called each second.
        :payload:
            None

        :abortable: No

    :"player.runCommand":

        :description: When player runs a command.
        :payload:

            :"player": the player
            :"command": what he was up to
            :"args": what he said
        :abortable: Can cancel or modify by returning new value

    :"player.place":

        :description: When player runs a command.
        :payload:

            :"position": position,
            :"clickposition": clickposition,
            :"hand": hand
        :abortable: Yes



