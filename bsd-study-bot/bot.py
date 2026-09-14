import os
import random
import traceback
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database
import study
import characters
import quizlet_import
from act_questions import ACT_QUESTIONS


# ============================================================
# LOAD TOKEN
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Add it to your .env file as "
        "DISCORD_TOKEN=your_token_here"
    )


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

IMAGES_DIR = os.path.join(
    BASE_DIR,
    "images"
)

PROFILE_BANNER_FILENAME = "banner.png"


# ============================================================
# IMAGE HELPERS
# ============================================================

def get_image_path(character):
    """
    Get the full path to a character's image.
    """

    filename = character.get("image")

    if not filename:
        return None

    return os.path.join(
        IMAGES_DIR,
        filename
    )


def character_card_description(character, copies=1):
    return (
        "· · ─ ·✶· ─ · ·\n"
        f".　⟢    {character['name']} ﾉ ݁ ˖\n"
        f"␥ {character['rarity']} ⌗ copy’s: {copies} ›\n"
        f"﹒ 𑣲　𓏼　{character['ability']}  ⌣  ."
    )


def compact_collection_card(character, rarity, copies):
    return (
        f".　⟢    {character['name']} ﾉ ݁ ˖ "
        f"␥ {rarity} ⌗ copy’s: {copies} ›"
    )


def image_exists(character):
    """
    Check whether the character's image actually exists.
    """

    path = get_image_path(character)

    if not path:
        print(
            f"❌ NO IMAGE NAME FOR: "
            f"{character.get('name', 'Unknown')}"
        )
        return False

    exists = os.path.isfile(path)

    print(
        f"IMAGE CHECK: "
        f"{character.get('name', 'Unknown')} "
        f"-> {path} "
        f"-> {exists}"
    )

    return exists


def create_image_file(character):
    """
    Create a Discord File for the character image.

    Returns:
        discord.File or None
    """

    path = get_image_path(character)

    if not path:
        print(
            f"❌ IMAGE NAME MISSING: "
            f"{character.get('name', 'Unknown')}"
        )
        return None

    if not os.path.isfile(path):
        print(
            f"❌ IMAGE NOT FOUND: {path}"
        )
        return None

    try:
        filename = os.path.basename(path)

        print(
            f"✅ ATTACHING IMAGE: {path}"
        )

        return discord.File(
            path,
            filename=filename
        )

    except Exception as error:

        print(
            f"❌ COULD NOT CREATE DISCORD FILE: "
            f"{error}"
        )

        traceback.print_exc()

        return None


def attachment_filename(character):
    """
    Return the exact filename Discord will receive.
    """

    path = get_image_path(character)

    if not path:
        return None

    return os.path.basename(path)


def set_character_image(embed, character):
    """
    Add the attachment:// image URL to an embed.

    Returns True if an image exists.
    """

    filename = attachment_filename(character)

    if not filename:
        return False

    if not image_exists(character):
        return False

    embed.set_image(
        url=f"attachment://{filename}"
    )

    return True


def create_profile_banner_file():
    path = os.path.join(
        IMAGES_DIR,
        PROFILE_BANNER_FILENAME
    )

    if not os.path.isfile(path):
        return None

    return discord.File(
        path,
        filename=PROFILE_BANNER_FILENAME
    )


# ============================================================
# SAFE ERROR SENDER
# ============================================================

async def send_error_message(
    interaction,
    message,
    ephemeral=False
):
    """
    Safely send an error message whether the interaction
    has already been acknowledged or not.
    """

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=ephemeral
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=ephemeral
            )

    except Exception as error:

        print(
            f"❌ COULD NOT SEND ERROR MESSAGE: {error}"
        )


# ============================================================
# BOT SETUP
# ============================================================

class BSDStudyBot(commands.Bot):

    async def setup_hook(self):

        try:

            await self.tree.sync()

            for guild in self.guilds:
                guild_object = discord.Object(id=guild.id)
                self.tree.copy_global_to(guild=guild_object)
                await self.tree.sync(guild=guild_object)

            print(
                f"Slash commands synced globally and to {len(self.guilds)} server(s)!"
            )

        except Exception as error:

            print(
                f"Command sync error: {error}"
            )

            traceback.print_exc()


intents = discord.Intents.default()

bot = BSDStudyBot(
    command_prefix=[],
    intents=intents,
    help_command=None
)

