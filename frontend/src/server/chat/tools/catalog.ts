import type { ChatToolName } from "./types";

/** Single source of truth for chat tool names, descriptions, and arg schemas. */

export interface ToolArgDefinition {
  type: "string" | "number" | "boolean";
  /** Human-readable arg hint used in Cursor prompts and OpenRouter schemas. */
  description: string;
  required?: boolean;
  enum?: readonly string[];
  minimum?: number;
  maximum?: number;
}

export interface ToolDefinition {
  description: string;
  args: Record<string, ToolArgDefinition>;
}

interface JsonSchemaProperty {
  type: string | string[];
  description?: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
}

interface ToolJsonSchema {
  type: "object";
  properties: Record<string, JsonSchemaProperty>;
  required?: string[];
  additionalProperties: false;
}

export interface OpenRouterToolDefinition {
  type: "function";
  function: {
    name: ChatToolName;
    description: string;
    parameters: ToolJsonSchema;
  };
}

export interface ChatToolDescription {
  tool: ChatToolName;
  description: string;
  args: Record<string, string>;
}

const TEAM_STAT_ENUM = [
  "goals",
  "total_goals",
  "shots",
  "shots_on_target",
  "corners",
  "cards",
  "offsides",
  "fouls",
  "penalty_minutes",
  "penalties",
] as const;

const MATCHUP_TARGET_ENUM = ["result", ...TEAM_STAT_ENUM] as const;

const PLAYER_LEADER_STAT_ENUM = [
  "goals",
  "assists",
  "shots",
  "shots_on_target",
  "fouls_conceded",
  "yellow_cards",
] as const;

const STANDINGS_SCOPE_ENUM = ["overall", "home", "away", "ou_btts"] as const;

/**
 * Canonical tool catalog. Add new tools here only — Cursor prompts and
 * OpenRouter schemas are derived below.
 */
export const CHAT_TOOL_CATALOG = {
  list_leagues: {
    description:
      "Lists leagues, optionally filtered by active status and sport_id.",
    args: {
      active: {
        type: "boolean",
        description: "Filter by active leagues",
      },
      sport_id: {
        type: "number",
        description: "Sport id from GUI context, e.g. 1 football, 2 hockey, 3 basketball",
      },
    },
  },
  search_teams: {
    description:
      "Searches teams by natural team name, country, sport, or shortcut.",
    args: {
      query: {
        type: "string",
        description: "Team search phrase",
        required: true,
      },
      sport_id: {
        type: "number",
        description: "Sport id optional filter",
      },
      page_size: {
        type: "number",
        description: "Page size",
        minimum: 1,
        maximum: 10,
      },
    },
  },
  get_team_profile: {
    description: "Gets a team profile after team id is known.",
    args: {
      team_id: {
        type: "number",
        description: "Team id",
        required: true,
      },
      season_id: {
        type: "number",
        description: "Omit for latest/all played matches across seasons",
      },
      league_id: {
        type: "number",
        description: "Optional league filter",
      },
      limit: {
        type: "number",
        description: "Recent matches limit",
        minimum: 1,
        maximum: 20,
      },
    },
  },
  get_team_overview: {
    description:
      "Builds a team profile by team name or id, including recent form, split stats, and an optional chart chosen by the assistant.",
    args: {
      team_id: {
        type: "number",
        description: "Optional when query is provided",
      },
      query: {
        type: "string",
        description: "Team search phrase",
      },
      season_id: {
        type: "number",
        description: "Optional season id",
      },
      season_years: {
        type: "string",
        description: "e.g. 2024/2025",
      },
      league_id: {
        type: "number",
        description: "Optional league filter",
      },
      limit: {
        type: "number",
        description: "Recent matches limit",
        minimum: 1,
        maximum: 20,
      },
    },
  },
  get_team_stat_series: {
    description:
      "Builds chart-ready recent-match series for one team and one statistic.",
    args: {
      team_id: {
        type: "number",
        description: "Optional when query is provided",
      },
      query: {
        type: "string",
        description: "Team search phrase",
      },
      season_id: {
        type: "number",
        description: "Omit for latest/all played matches across seasons",
      },
      league_id: {
        type: "number",
        description: "Optional league filter",
      },
      stat: {
        type: "string",
        description: "Match statistic to plot",
        required: true,
        enum: TEAM_STAT_ENUM,
      },
      perspective: {
        type: "string",
        description: "Which side of the stat to use",
        enum: ["team", "opponent", "total"],
      },
      limit: {
        type: "number",
        description: "Recent matches limit",
        minimum: 1,
        maximum: 20,
      },
    },
  },
  get_team_player_stat_leader: {
    description:
      "Finds which football player on a team leads a selected stat across the team's recent matches.",
    args: {
      team_id: {
        type: "number",
        description: "Optional when query is provided",
      },
      query: {
        type: "string",
        description: "Team search phrase",
      },
      season_id: {
        type: "number",
        description: "Optional season id",
      },
      season_years: {
        type: "string",
        description: "e.g. 2024/2025",
      },
      stat: {
        type: "string",
        description: "Football player leader stat",
        required: true,
        enum: PLAYER_LEADER_STAT_ENUM,
      },
      limit: {
        type: "number",
        description: "Recent team matches",
        minimum: 1,
        maximum: 10,
      },
    },
  },
  get_player_stat_summary: {
    description:
      "Finds a player by name in the selected sport and returns supported match-log stat totals, averages, a table, and a chart.",
    args: {
      query: {
        type: "string",
        description: "Player search phrase, e.g. Connor McDavid",
        required: true,
      },
      season_id: {
        type: "number",
        description: "Optional season id",
      },
      season_years: {
        type: "string",
        description: "e.g. 2024/2025",
      },
      team_id: {
        type: "number",
        description: "Optional team filter",
      },
      sport_id: {
        type: "number",
        description: "Sport id from GUI context",
      },
      stat: {
        type: "string",
        description:
          "football: goals, assists, shots, shots_on_target, fouls_conceded, yellow_cards; hockey skater: points, goals, assists, sog, plus_minus, penalty_minutes, toi_minutes; hockey goalie: shots_against, shots_saved, saves_acc, toi_minutes",
        required: true,
      },
      limit: {
        type: "number",
        description:
          "Recent matches, max 200; use 200 for full-season player questions",
        minimum: 1,
        maximum: 200,
      },
    },
  },
  get_matchup_projection: {
    description:
      "Projects a hypothetical match between team A and team B using recent team statistics. Use for questions about predicted score, cards, corners, fouls, shots, or any supported match statistic.",
    args: {
      team_a_query: {
        type: "string",
        description: "Home/team A search phrase",
        required: true,
      },
      team_b_query: {
        type: "string",
        description: "Away/team B search phrase",
        required: true,
      },
      target: {
        type: "string",
        description: "Projected outcome or statistic",
        required: true,
        enum: MATCHUP_TARGET_ENUM,
      },
      season_id: {
        type: "number",
        description: "Optional season id",
      },
      season_years: {
        type: "string",
        description: "e.g. 2024/2025",
      },
      league_id: {
        type: "number",
        description: "Optional league filter",
      },
      limit: {
        type: "number",
        description: "Recent matches per team",
        minimum: 1,
        maximum: 20,
      },
    },
  },
  get_match_details: {
    description:
      "Gets match details by match id: teams, score, date, and summarized key info (odds/predictions as counts).",
    args: {
      match_id: {
        type: "number",
        description: "Match id",
        required: true,
      },
    },
  },
  get_league_standings: {
    description: "Gets league standings for one season by league_id and season_id.",
    args: {
      league_id: {
        type: "number",
        description: "League id",
        required: true,
      },
      season_id: {
        type: "number",
        description: "Season id",
        required: true,
      },
      scope: {
        type: "string",
        description: "Standings scope",
        enum: STANDINGS_SCOPE_ENUM,
      },
    },
  },
  get_league_table: {
    description:
      "Finds a league by name, resolves season years, and returns the league table.",
    args: {
      query: {
        type: "string",
        description: "League search phrase",
        required: true,
      },
      season_years: {
        type: "string",
        description: "e.g. 2024/2025",
        required: true,
      },
      scope: {
        type: "string",
        description: "Standings scope",
        enum: STANDINGS_SCOPE_ENUM,
      },
    },
  },
} as const satisfies Record<ChatToolName, ToolDefinition>;

