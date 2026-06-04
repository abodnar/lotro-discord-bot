# Command Reference

Use `/raid_commands` or `/raid_help` in Discord for a quick in-app overview.

---

## Scheduling

| Command | Example | Notes |
|---------|---------|-------|
| `/[raid]` `<tier>` `<time>` `[aim]` | `/rem t3 friday 8pm` | Schedule a specific raid. Tab-complete shows all available raids. |
| `/custom` `<name>` `<time>` `[tier]` `[aim]` | `/custom Turtle friday 8pm` | Schedule a custom event. |
| `/creep` `<time>` `[aim]` | `/creep saturday 2100` | Schedule an Ettenmoors event. |

Time accepts natural language (`tomorrow 8pm`, `friday 20:00`, `2026-06-10 2100`).

---

## Sign-up (on the raid post)

| Action | How |
|--------|-----|
| Sign up as a class | Click the class emoji button |
| Sign up with all previous classes | Click ✅ |
| Remove your sign up | Click ❌ |

Clicking a class you're already signed up with removes that class. If it's your only class, it removes your sign up entirely.

---

## Raid Leader Tools (on the raid post)

| Button | Action |
|--------|--------|
| ⚙️ | Edit raid name, tier, aim, or time; or delete the raid |
| ⛏️ | Open the roster picker — assign players to slots, set per-slot spec and role |

### Roster picker dropdowns (in order)

1. **Slot** — which slot to configure (or Automatic)
2. **Player** — who to assign
3. **Class** — which class they're filling
4. **Spec** — 🔴 Red / 🔵 Blue / 🟡 Yellow / combinations / All three
5. **Role** — 🛡️ Tank / 💚 Healer / ⚡ CC / ⚔️ DPS

Spec and Role are per-slot and persist when players are swapped.

---

## Calendar

| Command | Notes |
|---------|-------|
| `/calendar channel` | Creates a self-updating overview of upcoming raids in this channel. Run once; it updates automatically as raids are posted. |
| `/calendar discord` | Adds each raid as a Discord guild scheduled event. |
| `/list_raids` | Lists all upcoming raids for this server. |
| `/list_players` | Lists signed-up players in sign-up order (raid leaders only). |

---

## Personal Settings

| Command | Example | Notes |
|---------|---------|-------|
| `/specs` `<class>` | `/specs guardian` | Set your specialization for a class — choose from a visual selector showing all 7 spec combinations. |
| `/remove_roles` | | Clear all your class roles (resets the ✅ quick sign-up). |
| `/time_zones personal` `<timezone>` | `/time_zones personal Europe/London` | Set your personal timezone for interpreting raid commands. |

---

## Server Settings (Admin only)

| Command | Example | Notes |
|---------|---------|-------|
| `/leader` `<role>` | `/leader Officer` | Set the raid leader role. Leaders can edit any raid. |
| `/kin` `<role>` | `/kin Kinship` | Set the kin role. Kin members are marked on the sign-up sheet. |
| `/time_zones server` `<timezone>` | `/time_zones server America/New_York` | Set the default server timezone. |
| `/rss on/off` | `/rss on` | Post LotRO news announcements to this channel. |

---

## Info

| Command | Notes |
|---------|-------|
| `/raid_commands` or `/raid_help` | Shows all commands as clickable links (ephemeral). |
| `/about` | Bot info, version, uptime, invite link. |
| `/events` | Upcoming official LotRO in-game events. |
| `/server_time` | Current server time in the configured timezone. |
| `/loot` `<chest>` `[class]` `[level]` `[tracery]` | Loot table for any chest. Requires the LotRO data submodule. |
| `/privacy` | Data collection and retention policy. |
| `/welcome` | Resends the welcome and setup message. |
