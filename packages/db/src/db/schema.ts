import {
  pgTable,
  index,
  foreignKey,
  varchar,
  integer,
  timestamp,
  json,
  date,
  doublePrecision,
  primaryKey,
  boolean,
} from "drizzle-orm/pg-core";

export const matches = pgTable(
  "matches",
  {
    key: varchar().primaryKey().notNull(),
    eventKey: varchar("event_key").notNull(),
    compLevel: varchar("comp_level").notNull(),
    setNumber: integer("set_number").notNull(),
    matchNumber: integer("match_number").notNull(),
    winningAlliance: varchar("winning_alliance").notNull(),
    time: timestamp({ withTimezone: true, mode: "string" }),
    actualTime: timestamp("actual_time", {
      withTimezone: true,
      mode: "string",
    }),
    predictedTime: timestamp("predicted_time", {
      withTimezone: true,
      mode: "string",
    }),
    postResultTime: timestamp("post_result_time", {
      withTimezone: true,
      mode: "string",
    }),
  },
  (table) => [
    index("ix_matches_comp_level").using(
      "btree",
      table.compLevel.asc().nullsLast().op("text_ops"),
    ),
    index("ix_matches_event_key").using(
      "btree",
      table.eventKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.eventKey],
      foreignColumns: [events.key],
      name: "matches_event_key_fkey",
    }),
  ],
);

export const rankingEventInfos = pgTable(
  "ranking_event_infos",
  {
    eventKey: varchar("event_key").primaryKey().notNull(),
    extraStatsInfo: json("extra_stats_info"),
    sortOrderInfo: json("sort_order_info"),
  },
  (table) => [
    foreignKey({
      columns: [table.eventKey],
      foreignColumns: [events.key],
      name: "ranking_event_infos_event_key_fkey",
    }),
  ],
);

export const etags = pgTable("etags", {
  endpoint: varchar().primaryKey().notNull(),
  etag: varchar().notNull(),
});

export const eventDistricts = pgTable(
  "event_districts",
  {
    key: varchar().primaryKey().notNull(),
    year: integer().notNull(),
    abbreviation: varchar().notNull(),
    displayName: varchar("display_name").notNull(),
  },
  (table) => [
    index("ix_event_districts_year").using(
      "btree",
      table.year.asc().nullsLast().op("int4_ops"),
    ),
  ],
);

export const events = pgTable(
  "events",
  {
    key: varchar().primaryKey().notNull(),
    districtKey: varchar("district_key"),
    parentEventKey: varchar("parent_event_key"),
    name: varchar().notNull(),
    eventCode: varchar("event_code").notNull(),
    eventType: integer("event_type").notNull(),
    eventTypeString: varchar("event_type_string").notNull(),
    year: integer().notNull(),
    startDate: date("start_date").notNull(),
    endDate: date("end_date").notNull(),
    week: integer(),
    shortName: varchar("short_name"),
    city: varchar(),
    stateProv: varchar("state_prov"),
    country: varchar(),
    postalCode: varchar("postal_code"),
    address: varchar(),
    locationName: varchar("location_name"),
    timezone: varchar(),
    lat: doublePrecision(),
    lng: doublePrecision(),
    website: varchar(),
    gmapsPlaceId: varchar("gmaps_place_id"),
    gmapsUrl: varchar("gmaps_url"),
    firstEventId: varchar("first_event_id"),
    firstEventCode: varchar("first_event_code"),
    playoffType: integer("playoff_type"),
    playoffTypeString: varchar("playoff_type_string"),
    divisionKeys: varchar("division_keys").array(),
  },
  (table) => [
    index("ix_events_district_key").using(
      "btree",
      table.districtKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_events_event_code").using(
      "btree",
      table.eventCode.asc().nullsLast().op("text_ops"),
    ),
    index("ix_events_parent_event_key").using(
      "btree",
      table.parentEventKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_events_year").using(
      "btree",
      table.year.asc().nullsLast().op("int4_ops"),
    ),
    foreignKey({
      columns: [table.districtKey],
      foreignColumns: [eventDistricts.key],
      name: "events_district_key_fkey",
    }),
    foreignKey({
      columns: [table.parentEventKey],
      foreignColumns: [table.key],
      name: "events_parent_event_key_fkey",
    }),
  ],
);