/** Stable tool order for prompts and OpenRouter schemas. */
export const CHAT_TOOL_NAMES = [
  "list_leagues",
  "search_teams",
  "get_team_profile",
  "get_team_overview",
  "get_team_stat_series",
  "get_team_player_stat_leader",
  "get_player_stat_summary",
  "get_matchup_projection",
  "get_match_details",
  "get_league_table",
  "get_league_standings",
] as const satisfies readonly ChatToolName[];

export function isChatToolName(value: string): value is ChatToolName {
  return (CHAT_TOOL_NAMES as readonly string[]).includes(value);
}

function formatArgForPrompt(arg: ToolArgDefinition): string {
  const parts: string[] = [arg.type, arg.required ? "required" : "optional"];
  if (arg.enum && arg.enum.length > 0) {
    parts.push(`one of ${arg.enum.join(", ")}`);
  }
  if (arg.minimum !== undefined || arg.maximum !== undefined) {
    const min = arg.minimum ?? "…";
    const max = arg.maximum ?? "…";
    parts.push(`range ${min}-${max}`);
  }
  if (arg.description) {
    parts.push(arg.description);
  }
  return parts.join("; ");
}

function toOpenRouterProperty(arg: ToolArgDefinition): JsonSchemaProperty {
  const property: JsonSchemaProperty = {
    type: arg.type,
    description: arg.description,
  };
  if (arg.enum) {
    property.enum = [...arg.enum];
  }
  if (arg.minimum !== undefined) {
    property.minimum = arg.minimum;
  }
  if (arg.maximum !== undefined) {
    property.maximum = arg.maximum;
  }
  return property;
}

function buildChatToolDescriptions(): ChatToolDescription[] {
  return CHAT_TOOL_NAMES.map((tool) => {
    const definition = CHAT_TOOL_CATALOG[tool];
    const args: Record<string, string> = {};
    for (const [key, arg] of Object.entries(definition.args)) {
      args[key] = formatArgForPrompt(arg);
    }
    return {
      tool,
      description: definition.description,
      args,
    };
  });
}

function buildOpenRouterTools(): OpenRouterToolDefinition[] {
  return CHAT_TOOL_NAMES.map((tool) => {
    const definition = CHAT_TOOL_CATALOG[tool];
    const properties: Record<string, JsonSchemaProperty> = {};
    const required: string[] = [];

    for (const [key, arg] of Object.entries(definition.args)) {
      properties[key] = toOpenRouterProperty(arg);
      if (arg.required) {
        required.push(key);
      }
    }

    return {
      type: "function",
      function: {
        name: tool,
        description: definition.description,
        parameters: {
          type: "object",
          properties,
          ...(required.length > 0 ? { required } : {}),
          additionalProperties: false,
        },
      },
    };
  });
}

/** Cursor planner view — generated from CHAT_TOOL_CATALOG. */
export const CHAT_TOOL_DESCRIPTIONS = buildChatToolDescriptions();

/** OpenRouter function-calling schemas — generated from CHAT_TOOL_CATALOG. */
export const OPENROUTER_TOOLS = buildOpenRouterTools();