guild_commands_synced = False


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    print(f"❌ SLASH COMMAND ERROR: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

    message = "❌ That command ran into an error. Please try again."

    if isinstance(error, app_commands.CommandOnCooldown):
        message = "⏳ Please wait a moment and try again."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception as response_error:
        print(f"❌ COULD NOT ACKNOWLEDGE SLASH ERROR: {response_error}")


# ============================================================
# BOT STARTUP
# ============================================================

@bot.event
async def on_ready():

    global guild_commands_synced

    if not guild_commands_synced:
        for guild in bot.guilds:
            guild_object = discord.Object(id=guild.id)
            bot.tree.copy_global_to(guild=guild_object)
            await bot.tree.sync(guild=guild_object)

        guild_commands_synced = True
        print(
            f"Commands synced to {len(bot.guilds)} server(s)!"
        )

    print("----------------------------")

    print(
        f"Logged in as {bot.user}"
    )

    print(
        "BSD Study Bot is ready!"
    )

    print(
        f"BOT LOCATION: {BASE_DIR}"
    )

    print(
        f"IMAGES LOCATION: {IMAGES_DIR}"
    )

    print(
        "IMAGES FOUND:"
    )

    if os.path.isdir(IMAGES_DIR):

        files = os.listdir(IMAGES_DIR)

        if files:

            for image in sorted(files):

                image_path = os.path.join(
                    IMAGES_DIR,
                    image
                )

                if os.path.isfile(image_path):

                    print(
                        f"  - {image}"
                    )

        else:

            print(
                "  ❌ Images folder is empty!"
            )

    else:

        print(
            "❌ IMAGES FOLDER NOT FOUND!"
        )

    print("----------------------------")


# ============================================================
# CHARACTER COLLECTION VIEW
# ============================================================

class CharacterCollectionView(
    discord.ui.View
):

    def __init__(
        self,
        user_id,
        viewer_id=None,
        show_images=True
    ):

        super().__init__(
            timeout=120
        )

        self.user_id = viewer_id or user_id
        self.collection_user_id = user_id
        self.show_images = show_images

        self.characters = (
            database.get_character_cards(
                user_id
            )
        )

        self.current_index = 0

    # ========================================================
    # GET CURRENT CHARACTER
    # ========================================================

    def get_current_character(self):

        if not self.characters:
            return None

        card_id, character_name, rarity, copies = (
            self.characters[
                self.current_index
            ]
        )

        for character in characters.CHARACTERS:

            if (
                character["name"]
                == character_name
            ):

                return character

        return None

    # ========================================================
    # CREATE EMBED
    # ========================================================

    def create_character_embed(self):

        if not self.characters:

            embed = discord.Embed(

                title="🎴 CHARACTER COLLECTION",

                description=(
                    "You don't have any characters yet :(\n\n"
                    "Study to earn 💎 Ability Crystals, "
                    "then use them to pull characters."
                ),

                color=discord.Color.blue()
            )

            embed.set_footer(
                text="Your collection is waiting..."
            )

            return embed

        (
            card_id,
            character_name,
            rarity,
            copies
        ) = self.characters[
            self.current_index
        ]

        character_data = (
            self.get_current_character()
        )

        if character_data is None:

            return discord.Embed(

                title="🎴 CHARACTER ERROR",

                description=(
                    "This character could not be found "
                    "in characters.py."
                ),

                color=discord.Color.red()
            )

        rarity_colors = {

            "R":
                discord.Color.light_grey(),

            "SR":
                discord.Color.blue(),

            "SSR":
                discord.Color.gold()

        }

        embed = discord.Embed(

            description=character_card_description(
                character_data,
                copies
            ),

            color=rarity_colors.get(
                rarity,
                discord.Color.blue()
            )
        )

        if self.show_images:
            set_character_image(
                embed,
                character_data
            )

        embed.set_footer(
            text=(
                f"Card ID: {card_id}  ·  "
                f"{self.current_index + 1} / {len(self.characters)}"
            )
        )

        return embed

    # ========================================================
    # PREVIOUS
    # ========================================================

    @discord.ui.button(
        label="◀️",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your character collection!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        if not self.characters:

            await interaction.edit_original_response(
                view=self
            )

            return

        self.current_index -= 1

        if self.current_index < 0:

            self.current_index = (
                len(self.characters) - 1
            )

        character = (
            self.get_current_character()
        )

        embed = (
            self.create_character_embed()
        )

        image_file = None

        if character and self.show_images:

            image_file = (
                create_image_file(
                    character
                )
            )

        attachments = []

        if image_file:

            attachments.append(
                image_file
            )

        try:

            await interaction.edit_original_response(

                embed=embed,

                view=self,

                attachments=attachments
            )

        except discord.HTTPException as error:

            print(
                f"❌ DISCORD REJECTED COLLECTION IMAGE: "
                f"{error}"
            )

            await send_error_message(
                interaction,
                f"❌ Discord rejected the photo.\n`{error}`",
                ephemeral=True
            )

    # ========================================================
    # PROFILE
    # ========================================================

    @discord.ui.button(
        label="🏠 Profile",
        style=discord.ButtonStyle.primary
    )
    async def profile_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your profile!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        embed = (
            create_profile_embed(
                interaction.user
            )
        )

        banner_file = create_profile_banner_file()

        attachments = []

        if banner_file:
            attachments.append(banner_file)

        await interaction.edit_original_response(

            embed=embed,

            view=ProfileView(
                self.user_id
            ),

            attachments=attachments
        )

    # ========================================================
    # NEXT
    # ========================================================

    @discord.ui.button(
        label="▶️",
        style=discord.ButtonStyle.secondary
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your character collection!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        if not self.characters:

            await interaction.edit_original_response(
                view=self
            )

            return

        self.current_index += 1

        if (
            self.current_index
            >= len(self.characters)
        ):

            self.current_index = 0

        character = (
            self.get_current_character()
        )

        embed = (
            self.create_character_embed()
        )

        image_file = None

        if character and self.show_images:

            image_file = (
                create_image_file(
                    character
                )
            )

        attachments = []

        if image_file:

            attachments.append(
                image_file
            )

        try:

            await interaction.edit_original_response(

                embed=embed,

                view=self,

                attachments=attachments
            )

        except discord.HTTPException as error:

            print(
                f"❌ DISCORD REJECTED COLLECTION IMAGE: "
                f"{error}"
            )

            await send_error_message(
                interaction,
                f"❌ Discord rejected the photo.\n`{error}`",
                ephemeral=True
            )


class CompactCollectionView(discord.ui.View):

    def __init__(self, user_id, viewer_id, target_name):
        super().__init__(timeout=180)
        self.user_id = viewer_id
        self.target_name = target_name
        self.cards = database.get_character_cards(user_id)
        self.page = 0

    def page_cards(self):
        start = self.page * 6
        return self.cards[start:start + 6]

    def create_page_embed(self):
        lines = []

        for card_id, character_name, rarity, copies in self.page_cards():
            character_data = next(
                (
                    character
                    for character in characters.CHARACTERS
                    if character["name"] == character_name
                ),
                None
            )

            if character_data is None:
                continue

            lines.append(
                f".{card_id}　⟢    {character_name} ﾉ ݁ ˖ "
                f"␥ {rarity} ⌗ copy’s: {copies} ›"
            )

        total_pages = max(1, (len(self.cards) + 5) // 6)
        return discord.Embed(
            title=(
                f"🎴 {self.target_name}'s Collection "
                f"· {self.page + 1}/{total_pages}"
            ),
            description="\n".join(lines),
            color=discord.Color.from_rgb(190, 155, 190)
        )

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your collection view!",
                ephemeral=True
            )
            return False

        return True

    async def update_page(self, interaction):
        await interaction.response.edit_message(
            embed=self.create_page_embed(),
            view=self
        )

    @discord.ui.button(
        label="◀️",
        style=discord.ButtonStyle.secondary
    )
    async def previous_page(self, interaction, button):
        total_pages = max(1, (len(self.cards) + 5) // 6)
        self.page = (self.page - 1) % total_pages
        await self.update_page(interaction)

    @discord.ui.button(
        label="▶️",
        style=discord.ButtonStyle.secondary
    )
    async def next_page(self, interaction, button):
        total_pages = max(1, (len(self.cards) + 5) // 6)
        self.page = (self.page + 1) % total_pages
        await self.update_page(interaction)


# ============================================================
# PROFILE EMBED
# ============================================================

def create_profile_embed(user):

    database.create_user(
        user.id,
        user.name
    )

    (
        username,
        total_seconds,
        crystals
    ) = database.get_user(
        user.id
    )

    session_count = (
        database.get_session_count(
            user.id
        )
    )

    owned_characters = (
        database.get_characters(
            user.id
        )
    )

    embed = discord.Embed(
        title=(
            f"✿  {username}  𓏼  # “to the stray dogs”  ⋆˚꩜"
        ),
        description=(
            "𓈒 ̣̣̣ e ִ⑅　꒰ᐢ . ݂ . ᐢ꒱　"
            f"ability crystals:{crystals}　　　 "
            f"sessions completed:{session_count}　𓈃\n"
            f"𓏼⚞ ۫ ˖　Characters owned  ๑  {len(owned_characters):02d}　♡❘❙"
        ),
        color=discord.Color.from_rgb(190, 155, 190)
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    if os.path.isfile(
        os.path.join(IMAGES_DIR, PROFILE_BANNER_FILENAME)
    ):
        embed.set_image(
            url=f"attachment://{PROFILE_BANNER_FILENAME}"
        )

    return embed


# ============================================================
# PROFILE VIEW
# ============================================================

class ProfileView(
    discord.ui.View
):

    def __init__(
        self,
        user_id
    ):

        super().__init__(
            timeout=120
        )

        self.user_id = user_id

    @discord.ui.button(
        label="🎴 Character Collection",
        style=discord.ButtonStyle.primary
    )
    async def collection(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your profile!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        view = CharacterCollectionView(
            self.user_id
        )

        character = (
            view.get_current_character()
        )

        image_file = None

        if character:

            image_file = (
                create_image_file(
                    character
                )
            )

        attachments = []

        if image_file:

            attachments.append(
                image_file
            )

        try:

            await interaction.edit_original_response(

                embed=(
                    view.create_character_embed()
                ),

                view=view,

                attachments=attachments
            )

        except discord.HTTPException as error:

            print(
                f"❌ DISCORD REJECTED COLLECTION IMAGE: "
                f"{error}"
            )

            await send_error_message(
                interaction,
                f"❌ Discord rejected the photo.\n`{error}`",
                ephemeral=True
            )


# ============================================================
# /STUDY_START
# ============================================================

@bot.tree.command(
    name="study_start",
    description="Start a study session!"
)
@app_commands.describe(
    subject="What are you studying?"
)
async def study_start(
    interaction: discord.Interaction,
    subject: str
):

    await interaction.response.defer()

    user = interaction.user

    try:

        success = study.start_session(
            user.id,
            user.name,
            subject
        )

        if not success:

            await interaction.followup.send(

                "⚠️ You're already studying!\n"
                "Use `/study_end` when you're finished.",

                ephemeral=True
            )

            return

        embed = discord.Embed(

            title="📚 STUDY SESSION STARTED",

            description=(

                f"**Subject:** {subject}\n\n"

                "Your study time is now being "
                "tracked!\n\n"

                "💎 **1 minute = 1 Ability Crystal**"

            ),

            color=discord.Color.blue()
        )

        embed.set_footer(
            text=(
                "Kunikida is watching. "
                "Study properly."
            )
        )

        await interaction.followup.send(
            embed=embed
        )

    except Exception as error:

        print(
            f"❌ STUDY_START ERROR: {error}"
        )

        traceback.print_exc()

        await send_error_message(
            interaction,
            f"❌ Something went wrong.\n`{error}`",
            ephemeral=True
        )


# ============================================================
# /STUDY_END
# ============================================================

@bot.tree.command(
    name="study_end",
    description="End your current study session."
)
async def study_end(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    user = interaction.user

    try:

        result = study.end_session(
            user.id
        )

        if result is None:

            await interaction.followup.send(

                "⚠️ You don't have an active "
                "study session!",

                ephemeral=True
            )

            return

        duration = study.format_time(
            result["duration"]
        )

        embed = discord.Embed(

            title="🎉 STUDY SESSION COMPLETE!",

            description=(

                f"**Subject:** "
                f"{result['subject']}\n"

                f"**Time Studied:** "
                f"{duration}\n"

                f"**💎 Crystals Earned:** "
                f"{result['crystals']}"

            ),

            color=discord.Color.green()
        )

        embed.set_footer(
            text=(
                "Ranpo says you did adequately."
            )
        )

        await interaction.followup.send(
            embed=embed
        )

    except Exception as error:

        print(
            f"❌ STUDY_END ERROR: {error}"
        )

        traceback.print_exc()

        await send_error_message(
            interaction,
            f"❌ Something went wrong.\n`{error}`",
            ephemeral=True
        )


def command_help_text():
    return (
        "**BSD STUDY BOT COMMANDS**\n\n"
        "**Study**\n"
        "`/study_start subject:<name>` — start studying\n"
        "`/study_end` — end studying and earn crystals\n"
        "`/profile` — view your profile\n\n"
        "`/collection [user_id]` — browse text-only cards with buttons\n"
        "`/view card_id:<ID>` — open one card directly\n\n"
        "**Quizzes**\n"
        "`/act_quiz` — start the built-in ACT-style quiz\n"
        "`/quiz_create` — make a question set\n"
        "`/quiz_import` — import a Quizlet URL or export\n"
        "`/quiz_sets` — list your sets\n"
        "`/quiz_start` — start a saved set\n\n"
        "**Other**\n"
        "`/pull` — spend 100 crystals for a character\n"
        "`/pull10` — spend 1,000 crystals for ten characters\n"
        "`/help` — show this guide"
    )


def create_collection_card_embed(character_data, rarity, copies):
    rarity_colors = {
        "R": discord.Color.light_grey(),
        "SR": discord.Color.blue(),
        "SSR": discord.Color.gold()
    }

    embed = discord.Embed(
        description=character_card_description(
            character_data,
            copies
        ),
        color=rarity_colors.get(
            rarity,
            discord.Color.blue()
        )
    )

    set_character_image(embed, character_data)
    return embed


@bot.tree.command(
    name="collection",
    description="View every character card in a collection."
)
@app_commands.describe(
    user_id="Optional Discord user ID; leave blank to view your collection"
)
async def collection(
    interaction: discord.Interaction,
    user_id: str = None
):
    await interaction.response.defer()

    try:
        target_id = interaction.user.id
        target_name = interaction.user.display_name

        if user_id:
            try:
                target_id = int(user_id.strip())
            except ValueError:
                await interaction.followup.send(
                    "❌ User ID must contain numbers only.",
                    ephemeral=True
                )
                return

            try:
                target_user = await bot.fetch_user(target_id)
                target_name = target_user.display_name
            except discord.NotFound:
                target_name = f"User {target_id}"

        view = CompactCollectionView(
            target_id,
            interaction.user.id,
            target_name
        )

        if not view.cards:
            await interaction.followup.send(
                f"🎴 **{target_name}** does not have any character cards yet."
            )
            return

        await interaction.followup.send(
            embed=view.create_page_embed(),
            view=view
        )
    except Exception as error:
        print(f"❌ COLLECTION ERROR: {error}")
        traceback.print_exc()
        try:
            await interaction.followup.send(
                f"❌ Collection error: `{error}`",
                ephemeral=True
            )
        except Exception as response_error:
            print(f"❌ COLLECTION ERROR RESPONSE FAILED: {response_error}")


@bot.tree.command(
    name="view",
    description="View one character card by its card ID."
)
@app_commands.describe(card_id="The card ID shown at the bottom of a card")
async def view_card(
    interaction: discord.Interaction,
    card_id: int
):
    await interaction.response.defer()

    try:
        card = database.get_character_card(card_id)

        if not card:
            await interaction.followup.send(
                "❌ That card ID does not exist.",
                ephemeral=True
            )
            return

        card_owner_id = card[1]
        view = CharacterCollectionView(
            card_owner_id,
            interaction.user.id
        )

        for index, saved_card in enumerate(view.characters):
            if saved_card[0] == card_id:
                view.current_index = index
                break

        character = view.get_current_character()
        image_file = create_image_file(character) if character else None
        message_kwargs = {
            "embed": view.create_character_embed(),
            "view": view
        }

        if image_file:
            message_kwargs["file"] = image_file

        await interaction.followup.send(**message_kwargs)
    except Exception as error:
        print(f"❌ VIEW CARD ERROR: {error}")
        traceback.print_exc()
        await interaction.followup.send(
            "❌ I couldn't load that card.",
            ephemeral=True
        )


# ============================================================
# /PROFILE
# ============================================================

async def delete_old_profile_messages(channel):
    if channel is None or not hasattr(channel, "history"):
        return

    deleted_count = 0

    try:
        async for message in channel.history(limit=None):
            if message.author.id != bot.user.id or not message.embeds:
                continue

            profile_embed = message.embeds[0]
            title = (profile_embed.title or "").casefold()
            footer = (profile_embed.footer.text or "").casefold()
            has_profile_button = any(
                getattr(component, "label", "") == "🎴 Character Collection"
                for row in message.components
                for component in row.children
            )

            if (
                ("study" in title and "profile" in title)
                or "to the stray dogs" in title
                or "study harder. collect them all." in footer
                or "study, collect, and keep going" in footer
                or has_profile_button
            ):
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.Forbidden as error:
                    print(
                        "❌ CANNOT DELETE PROFILE MESSAGE: "
                        "the bot needs Manage Messages permission. "
                        f"{error}"
                    )
                except discord.HTTPException as error:
                    print(f"❌ COULD NOT DELETE PROFILE MESSAGE: {error}")
            elif is_legacy_character_card(message):
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.Forbidden as error:
                    print(
                        "❌ CANNOT DELETE OLD CHARACTER CARD: "
                        "the bot needs Manage Messages permission. "
                        f"{error}"
                    )
                except discord.HTTPException as error:
                    print(f"❌ COULD NOT DELETE OLD CHARACTER CARD: {error}")
    except discord.HTTPException as error:
        print(f"❌ COULD NOT CLEAN OLD PROFILES: {error}")

    print(f"PROFILE CLEANUP: deleted {deleted_count} old profile message(s)")


def is_current_profile_message(message):
    if not message.embeds:
        return False

    embed = message.embeds[0]
    title = (embed.title or "").casefold()
    description = (embed.description or "").casefold()

    return (
        "to the stray dogs" in title
        and "ability crystals:" in description
        and "sessions completed:" in description
        and "characters owned" in description
    )


def is_current_character_card(message):
    if not message.embeds:
        return False

    description = message.embeds[0].description or ""
    return description.startswith("· · ─ ·✶· ─ · ·")


def is_legacy_character_card(message):
    if not message.embeds or is_current_profile_message(message):
        return False

    embed = message.embeds[0]
    title = (embed.title or "").casefold()
    footer = (embed.footer.text or "").casefold()
    has_image = bool(embed.image.url)

    return (
        has_image
        and not is_current_character_card(message)
        and (
            "character" in title
            or "gacha" in title
            or "pull" in title
            or "character" in footer
            or "10-pull" in footer
        )
    )


async def delete_legacy_profiles_everywhere():
    deleted_count = 0

    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=None):
                    if message.author.id != bot.user.id:
                        continue

                    if not message.embeds or is_current_profile_message(message):
                        continue

                    embed = message.embeds[0]
                    title = (embed.title or "").casefold()
                    footer = (embed.footer.text or "").casefold()
                    has_profile_button = any(
                        getattr(component, "label", "") == "🎴 Character Collection"
                        for row in message.components
                        for component in row.children
                    )

                    if (
                        ("study" in title and "profile" in title)
                        or "to the stray dogs" in title
                        or "study harder. collect them all." in footer
                        or "study, collect, and keep going" in footer
                        or has_profile_button
                    ):
                        await message.delete()
                        deleted_count += 1
                    elif is_legacy_character_card(message):
                        await message.delete()
                        deleted_count += 1
            except discord.Forbidden:
                print(
                    f"❌ Cannot clean profiles in #{channel.name}: "
                    "Manage Messages permission is required."
                )
            except discord.HTTPException as error:
                print(f"❌ Could not clean #{channel.name}: {error}")

    print(
        f"STARTUP PROFILE CLEANUP: deleted "
        f"{deleted_count} legacy profile message(s)"
    )

@bot.tree.command(
    name="profile",
    description="View your BSD study profile."
)
async def profile(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:
        embed = create_profile_embed(
            interaction.user
        )

        banner_file = create_profile_banner_file()

        await interaction.followup.send(

            embed=embed,

            view=ProfileView(
                interaction.user.id
            ),

            file=banner_file
        )

    except Exception as error:

        print(
            f"❌ PROFILE ERROR: {error}"
        )

        traceback.print_exc()

        await send_error_message(
            interaction,
            f"❌ Something went wrong.\n`{error}`",
            ephemeral=True
        )


@bot.tree.command(
    name="help",
    description="Show the bot command guide."
)
async def slash_help(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(command_help_text(), ephemeral=True)


# ============================================================
# 10-PULL RESULTS VIEW
# ============================================================

class PullResultsView(
    discord.ui.View
):

    def __init__(
        self,
        user_id,
        results
    ):

        super().__init__(
            timeout=180
        )

        self.user_id = user_id

        self.results = results

        self.current_index = 0

    # ========================================================
    # CREATE EMBED
    # ========================================================

    def create_embed(self):

        character = (
            self.results[
                self.current_index
            ]
        )

        rarity_colors = {

            "R":
                discord.Color.light_grey(),

            "SR":
                discord.Color.blue(),

            "SSR":
                discord.Color.gold()

        }

        embed = discord.Embed(

            description=(
                character_card_description(character)
                + "\n\n"
                + f"Pull: {self.current_index + 1} / {len(self.results)}"
            ),

            color=rarity_colors.get(

                character["rarity"],

                discord.Color.blue()

            )
        )

        set_character_image(
            embed,
            character
        )

        embed.set_footer(
            text="Use ◀️ ▶️ to view every card."
        )

        return embed

    # ========================================================
    # PREVIOUS
    # ========================================================

    @discord.ui.button(
        label="◀️",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your pull!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        self.current_index -= 1

        if self.current_index < 0:

            self.current_index = (
                len(self.results) - 1
            )

        character = (
            self.results[
                self.current_index
            ]
        )

        image_file = (
            create_image_file(
                character
            )
        )

        attachments = []

        if image_file:

            attachments.append(
                image_file
            )

        try:

            await interaction.edit_original_response(

                embed=self.create_embed(),

                view=self,

                attachments=attachments
            )

        except discord.HTTPException as error:

            print(
                f"❌ DISCORD REJECTED 10-PULL IMAGE: "
                f"{error}"
            )

            await send_error_message(
                interaction,
                f"❌ Discord rejected the photo.\n`{error}`",
                ephemeral=True
            )

    # ========================================================
    # CLOSE
    # ========================================================

    @discord.ui.button(
        label="❌ Close",
        style=discord.ButtonStyle.danger
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your pull!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        try:

            await interaction.delete_original_response()

        except Exception as error:

            print(
                f"❌ COULD NOT DELETE PULL: {error}"
            )

    # ========================================================
    # NEXT
    # ========================================================

    @discord.ui.button(
        label="▶️",
        style=discord.ButtonStyle.secondary
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            interaction.user.id
            != self.user_id
        ):

            await interaction.response.send_message(
                "This isn't your pull!",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        self.current_index += 1

        if (
            self.current_index
            >= len(self.results)
        ):

            self.current_index = 0

        character = (
            self.results[
                self.current_index
            ]
        )

        image_file = (
            create_image_file(
                character
            )
        )

        attachments = []

        if image_file:

            attachments.append(
                image_file
            )

        try:

            await interaction.edit_original_response(

                embed=self.create_embed(),

                view=self,

                attachments=attachments
            )

        except discord.HTTPException as error:

            print(
                f"❌ DISCORD REJECTED 10-PULL IMAGE: "
                f"{error}"
            )

            await send_error_message(
                interaction,
                f"❌ Discord rejected the photo.\n`{error}`",
                ephemeral=True
            )


# ============================================================
# /PULL
# ============================================================

@bot.tree.command(
    name="pull",
    description=(
        "Spend 100 Ability Crystals "
        "to pull a BSD character!"
    )
)
async def pull(
    interaction: discord.Interaction
):

    # ========================================================
    # VERY FIRST THING
    # ========================================================

    await interaction.response.defer()

    try:

        user = interaction.user

        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        database.create_user(
            user.id,
            user.name
        )

        (
            username,
            total_seconds,
            crystals
        ) = database.get_user(
            user.id
        )

        # ----------------------------------------------------
        # CHECK CRYSTALS
        # ----------------------------------------------------

        if crystals < 100:

            await interaction.followup.send(

                f"❌ You need "
                f"**100 💎 Ability Crystals** "
                f"to pull!\n\n"

                f"You currently have "
                f"**{crystals} 💎**."
            )

            return

        # ----------------------------------------------------
        # SPEND CRYSTALS
        # ----------------------------------------------------

        database.update_user_stats(
            user.id,
            0,
            -100
        )

        # ----------------------------------------------------
        # RANDOM CHARACTER
        # ----------------------------------------------------

        character = random.choice(
            characters.CHARACTERS
        )

        print(
            "================================"
        )

        print(
            f"PULLED CHARACTER: "
            f"{character['name']}"
        )

        print(
            f"RARITY: "
            f"{character['rarity']}"
        )

        print(
            f"IMAGE NAME: "
            f"{character['image']}"
        )

        print(
            f"IMAGE PATH: "
            f"{get_image_path(character)}"
        )

        # ----------------------------------------------------
        # SAVE CHARACTER
        # ----------------------------------------------------

        database.add_character(
            user.id,
            character["name"],
            character["rarity"]
        )

        # ----------------------------------------------------
        # RARITY COLORS
        # ----------------------------------------------------

        rarity_colors = {

            "R":
                discord.Color.light_grey(),

            "SR":
                discord.Color.blue(),

            "SSR":
                discord.Color.gold()

        }

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(

            description=character_card_description(character),

            color=rarity_colors.get(

                character["rarity"],

                discord.Color.blue()

            )
        )

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        if not image_exists(character):

            print(
                "❌ PHOTO NOT FOUND"
            )

            await interaction.followup.send(

                embed=embed,

                content=(
                    "❌ **Photo not found.**\n"
                    f"Expected file: "
                    f"`{character['image']}`"
                )
            )

            return

        image_file = (
            create_image_file(
                character
            )
        )

        if image_file is None:

            await interaction.followup.send(

                embed=embed,

                content=(
                    "❌ **Photo could not be attached.**"
                )
            )

            return

        filename = (
            attachment_filename(
                character
            )
        )

        embed.set_image(
            url=f"attachment://{filename}"
        )

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

        try:

            await interaction.followup.send(

                embed=embed,

                file=image_file
            )

            print(
                "✅ PULL SENT SUCCESSFULLY"
            )

        except discord.HTTPException as error:

            print(
                "❌ DISCORD REJECTED THE "
                "ATTACHMENT/EMBED"
            )

            print(
                f"HTTP ERROR: {error}"
            )

            traceback.print_exc()

            # Send text-only fallback
            try:

                await interaction.followup.send(

                    embed=embed,

                    content=(
                        "⚠️ **Discord rejected the photo.**\n"
                        f"Discord error: `{error}`"
                    )
                )

            except discord.HTTPException as second_error:

                print(
                    f"❌ FALLBACK ALSO FAILED: "
                    f"{second_error}"
                )

        print(
            "================================"
        )

    except Exception as error:

        print(
            f"❌ PULL COMMAND ERROR: {error}"
        )

        traceback.print_exc()

        await send_error_message(
            interaction,
            f"❌ Something went wrong.\n`{error}`"
        )


# ============================================================
# QUIZZES
# ============================================================

def ensure_act_set(user):
    database.create_user(user.id, user.name)
    return database.ensure_question_set(
        user.id,
        "ACT Practice",
        ACT_QUESTIONS,
        source="original ACT-style practice"
    )

def normalize_answer(answer):
    return " ".join(answer.casefold().strip().split())


def create_quiz_embed(quiz_view, finished=False):
    if finished:
        title = "✅ QUIZ COMPLETE"
        description = (
            f"**{quiz_view.score} / {len(quiz_view.questions)} correct**\n\n"
            f"You earned **{quiz_view.score * 10} 💎 Ability Crystals**."
        )
    else:
        prompt, answer = quiz_view.questions[quiz_view.current_index]
        title = f"🧠 {quiz_view.set_name}"
        description = (
            f"**Question {quiz_view.current_index + 1} / "
            f"{len(quiz_view.questions)}**\n\n{prompt}"
        )

        if quiz_view.answered:
            description += f"\n\nAnswer submitted. Press **Next**."

    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green() if finished else discord.Color.blue()
    )


class QuizAnswerModal(discord.ui.Modal, title="Your Answer"):

    answer = discord.ui.TextInput(
        label="Answer",
        placeholder="Type your answer...",
        required=True,
        max_length=1000
    )

    def __init__(self, quiz_view):
        super().__init__()
        self.quiz_view = quiz_view

    async def on_submit(self, interaction):
        if self.quiz_view.answered:
            await interaction.response.send_message(
                "This question has already been answered.",
                ephemeral=True
            )
            return

        prompt, correct_answer = self.quiz_view.questions[
            self.quiz_view.current_index
        ]
        self.quiz_view.answered = True
        self.quiz_view.next_button.disabled = False
        is_correct = normalize_answer(self.answer.value) == normalize_answer(
            correct_answer
        )

        if is_correct:
            self.quiz_view.score += 1
            database.update_user_stats(
                interaction.user.id,
                0,
                10
            )
            result = "✅ Correct! You earned **10 💎 Ability Crystals**."
        else:
            result = f"❌ Not quite. The answer was **{correct_answer}**."

        await interaction.response.send_message(result, ephemeral=True)

        if self.quiz_view.message:
            await self.quiz_view.message.edit(
                embed=create_quiz_embed(self.quiz_view),
                view=self.quiz_view
            )


class QuizView(discord.ui.View):

    def __init__(self, user_id, set_name, questions):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.set_name = set_name
        self.questions = questions
        self.current_index = 0
        self.score = 0
        self.answered = False
        self.message = None

        self.next_button.disabled = True

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your quiz!",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Answer",
        emoji="✍️",
        style=discord.ButtonStyle.primary
    )
    async def answer_button(self, interaction, button):
        if self.answered:
            await interaction.response.send_message(
                "You already answered this question.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(QuizAnswerModal(self))

    @discord.ui.button(
        label="Next",
        emoji="➡️",
        style=discord.ButtonStyle.secondary
    )
    async def next_button(self, interaction, button):
        self.current_index += 1

        if self.current_index >= len(self.questions):
            self.stop()
            await interaction.response.edit_message(
                embed=create_quiz_embed(self, finished=True),
                view=None
            )
            return

        self.answered = False
        self.next_button.disabled = True
        self.answer_button.disabled = False
        await interaction.response.edit_message(
            embed=create_quiz_embed(self),
            view=self
        )


@bot.tree.command(
    name="quiz_create",
    description="Create a question set from question | answer lines."
)
@app_commands.describe(
    name="The name of your question set",
    questions="One question | answer pair per line"
)
async def quiz_create(interaction, name: str, questions: str):
    await interaction.response.defer(ephemeral=True)

    try:
        parsed_questions = quizlet_import.parse_question_text(questions)

        if not parsed_questions:
            await interaction.followup.send(
                "❌ No questions found. Use one `question | answer` pair per line.",
                ephemeral=True
            )
            return

        if len(parsed_questions) > 50:
            await interaction.followup.send(
                "❌ A question set can contain at most 50 questions.",
                ephemeral=True
            )
            return

        database.create_user(interaction.user.id, interaction.user.name)
        database.create_question_set(
            interaction.user.id,
            name,
            parsed_questions
        )

        await interaction.followup.send(
            f"✅ Created **{name}** with **{len(parsed_questions)} questions**.",
            ephemeral=True
        )
    except Exception as error:
        print(f"❌ QUIZ_CREATE ERROR: {error}")
        traceback.print_exc()
        await interaction.followup.send(
            "❌ I couldn't create that question set.",
            ephemeral=True
        )


@bot.tree.command(
    name="quiz_import",
    description="Import a public Quizlet set or pasted Quizlet export."
)
@app_commands.describe(
    name="The name to give the imported question set",
    source="A public Quizlet URL, or pasted term<TAB>definition text"
)
async def quiz_import(interaction, name: str, source: str):
    await interaction.response.defer(ephemeral=True)

    try:
        parsed_questions = await asyncio.to_thread(
            quizlet_import.import_source,
            source
        )

        if len(parsed_questions) > 50:
            await interaction.followup.send(
                "❌ An imported set can contain at most 50 questions.",
                ephemeral=True
            )
            return

        database.create_user(interaction.user.id, interaction.user.name)
        database.create_question_set(
            interaction.user.id,
            name,
            parsed_questions,
            source="quizlet",
            source_url=source if source.startswith("http") else None
        )

        await interaction.followup.send(
            f"✅ Imported **{len(parsed_questions)} questions** into **{name}**.",
            ephemeral=True
        )
    except Exception as error:
        await interaction.followup.send(
            f"❌ Quizlet import failed: `{error}`",
            ephemeral=True
        )


@bot.tree.command(
    name="quiz_sets",
    description="List your question sets."
)
async def quiz_sets(interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        ensure_act_set(interaction.user)
        sets = database.get_question_sets(interaction.user.id)

        if not sets:
            await interaction.followup.send(
                "You have no question sets yet. Use `/quiz_create` or `/quiz_import`.",
                ephemeral=True
            )
            return

        lines = [
            f"**{name}** — {question_count} questions ({source})"
            for set_id, name, source, question_count in sets
        ]
        await interaction.followup.send("\n".join(lines), ephemeral=True)
    except Exception as error:
        print(f"❌ QUIZ_SETS ERROR: {error}")
        traceback.print_exc()
        await interaction.followup.send(
            "❌ I couldn't load your question sets.",
            ephemeral=True
        )


@bot.tree.command(
    name="quiz_start",
    description="Start a quiz from one of your question sets."
)
@app_commands.describe(name="The exact name of the question set")
async def quiz_start(interaction, name: str):
    await interaction.response.defer()
    try:
        ensure_act_set(interaction.user)
        question_set, questions = database.get_question_set(
            interaction.user.id,
            name
        )

        if not question_set or not questions:
            await interaction.followup.send(
                "❌ Question set not found. Use `/quiz_sets` to see your sets.",
                ephemeral=True
            )
            return

        view = QuizView(interaction.user.id, question_set[1], questions)
        quiz_message = await interaction.followup.send(
            embed=create_quiz_embed(view),
            view=view
        )
        view.message = quiz_message
    except Exception as error:
        print(f"❌ QUIZ_START ERROR: {error}")
        traceback.print_exc()
        await interaction.followup.send(
            "❌ I couldn't start that quiz.",
            ephemeral=True
        )


@bot.tree.command(
    name="act_quiz",
    description="Start the built-in ACT-style practice quiz."
)
async def act_quiz(interaction):
    await interaction.response.defer()
    try:
        ensure_act_set(interaction.user)
        question_set, questions = database.get_question_set(
            interaction.user.id,
            "ACT Practice"
        )

        if not question_set or not questions:
            await interaction.followup.send(
                "❌ The ACT practice set is unavailable.",
                ephemeral=True
            )
            return

        view = QuizView(interaction.user.id, question_set[1], questions)
        quiz_message = await interaction.followup.send(
            embed=create_quiz_embed(view),
            view=view
        )
        view.message = quiz_message
    except Exception as error:
        print(f"❌ ACT_QUIZ ERROR: {error}")
        traceback.print_exc()
        await interaction.followup.send(
            "❌ I couldn't start the ACT quiz.",
            ephemeral=True
        )


# ============================================================
# /PULL10
# ============================================================

@bot.tree.command(
    name="pull10",
    description=(
        "Spend 1,000 Ability Crystals "
        "for 10 BSD characters!"
    )
)
async def pull10(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        user = interaction.user

        database.create_user(
            user.id,
            user.name
        )

        (
            username,
            total_seconds,
            crystals
        ) = database.get_user(
            user.id
        )

        # ----------------------------------------------------
        # CHECK CRYSTALS
        # ----------------------------------------------------

        if crystals < 1000:

            await interaction.followup.send(

                f"❌ You need "
                f"**1,000 💎 Ability Crystals** "
                f"for a 10-pull!\n\n"

                f"You currently have "
                f"**{crystals} 💎**."
            )

            return

        # ----------------------------------------------------
        # SPEND CRYSTALS
        # ----------------------------------------------------

        database.update_user_stats(
            user.id,
            0,
            -1000
        )

        # ----------------------------------------------------
        # PULL 10
        # ----------------------------------------------------

        results = []

        for _ in range(10):

            character = random.choice(
                characters.CHARACTERS
            )

            database.add_character(
                user.id,
                character["name"],
                character["rarity"]
            )

            results.append(
                character
            )

        # ----------------------------------------------------
        # CREATE VIEW
        # ----------------------------------------------------

        view = PullResultsView(
            user.id,
            results
        )

        # ----------------------------------------------------
        # FIRST CHARACTER
        # ----------------------------------------------------

        first_character = results[0]

        print(
            "================================"
        )

        print(
            "10-PULL RESULTS:"
        )

        for number, character in enumerate(
            results,
            start=1
        ):

            print(
                f"{number}. "
                f"{character['name']} "
                f"({character['rarity']}) "
                f"-> {character['image']}"
            )

        print(
            "================================"
        )

        embed = (
            view.create_embed()
        )

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        if not image_exists(first_character):

            await interaction.followup.send(

                embed=embed,

                view=view,

                content=(
                    "❌ **Photo not found for this character.**\n"
                    f"Expected file: "
                    f"`{first_character['image']}`"
                )
            )

            return

        image_file = (
            create_image_file(
                first_character
            )
        )

        if image_file is None:

            await interaction.followup.send(

                embed=embed,

                view=view,

                content=(
                    "❌ **Photo could not be attached.**"
                )
            )

            return

        filename = (
            attachment_filename(
                first_character
            )
        )

        embed.set_image(
            url=f"attachment://{filename}"
        )

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

        try:

            await interaction.followup.send(

                embed=embed,

                view=view,

                file=image_file
            )

            print(
                "✅ 10-PULL SENT SUCCESSFULLY"
            )

        except discord.HTTPException as error:

            print(
                "❌ DISCORD REJECTED THE "
                "10-PULL ATTACHMENT/EMBED"
            )

            print(
                f"HTTP ERROR: {error}"
            )

            traceback.print_exc()

            try:

                await interaction.followup.send(

                    embed=embed,

                    view=view,

                    content=(
                        "⚠️ **Discord rejected the photo.**\n"
                        f"Discord error: `{error}`"
                    )
                )

            except discord.HTTPException as second_error:

                print(
                    f"❌ FALLBACK FAILED: "
                    f"{second_error}"
                )

    except Exception as error:

        print(
            f"❌ PULL10 COMMAND ERROR: {error}"
        )

        traceback.print_exc()

        await send_error_message(
            interaction,
            f"❌ Something went wrong.\n`{error}`"
        )


# ============================================================
# /TEST_CRYSTALS
# ============================================================

@bot.tree.command(
    name="test_crystals",
    description="Give yourself test Ability Crystals."
)
async def test_crystals(
    interaction: discord.Interaction
):

    # ========================================================
    # RESPOND IMMEDIATELY
    # ========================================================

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        # ----------------------------------------------------
        # CHECK USER
        # ----------------------------------------------------

        if (
            interaction.user.id
            != 1000256548825735208
        ):

            await interaction.followup.send(

                "❌ You can't use this command.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        database.create_user(
            interaction.user.id,
            interaction.user.name
        )

        # ----------------------------------------------------
        # GIVE CRYSTALS
        # ----------------------------------------------------

        database.set_crystals(
            interaction.user.id,
            1000
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        await interaction.followup.send(

            "🧪 **TEST MODE**\n\n"

            "You now have "
            "**1,000 💎 Ability Crystals**!\n\n"

            "That's enough for "
            "**10 pulls**.",

            ephemeral=True
        )

    except Exception as error:

        print(
            f"❌ TEST_CRYSTALS ERROR: {error}"
        )

        traceback.print_exc()

        await send_error_message(
            interaction,
            f"❌ Something went wrong.\n`{error}`",
            ephemeral=True
        )


# ============================================================
# DATABASE
# ============================================================

database.setup_database()


# ============================================================
# START BOT
# ============================================================

try:

    bot.run(
        TOKEN
    )

except discord.errors.PrivilegedIntentsRequired:

    print(
        "\nDiscord bot startup blocked: "
        "Message Content Intent is disabled."
    )

    print(
        "\nGo to the Discord Developer Portal."
    )

    print(
        "Select your app -> Bot."
    )

    print(
        "Enable "
        "'Message Content Intent'."
    )

    print(
        "Then restart the bot."
    )

except discord.LoginFailure:

    print(
        "\n❌ Discord rejected the bot token."
    )

except Exception as error:

    print(
        f"\n❌ BOT CRASHED: {error}"
    )

    traceback.print_exc()