export const teams = pgTable(
  "teams",
  {
    key: varchar().primaryKey().notNull(),
    teamNumber: integer("team_number").notNull(),
    nickname: varchar().notNull(),
    name: varchar().notNull(),
    schoolName: varchar("school_name"),
    city: varchar(),
    stateProv: varchar("state_prov"),
    country: varchar(),
    postalCode: varchar("postal_code"),
    website: varchar(),
    rookieYear: integer("rookie_year"),
  },
  (table) => [
    index("ix_teams_rookie_year").using(
      "btree",
      table.rookieYear.asc().nullsLast().op("int4_ops"),
    ),
    index("ix_teams_team_number").using(
      "btree",
      table.teamNumber.asc().nullsLast().op("int4_ops"),
    ),
  ],
);

export const eventTeams = pgTable(
  "event_teams",
  {
    eventKey: varchar("event_key").notNull(),
    teamKey: varchar("team_key").notNull(),
  },
  (table) => [
    index("ix_event_teams_event_key").using(
      "btree",
      table.eventKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_event_teams_team_key").using(
      "btree",
      table.teamKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.eventKey],
      foreignColumns: [events.key],
      name: "event_teams_event_key_fkey",
    }),
    foreignKey({
      columns: [table.teamKey],
      foreignColumns: [teams.key],
      name: "event_teams_team_key_fkey",
    }),
    primaryKey({
      columns: [table.eventKey, table.teamKey],
      name: "event_teams_pkey",
    }),
  ],
);

export const matchAlliances = pgTable(
  "match_alliances",
  {
    matchKey: varchar("match_key").notNull(),
    allianceColor: varchar("alliance_color").notNull(),
    score: integer().notNull(),
    scoreBreakdown: json("score_breakdown"),
  },
  (table) => [
    index("ix_match_alliances_match_key").using(
      "btree",
      table.matchKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.matchKey],
      foreignColumns: [matches.key],
      name: "match_alliances_match_key_fkey",
    }),
    primaryKey({
      columns: [table.matchKey, table.allianceColor],
      name: "match_alliances_pkey",
    }),
  ],
);

export const allianceTeams = pgTable(
  "alliance_teams",
  {
    eventKey: varchar("event_key").notNull(),
    allianceName: varchar("alliance_name").notNull(),
    teamKey: varchar("team_key").notNull(),
    pickOrder: integer("pick_order").notNull(),
  },
  (table) => [
    index("ix_alliance_teams_event_key").using(
      "btree",
      table.eventKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_alliance_teams_team_key").using(
      "btree",
      table.teamKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.eventKey, table.allianceName],
      foreignColumns: [alliances.eventKey, alliances.name],
      name: "alliance_teams_event_key_alliance_name_fkey",
    }),
    foreignKey({
      columns: [table.eventKey, table.teamKey],
      foreignColumns: [eventTeams.eventKey, eventTeams.teamKey],
      name: "alliance_teams_event_key_team_key_fkey",
    }),
    primaryKey({
      columns: [table.eventKey, table.allianceName, table.teamKey],
      name: "alliance_teams_pkey",
    }),
  ],
);

