import type { ChatSportContext } from "@/types/api";
import {
  buildAuditToolCall,
  logChatAudit,
  type ChatAuditToolCall,
} from "@/server/chat/audit";

import { getLeagueStandings, getLeagueTable, listLeagues } from "./leagues";
import { getMatchDetails } from "./matches";
import {
  getPlayerStatSummary,
  getTeamPlayerStatLeader,
} from "./players";
import {
  getMatchupProjection,
  getTeamOverview,
  getTeamProfile,
  getTeamStatSeries,
  searchTeams,
} from "./teams";
import type { ChatToolName, PlannedToolCall, ToolResult } from "./types";
import { MAX_TOOL_CALLS } from "./types";

// opisy narzędzi: tools/catalog.ts (jedno źródło dla Cursor + OpenRouter)

const TOOL_RUNNERS: Record<
  ChatToolName,
  (args: Record<string, unknown>) => Promise<ToolResult>
> = {
  list_leagues: listLeagues,
  search_teams: searchTeams,
  get_team_profile: getTeamProfile,
  get_team_overview: getTeamOverview,
  get_team_stat_series: getTeamStatSeries,
  get_team_player_stat_leader: getTeamPlayerStatLeader,
  get_player_stat_summary: getPlayerStatSummary,
  get_matchup_projection: getMatchupProjection,
  get_match_details: getMatchDetails,
  get_league_table: getLeagueTable,
  get_league_standings: getLeagueStandings,
};

export interface RunPlannedToolsOptions {
  provider?: string;
  questionPreview?: string;
}

export async function runPlannedTools(
  plannedCalls: PlannedToolCall[],
  sport: ChatSportContext,
  options?: RunPlannedToolsOptions,
): Promise<ToolResult[]> {
  const results: ToolResult[] = [];
  const auditCalls: ChatAuditToolCall[] = [];
  const startedAt = Date.now();

  for (const call of plannedCalls.slice(0, MAX_TOOL_CALLS)) {
    const runner = TOOL_RUNNERS[call.tool];
    const callStarted = Date.now();
    const args = {
      ...(call.args ?? {}),
      sport_id: sport.sport_id,
    };

    if (!runner) {
      results.push({
        name: call.tool,
        summary: `Narzędzie ${call.tool} nie jest dozwolone.`,
        data: null,
        dataSources: [],
        warnings: [`Pominięto niedozwolone narzędzie: ${call.tool}.`],
      });
      auditCalls.push(
        buildAuditToolCall({
          tool: call.tool,
          args,
          durationMs: Date.now() - callStarted,
          ok: false,
          warningCount: 1,
        }),
      );
      continue;
    }

    try {
      const result = await runner(args);
      results.push(result);
      auditCalls.push(
        buildAuditToolCall({
          tool: call.tool,
          args,
          durationMs: Date.now() - callStarted,
          ok: true,
          warningCount: result.warnings.length,
        }),
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unknown tool execution error.";
      results.push({
        name: call.tool,
        summary: `Narzędzie ${call.tool} nie zwróciło danych.`,
        data: null,
        dataSources: [],
        warnings: [message],
      });
      auditCalls.push(
        buildAuditToolCall({
          tool: call.tool,
          args,
          durationMs: Date.now() - callStarted,
          ok: false,
          warningCount: 1,
        }),
      );
    }
  }

  logChatAudit({
    event: "chat.tools",
    provider: options?.provider,
    sportId: sport.sport_id,
    questionPreview: options?.questionPreview,
    toolCalls: auditCalls,
    totalDurationMs: Date.now() - startedAt,
  });

  return results;
}
