import discord
import decouple
from discord.ext import commands
import mysql.connector

db_config = {
    'user': decouple.config("DB_USER"),
    'password': decouple.config("DB_PASSWORD"),
    'host': decouple.config("DB_HOST"),
    'port': decouple.config("DB_PORT"),
    'database': decouple.config("DB_NAME")
}

db = mysql.connector.connect(**db_config)
cursor = db.cursor()

buddy = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@buddy.event
async def on_ready():
    print("Ready")
    return await buddy.tree.sync()


@buddy.event
async def on_member_join(member):
    welcome_channel_id = 1199376584738603111
    welcome_channel = buddy.get_channel(welcome_channel_id)
    welcome_message = f"Welcome to the server, {member.name}!"

    await welcome_channel.send(welcome_message)

    try:
        dm_channel = await member.create_dm()
        await dm_channel.send(f"Welcome to the server, {member.name}!")
    except discord.Forbidden:
        print(f"Unable to send DM to {member.name}.")

    return


@buddy.event
async def on_message(message):
    if message.author.bot:
        return
    print(message)
    words = message.content.lower().split()
    discord_id = message.author.id

    for word in words:
        print(word)
        cursor.execute(
            f"""INSERT INTO user_words(discord_id,word)
            VALUES {discord_id},{word};
        """
        )
    db.commit()
    return


@buddy.tree.command(name='word-status', description="description")
async def word_status(interaction):
    cursor.execute("""
        SELECT word, COUNT(word) AS count
        FROM user_words
        GROUP BY word
        ORDER BY count DESC
        LIMIT 10;
    """)
    results = cursor.fetchall()

    response = "Top 10 most used words in the guild:\n"

    for word, count in results:
        response += f"{word}: {count} times\n"

    return await interaction.response.send_message(response)


@buddy.tree.command(name='user-status', description='description')
async def user_status(interaction: discord.Interaction, user: discord.User):
    cursor.execute("""
        SELECT word, COUNT(word) AS count
        FROM user_words
        WHERE discord_id = %s
        GROUP BY word
        ORDER BY count DESC
        LIMIT 10;
    """, (user.id,))
    results = cursor.fetchall()

    response = f"Top 10 most used words by {user.name}:\n"
    for word, count in results:
        response += f"{word}: {count} times\n"

    return await interaction.response.send_message(response)


@buddy.tree.command(name='select-role', description='description')
async def select_role(interaction: discord.Interaction):
    roles = [
        discord.SelectOption(label="Moderator", value="Moderator"),
        discord.SelectOption(label="Guest", value="Guest"),
        discord.SelectOption(label="Developer", value="Developer")
    ]
    select_menu = discord.ui.Select(
        placeholder="Choose a role",
        options=roles
    )
    select_menu = discord.ui.Select(
        placeholder="Choose a role...",
        options=roles
    )

    async def select_callback(interaction: discord.Interaction):
        selected_role = interaction.data["values"][0]
        discord_id = interaction.user.id

        try:
            cursor.execute(
                "REPLACE INTO user_role (discord_id, role) VALUES (%s, %s)",
                (discord_id, selected_role)
            )
            db.commit()

            guild = interaction.guild
            role = discord.utils.get(guild.roles, name=selected_role)
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"You have been given the role: {selected_role}")
            else:
                await interaction.response.send_message(f"Role {selected_role} not found in the server.")

        except mysql.connector.Error as db_err:
            print(f"MySQL error: {db_err}")
            await interaction.response.send_message(
                "An error occurred while updating your role. Please try again later.")

        except discord.HTTPException as discord_err:
            print(f"Discord API error: {discord_err}")
            await interaction.response.send_message(
                "An error occurred while granting you the role. Please try again later.")

        except Exception as err:
            print(f"An unexpected error occurred: {err}")
            await interaction.response.send_message("An unexpected error occurred. Please try again later.")

    select_menu.callback = select_callback

    view = discord.ui.View()
    view.add_item(select_menu)
    await interaction.response.send_message("Select a role:", view=view)


buddy.run(decouple.config("TOKEN"))
