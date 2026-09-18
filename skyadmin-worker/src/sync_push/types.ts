import { SyncTableName } from "../sync_schema";

export type PushChange = {
  table?: string;
  global_id?: string;
  row?: Record<string, unknown>;
  updated_at?: string;
  deleted_at?: string | null;
  hlc?: string;
  proto?: number;
};

export type PreparedPushChange = {
  table: SyncTableName;
  globalId: string;
  updatedAt: string;
  deletedAt: string | null;
  rowJson: string;
  hlc: string | null;
};

export type ExistingSyncRow = {
  updatedAt: string;
  hlc: string | null;
};

export type ParsedHlc = {
  wall: number;
  counter: number;
  node: string;
};

export type PushPartition = {
  apply: PreparedPushChange[];
  conflicts: PreparedPushChange[];
  skipped: number;
};
