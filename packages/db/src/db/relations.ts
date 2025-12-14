import { relations } from "drizzle-orm/relations";
import {
  events,
  matches,
  rankingEventInfos,
  eventDistricts,
  eventTeams,
  teams,
  matchAlliances,
  alliances,
  allianceTeams,
  matchAllianceTeams,
  rankings,
} from "./schema";

export const matchesRelations = relations(matches, ({ one, many }) => ({
  event: one(events, {
    fields: [matches.eventKey],
    references: [events.key],
  }),
  matchAlliances: many(matchAlliances),
  matchAllianceTeams: many(matchAllianceTeams),
}));

export const eventsRelations = relations(events, ({ one, many }) => ({
  matches: many(matches),
  rankingEventInfos: many(rankingEventInfos),
  eventDistrict: one(eventDistricts, {
    fields: [events.districtKey],
    references: [eventDistricts.key],
  }),
  event: one(events, {
    fields: [events.parentEventKey],
    references: [events.key],
    relationName: "events_parentEventKey_events_key",
  }),
  events: many(events, {
    relationName: "events_parentEventKey_events_key",
  }),
  eventTeams: many(eventTeams),
  rankings: many(rankings),
  alliances: many(alliances),
}));

export const rankingEventInfosRelations = relations(
  rankingEventInfos,
  ({ one }) => ({
    event: one(events, {
      fields: [rankingEventInfos.eventKey],
      references: [events.key],
    }),
  }),
);

export const eventDistrictsRelations = relations(
  eventDistricts,
  ({ many }) => ({
    events: many(events),
  }),
);

export const eventTeamsRelations = relations(eventTeams, ({ one, many }) => ({
  event: one(events, {
    fields: [eventTeams.eventKey],
    references: [events.key],
  }),
  team: one(teams, {
    fields: [eventTeams.teamKey],
    references: [teams.key],
  }),
  allianceTeams: many(allianceTeams),
  matchAllianceTeams: many(matchAllianceTeams),
  rankings: many(rankings),
}));

export const teamsRelations = relations(teams, ({ many }) => ({
  eventTeams: many(eventTeams),
  rankings: many(rankings),
  alliances_backupIn: many(alliances, {
    relationName: "alliances_backupIn_teams_key",
  }),
  alliances_backupOut: many(alliances, {
    relationName: "alliances_backupOut_teams_key",
  }),
}));

export const matchAlliancesRelations = relations(
  matchAlliances,
  ({ one, many }) => ({
    match: one(matches, {
      fields: [matchAlliances.matchKey],
      references: [matches.key],
    }),
    matchAllianceTeams: many(matchAllianceTeams),
  }),
);

export const allianceTeamsRelations = relations(allianceTeams, ({ one }) => ({
  alliance: one(alliances, {
    fields: [allianceTeams.eventKey],
    references: [alliances.eventKey],
  }),
  eventTeam: one(eventTeams, {
    fields: [allianceTeams.eventKey],
    references: [eventTeams.eventKey],
  }),
}));

export const alliancesRelations = relations(alliances, ({ one, many }) => ({
  allianceTeams: many(allianceTeams),
  event: one(events, {
    fields: [alliances.eventKey],
    references: [events.key],
  }),
  team_backupIn: one(teams, {
    fields: [alliances.backupIn],
    references: [teams.key],
    relationName: "alliances_backupIn_teams_key",
  }),
  team_backupOut: one(teams, {
    fields: [alliances.backupOut],
    references: [teams.key],
    relationName: "alliances_backupOut_teams_key",
  }),
}));

export const matchAllianceTeamsRelations = relations(
  matchAllianceTeams,
  ({ one }) => ({
    matchAlliance: one(matchAlliances, {
      fields: [matchAllianceTeams.matchKey],
      references: [matchAlliances.allianceColor],
    }),
    eventTeam: one(eventTeams, {
      fields: [matchAllianceTeams.teamKey],
      references: [eventTeams.eventKey],
    }),
    match: one(matches, {
      fields: [matchAllianceTeams.matchKey],
      references: [matches.key],
    }),
  }),
);

export const rankingsRelations = relations(rankings, ({ one }) => ({
  eventTeam: one(eventTeams, {
    fields: [rankings.eventKey],
    references: [eventTeams.eventKey],
  }),
  event: one(events, {
    fields: [rankings.eventKey],
    references: [events.key],
  }),
  team: one(teams, {
    fields: [rankings.teamKey],
    references: [teams.key],
  }),
}));