export const matchAllianceTeams = pgTable(
  "match_alliance_teams",
  {
    matchKey: varchar("match_key").notNull(),
    allianceColor: varchar("alliance_color").notNull(),
    teamKey: varchar("team_key").notNull(),
    eventKey: varchar("event_key").notNull(),
    isSurrogate: boolean("is_surrogate").notNull(),
    isDq: boolean("is_dq").notNull(),
  },
  (table) => [
    index("ix_match_alliance_teams_event_key").using(
      "btree",
      table.eventKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_match_alliance_teams_match_key").using(
      "btree",
      table.matchKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_match_alliance_teams_team_key").using(
      "btree",
      table.teamKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.matchKey, table.allianceColor],
      foreignColumns: [matchAlliances.allianceColor, matchAlliances.matchKey],
      name: "match_alliance_teams_match_key_alliance_color_fkey",
    }),
    foreignKey({
      columns: [table.teamKey, table.eventKey],
      foreignColumns: [eventTeams.eventKey, eventTeams.teamKey],
      name: "match_alliance_teams_event_key_team_key_fkey",
    }),
    foreignKey({
      columns: [table.matchKey],
      foreignColumns: [matches.key],
      name: "match_alliance_teams_match_key_fkey",
    }),
    primaryKey({
      columns: [table.matchKey, table.allianceColor, table.teamKey],
      name: "match_alliance_teams_pkey",
    }),
  ],
);

export const rankings = pgTable(
  "rankings",
  {
    eventKey: varchar("event_key").notNull(),
    teamKey: varchar("team_key").notNull(),
    rank: integer().notNull(),
    matchesPlayed: integer("matches_played").notNull(),
    wins: integer().notNull(),
    losses: integer().notNull(),
    ties: integer().notNull(),
    dq: integer().notNull(),
    qualAverage: doublePrecision("qual_average"),
    extraStats: json("extra_stats"),
    sortOrders: json("sort_orders"),
  },
  (table) => [
    index("ix_rankings_event_key").using(
      "btree",
      table.eventKey.asc().nullsLast().op("text_ops"),
    ),
    index("ix_rankings_team_key").using(
      "btree",
      table.teamKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.eventKey, table.teamKey],
      foreignColumns: [eventTeams.eventKey, eventTeams.teamKey],
      name: "rankings_event_key_team_key_fkey",
    }),
    foreignKey({
      columns: [table.eventKey],
      foreignColumns: [events.key],
      name: "rankings_event_key_fkey",
    }),
    foreignKey({
      columns: [table.teamKey],
      foreignColumns: [teams.key],
      name: "rankings_team_key_fkey",
    }),
    primaryKey({
      columns: [table.eventKey, table.teamKey],
      name: "rankings_pkey",
    }),
  ],
);

export const alliances = pgTable(
  "alliances",
  {
    eventKey: varchar("event_key").notNull(),
    name: varchar().notNull(),
    backupIn: varchar("backup_in"),
    backupOut: varchar("backup_out"),
    status: varchar(),
    level: varchar(),
    wins: integer(),
    losses: integer(),
    ties: integer(),
    currentLevelWins: integer("current_level_wins"),
    currentLevelLosses: integer("current_level_losses"),
    currentLevelTies: integer("current_level_ties"),
    playoffType: integer("playoff_type"),
    playoffAverage: doublePrecision("playoff_average"),
    doubleElimRound: varchar("double_elim_round"),
    roundRobinRank: integer("round_robin_rank"),
    advancedToRoundRobinFinals: boolean("advanced_to_round_robin_finals"),
  },
  (table) => [
    index("ix_alliances_backup_in").using(
      "btree",
      table.backupIn.asc().nullsLast().op("text_ops"),
    ),
    index("ix_alliances_backup_out").using(
      "btree",
      table.backupOut.asc().nullsLast().op("text_ops"),
    ),
    index("ix_alliances_event_key").using(
      "btree",
      table.eventKey.asc().nullsLast().op("text_ops"),
    ),
    foreignKey({
      columns: [table.eventKey],
      foreignColumns: [events.key],
      name: "alliances_event_key_fkey",
    }),
    foreignKey({
      columns: [table.backupIn],
      foreignColumns: [teams.key],
      name: "alliances_backup_in_fkey",
    }),
    foreignKey({
      columns: [table.backupOut],
      foreignColumns: [teams.key],
      name: "alliances_backup_out_fkey",
    }),
    primaryKey({
      columns: [table.eventKey, table.name],
      name: "alliances_pkey",
    }),
  ],
);

export * from "./relations";
