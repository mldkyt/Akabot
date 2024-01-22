import {
    ButtonInteraction,
    CacheType,
    Channel,
    ChatInputCommandInteraction,
    Client,
    Emoji,
    Guild,
    GuildMember,
    Message,
    PermissionsBitField,
    Role,
    SlashCommandSubcommandBuilder,
    Sticker
} from "discord.js";
import { AllCommands, Module } from "./type";
import {
    ChannelSetting,
    IntegerSetting,
    setChannel,
    SettingsCommandBuilder,
    SettingsGroupBuilder,
    StringChoiceSetting,
    StringSetting,
    ToggleSetting
} from "../types/settings";
import { getSetting, setSetting } from "../data/settings";

export class SettingsModule implements Module {
    commands: AllCommands = [
        new SettingsCommandBuilder()
            .addSettingsGroup(
                new SettingsGroupBuilder("logging").addChannelSetting(new ChannelSetting("channel", "loggingChannel"))
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("welcome")
                    .addChannelSetting(new ChannelSetting("channel", "welcomeChannel"))
                    .addStringSetting(
                        new StringChoiceSetting(
                            "name",
                            "welcomeNameType",
                            "Whether to use the username or the global nickname of the user.",
                            [
                                { display: "Username", value: "username" },
                                { display: "Nickname", value: "nickname" }
                            ],
                            "nickname"
                        )
                    )
                    .addStringSetting(
                        new StringSetting(
                            "embed-title",
                            "welcomeEmbedTitle",
                            "The title of the welcome embed.",
                            "Welcome, {user}"
                        )
                    )
                    .addStringSetting(
                        new StringSetting(
                            "embed-message",
                            "welcomeEmbedMessage",
                            "The message of the welcome embed.",
                            "Welcome {user} to this server!"
                        )
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("goodbye")
                    .addChannelSetting(new ChannelSetting("channel", "goodbyeChannel"))
                    .addStringSetting(
                        new StringChoiceSetting(
                            "name",
                            "goodbyeNameType",
                            "Whether to use the username or the global nickname of the user.",
                            [
                                { display: "Username", value: "username" },
                                { display: "Nickname", value: "nickname" }
                            ],
                            "nickname"
                        )
                    )
                    .addStringSetting(
                        new StringSetting(
                            "embed-title",
                            "goodbyeEmbedTitle",
                            "The title of the goodbye embed.",
                            "Goodbye {user}"
                        )
                    )
                    .addStringSetting(
                        new StringSetting(
                            "embed-message",
                            "goodbyeEmbedMessage",
                            "The message of the goodbye embed.",
                            "Goodbye {user}, hope you enjoyed being in this server."
                        )
                    )
                    .addStringSetting(
                        new StringSetting(
                            "embed-message-kick",
                            "goodbyeEmbedMessageKick",
                            "Customized message for kicked people.",
                            "Goodbye {user}, you were kicked from this server for {reason}"
                        )
                    )
                    .addStringSetting(
                        new StringSetting(
                            "embed-message-ban",
                            "goodbyeEmbedMessageBan",
                            "Customized message for banned people.",
                            "Goodbye {user}, you were banned from this server for {reason}"
                        )
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("leveling")
                    .addChannelSetting(new ChannelSetting("channel", "levelingChannel"))
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("add-reward")
                            .setDescription("Add a reward for a level")
                            .addRoleOption((role) =>
                                role
                                    .setName("role")
                                    .setDescription("The role to give to members at the level")
                                    .setRequired(true)
                            )
                            .addNumberOption((level) =>
                                level.setName("level").setDescription("The level to add the role at").setRequired(true)
                            )
                    )
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("remove-reward")
                            .setDescription("Remove a reward on a specified level.")
                            .addNumberOption((level) =>
                                level.setName("level").setDescription("The level to remove at").setRequired(true)
                            )
                    )
                    .addToggleSetting(
                        new ToggleSetting("weekend-boost", "levelingWeekendBoost", "Double points on weekend", true)
                    )
                    .addToggleSetting(
                        new ToggleSetting(
                            "christmas-boost",
                            "levelingChristmasBoost",
                            "Quadruple points on Christmas",
                            true
                        )
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("reactionroles").addSubcommand(
                    new SlashCommandSubcommandBuilder()
                        .setName("new")
                        .setDescription("Create a reaction role")
                        .addStringOption((msg) =>
                            msg.setName("message").setDescription("The message").setRequired(true)
                        )
                        .addStringOption((mode) =>
                            mode
                                .setName("mode")
                                .setDescription("Mode to use this in")
                                .setChoices(
                                    {
                                        name: "Normal - Allow adding and removing",
                                        value: "normal"
                                    },
                                    { name: "Add only", value: "add" },
                                    { name: "Remove only", value: "remove" },
                                    {
                                        name: "Only allow a single role",
                                        value: "single"
                                    }
                                )
                                .setRequired(true)
                        )
                        .addRoleOption((role) => role.setName("role").setDescription("The role").setRequired(true))
                        .addRoleOption((role) => role.setName("role-2").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-3").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-4").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-5").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-6").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-7").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-8").setDescription("The role"))
                        .addRoleOption((role) => role.setName("role-9").setDescription("The role"))
                )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("antiraid")
                    .addStringSetting(
                        new StringChoiceSetting(
                            "newmembers",
                            "AntiRaidNewMembers",
                            "How old does a member have to be to be on this server",
                            [
                                { display: "Disable auto-kick", value: "0" },
                                { display: "Auto-kick members younger than 1 day", value: "1" },
                                { display: "Auto-kick members younger than 3 days", value: "3" },
                                { display: "Auto-kick members younger than 7 days", value: "7" },
                                { display: "Auto-kick members younger than 14 days", value: "14" },
                                { display: "Auto-kick members younger than 30 days", value: "30" }
                            ],
                            "0"
                        )
                    )
                    .addToggleSetting(
                        new ToggleSetting("nopfp", "AntiRaidNoPFP", "Kick members with no profile picture", false)
                    )
                    .addToggleSetting(
                        new ToggleSetting("spamdelete", "AntiRaidSpamDelete", "Delete messages from spammers", false)
                    )
                    .addToggleSetting(
                        new ToggleSetting(
                            "spamtimeout",
                            "AntiRaidSpamTimeout",
                            "Timeout spammers for a short period",
                            false
                        )
                    )
                    .addToggleSetting(
                        new ToggleSetting(
                            "spamalert",
                            "AntiRaidSpamSendAlert",
                            "Tell the spammer to stop spamming",
                            false
                        )
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("mediaonlychannels")
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("set")
                            .setDescription("Mark a channel as image only")
                            .addChannelOption((ch) =>
                                ch.setName("channel").setDescription("The channel").setRequired(true)
                            )
                            .addStringOption((type) =>
                                type
                                    .setName("type")
                                    .setDescription("Allow image, video or both")
                                    .setChoices(
                                        { name: "Image only", value: "image" },
                                        { name: "Video only", value: "video" },
                                        { name: "Image and video", value: "both" }
                                    )
                                    .setRequired(true)
                            )
                            .addBooleanOption((replies) =>
                                replies.setName("allow-replies").setDescription("Allow replies").setRequired(false)
                            )
                    )
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("remove")
                            .setDescription("Remove a channel from media only list")
                            .addChannelOption((ch) =>
                                ch.setName("channel").setDescription("The channel to remove").setRequired(true)
                            )
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("chatrevive")
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("role")
                            .setDescription("Set the role to ping when a channel is revived")
                            .addRoleOption((x) => x.setName("role").setDescription("The role").setRequired(true))
                    )
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("set")
                            .setDescription("Add or update channel's automatic revive settings")
                            .addChannelOption((ch) =>
                                ch.setName("channel").setDescription("The channel").setRequired(true)
                            )
                            .addNumberOption((time) =>
                                time.setName("time").setDescription("Time in hours").setRequired(true)
                            )
                    )
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("remove")
                            .setDescription("Remove channel's automatic revive settings")
                            .addChannelOption((ch) =>
                                ch.setName("channel").setDescription("The channel to remove").setRequired(true)
                            )
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("chatsummary")
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("add-channel")
                            .setDescription("Add a channel to summarize daily")
                            .addChannelOption((ch) =>
                                ch.setName("channel").setDescription("Channel to add").setRequired(true)
                            )
                    )
                    .addSubcommand(
                        new SlashCommandSubcommandBuilder()
                            .setName("remove-channel")
                            .setDescription("Remove a channel from daily summary")
                            .addChannelOption((ch) =>
                                ch.setName("channel").setDescription("Channel to remove").setRequired(true)
                            )
                    )
                    .addStringSetting(
                        new StringChoiceSetting(
                            "include-special",
                            "chatSummarySpecial",
                            'Include counting of "owo", ":3" and "meow"s',
                            [
                                {
                                    display: "Yes",
                                    value: "Yes"
                                },
                                {
                                    display: "No",
                                    value: "No"
                                }
                            ],
                            "No"
                        )
                    )
                    .addIntegerSetting(
                        new IntegerSetting("top-users", "chatSummaryTopUsers", "How many top users to show", 5, {
                            maximum: 10,
                            minimum: 0
                        })
                    )
            )
            .addSettingsGroup(
                new SettingsGroupBuilder("chatstreak").addSubcommand(
                    new SlashCommandSubcommandBuilder()
                        .setName("status-message")
                        .setDescription("Set whether or not to show a message when you achieve a streak")
                        .addBooleanOption((x) => x.setName("enabled").setDescription("Enabled").setRequired(true))
                )
            )
    ];
    settingsMaps = [];
    selfMemberId: string = "";

    async onSlashCommand(interaction: ChatInputCommandInteraction<CacheType>): Promise<void> {
        if (interaction.commandName !== "settings") return;
        if (!interaction.guild) return;
        if (!interaction.member) return;
        if (!interaction.options) return;

        const member = interaction.member as GuildMember;
        if (
            !member.permissions.has(PermissionsBitField.Flags.ManageGuild) &&
            !member.permissions.has(PermissionsBitField.Flags.Administrator)
        ) {
            await interaction.reply({
                content: "You do not have permissions",
                ephemeral: true
            });
            return;
        }

        const subcommandGroup = interaction.options.getSubcommandGroup();
        if (!subcommandGroup) return;
        const subcommand = interaction.options.getSubcommand(false);
        if (!subcommand) return;
        const commandBuilder = this.commands[0] as SettingsCommandBuilder;
        const command = commandBuilder.findSettingGroup(subcommandGroup, subcommand);
        if (!command) return;
        const settingsKey = command.settingsKey;
        const settingType = command.getType();
        const settingDesc = command.description;

        switch (settingType) {
            case "channel": {
                const newValue = interaction.options.getChannel("newvalue");
                if (newValue === null || newValue === undefined) {
                    const current = getSetting(interaction.guild.id, settingsKey);
                    const currentChannel = interaction.guild.channels.cache.get(current);
                    await interaction.reply({
                        content: `\`${settingDesc}\` is currently set to \`${currentChannel?.name ?? current}\``,
                        ephemeral: true
                    });
                    console.log("current", current);
                    break;
                }
                console.log("setChannel", subcommandGroup, subcommand);
                console.log("setChannel", settingsKey, newValue.name);
                setChannel(subcommandGroup, settingsKey, interaction, this.selfMemberId);
                break;
            }
            case "string": {
                const value = interaction.options.getString("newvalue");
                if (value === null || value === undefined) {
                    await interaction.reply({
                        content: `\`${settingDesc}\` is currently set to \`${getSetting(
                            interaction.guild.id,
                            settingsKey
                        )}\``,
                        ephemeral: true
                    });
                    break;
                }
                setSetting(interaction.guild.id, settingsKey, value);
                await interaction.reply({
                    content: `Set \`${settingDesc}\` to \`${value}\``,
                    ephemeral: true
                });
                break;
            }
            case "toggle": {
                const value = interaction.options.getBoolean("newvalue");
                if (value === null || value === undefined) {
                    const current = getSetting(interaction.guild.id, settingsKey);
                    await interaction.reply({
                        content: `\`${settingDesc}\` is currently set to \`${current}\``,
                        ephemeral: true
                    });
                    break;
                }
                setSetting(interaction.guild.id, settingsKey, value ? "yes" : "no");
                await interaction.reply({
                    content: `Set \`${settingDesc}\` to \`${value ? "yes" : "no"}\``,
                    ephemeral: true
                });
                break;
            }
            case "integer": {
                const value = interaction.options.getInteger("newvalue");
                if (value === null || value === undefined) {
                    const current = getSetting(interaction.guild.id, settingsKey);
                    await interaction.reply({
                        content: `\`${settingDesc}\` is currently set to \`${current}\``,
                        ephemeral: true
                    });
                    break;
                }

                const option = command as IntegerSetting;
                if (option.integerSettingOptions.maximum && value >= option.integerSettingOptions.maximum) {
                    await interaction.reply({
                        content: `The maximum value is ${option.integerSettingOptions.maximum}`,
                        ephemeral: true
                    });
                    return;
                }

                if (option.integerSettingOptions.minimum && value <= option.integerSettingOptions.minimum) {
                    await interaction.reply({
                        content: `The minimum value is ${option.integerSettingOptions.minimum}`,
                        ephemeral: true
                    });
                    return;
                }

                switch (option.integerSettingOptions.mode) {
                    case "only negative": {
                        if (value > 0) {
                            await interaction.reply({
                                content: "Only negative values are allowed",
                                ephemeral: true
                            });
                            return;
                        }
                        break;
                    }
                    case "only positive": {
                        if (value < 0) {
                            await interaction.reply({
                                content: "Only positive values are allowed",
                                ephemeral: true
                            });
                            return;
                        }
                        break;
                    }
                    case "only zero": {
                        if (value !== 0) {
                            await interaction.reply({
                                content: "Only zero is allowed",
                                ephemeral: true
                            });
                            return;
                        }
                        break;
                    }
                }

                setSetting(interaction.guild.id, settingsKey, value.toString());
                await interaction.reply({
                    content: `Set \`${settingDesc}\` to \`${value}\``,
                    ephemeral: true
                });
                break;
            }
        }
    }

    async onButtonClick(interaction: ButtonInteraction<CacheType>): Promise<void> {}

    async onRoleCreate(role: Role): Promise<void> {}

    async onRoleEdit(before: Role, after: Role): Promise<void> {}

    async onRoleDelete(role: Role): Promise<void> {}

    async onChannelCreate(role: Channel): Promise<void> {}

    async onChannelEdit(before: Channel, after: Channel): Promise<void> {}

    async onChannelDelete(role: Channel): Promise<void> {}

    async onMessage(msg: Message<boolean>): Promise<void> {}

    async onMessageDelete(msg: Message<boolean>): Promise<void> {}

    async onMessageEdit(before: Message<boolean>, after: Message<boolean>): Promise<void> {}

    async onMemberJoin(member: GuildMember): Promise<void> {}

    async onMemberEdit(before: GuildMember, after: GuildMember): Promise<void> {}

    async onMemberLeave(member: GuildMember): Promise<void> {}

    async onGuildAdd(guild: Guild): Promise<void> {}

    async onGuildRemove(guild: Guild): Promise<void> {}

    async onGuildEdit(before: Guild, after: Guild): Promise<void> {}

    async onEmojiCreate(emoji: Emoji): Promise<void> {}

    async onEmojiDelete(emoji: Emoji): Promise<void> {}

    async onEmojiEdit(before: Emoji, after: Emoji): Promise<void> {}

    async onStickerCreate(sticker: Sticker): Promise<void> {}

    async onStickerDelete(sticker: Sticker): Promise<void> {}

    async onStickerEdit(before: Sticker, after: Sticker): Promise<void> {}

    async onReady(client: Client): Promise<void> {}
}
