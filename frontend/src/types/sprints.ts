export type SprintStatus = "planned" | "active" | "completed";
export type SprintItemStatus = "todo" | "in_progress" | "blocked" | "done";

export interface Sprint {
  id: string;
  name: string;
  goal?: string | null;
  status: SprintStatus;
  start_date?: string | null;
  end_date?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface SprintItem {
  id: string;
  sprint_id: string;
  title: string;
  description?: string | null;
  status: SprintItemStatus;
  priority: number;
  estimate_points?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface SprintWithItems extends Sprint {
  items: SprintItem[];
}

export interface SprintCreate {
  name: string;
  goal?: string | null;
  status?: SprintStatus;
  start_date?: string | null;
  end_date?: string | null;
}

export interface SprintUpdate {
  name?: string;
  goal?: string | null;
  status?: SprintStatus;
  start_date?: string | null;
  end_date?: string | null;
}

export interface SprintItemCreate {
  title: string;
  description?: string | null;
  status?: SprintItemStatus;
  priority?: number;
  estimate_points?: number | null;
}

export interface SprintItemUpdate {
  title?: string;
  description?: string | null;
  status?: SprintItemStatus;
  priority?: number;
  estimate_points?: number | null;
}
