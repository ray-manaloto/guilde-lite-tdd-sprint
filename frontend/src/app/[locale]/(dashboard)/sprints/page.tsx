"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import type {
  PaginatedResponse,
  Sprint,
  SprintCreate,
  SprintItem,
  SprintItemCreate,
  SprintItemStatus,
  SprintStatus,
  SprintWithItems,
} from "@/types";
import { CheckCircle2, Flag, Loader2, Plus, Target } from "lucide-react";

const STATUS_LABELS: Record<SprintStatus, string> = {
  planned: "Planned",
  active: "Active",
  completed: "Completed",
};

const ITEM_COLUMNS: Array<{ status: SprintItemStatus; label: string; hint: string }> = [
  { status: "todo", label: "Todo", hint: "Queued up for the sprint" },
  { status: "in_progress", label: "In progress", hint: "Currently being worked on" },
  { status: "blocked", label: "Blocked", hint: "Waiting on dependencies" },
  { status: "done", label: "Done", hint: "Completed deliverables" },
];

const statusBadgeVariant = (status: SprintStatus) => {
  if (status === "active") return "default";
  if (status === "completed") return "secondary";
  return "outline";
};

const itemBadgeVariant = (status: SprintItemStatus) => {
  if (status === "blocked") return "destructive";
  if (status === "done") return "secondary";
  if (status === "in_progress") return "default";
  return "outline";
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

export default function SprintsPage() {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [selectedSprintId, setSelectedSprintId] = useState<string | null>(null);
  const [selectedSprint, setSelectedSprint] = useState<SprintWithItems | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [itemError, setItemError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isCreatingItem, setIsCreatingItem] = useState(false);

  const [draftSprint, setDraftSprint] = useState<SprintCreate>({
    name: "",
    goal: "",
    status: "planned",
    start_date: "",
    end_date: "",
  });

  const [draftItem, setDraftItem] = useState<SprintItemCreate>({
    title: "",
    description: "",
    status: "todo",
    priority: 2,
    estimate_points: undefined,
  });

  const loadSprints = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<PaginatedResponse<Sprint>>("/sprints");
      const items = data.items || [];
      setSprints(items);
      const preferred = items.find((sprint) => sprint.status === "active") || items[0] || null;
      setSelectedSprintId((prev) => prev || preferred?.id || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sprints.");
    } finally {
      setLoading(false);
    }
  };

  const loadSprintDetail = async (sprintId: string) => {
    setDetailLoading(true);
    setItemError(null);
    try {
      const data = await apiClient.get<SprintWithItems>(`/sprints/${sprintId}`);
      setSelectedSprint(data);
    } catch (err) {
      setItemError(err instanceof Error ? err.message : "Failed to load sprint details.");
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    loadSprints();
  }, []);

  useEffect(() => {
    if (!selectedSprintId) {
      setSelectedSprint(null);
      return;
    }
    loadSprintDetail(selectedSprintId);
  }, [selectedSprintId]);

  const handleCreateSprint = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError(null);

    if (!draftSprint.name?.trim()) {
      setCreateError("Sprint name is required.");
      return;
    }

    setIsCreating(true);
    try {
      const payload: SprintCreate = {
        name: draftSprint.name.trim(),
        goal: draftSprint.goal?.trim() || undefined,
        status: draftSprint.status,
        start_date: draftSprint.start_date || undefined,
        end_date: draftSprint.end_date || undefined,
      };
      const created = await apiClient.post<SprintWithItems>("/sprints", payload);
      setDraftSprint({ name: "", goal: "", status: "planned", start_date: "", end_date: "" });
      setSprints((prev) => [created, ...prev]);
      setSelectedSprintId(created.id);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create sprint.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreateItem = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setItemError(null);

    if (!selectedSprintId) {
      setItemError("Select a sprint before adding items.");
      return;
    }

    if (!draftItem.title?.trim()) {
      setItemError("Item title is required.");
      return;
    }

    setIsCreatingItem(true);
    try {
      const payload: SprintItemCreate = {
        title: draftItem.title.trim(),
        description: draftItem.description?.trim() || undefined,
        status: draftItem.status ?? "todo",
        priority: draftItem.priority ?? 2,
        estimate_points: draftItem.estimate_points ?? undefined,
      };
      const created = await apiClient.post<SprintItem>(
        `/sprints/${selectedSprintId}/items`,
        payload
      );
      setDraftItem((prev) => ({
        ...prev,
        title: "",
        description: "",
        estimate_points: undefined,
      }));
      setSelectedSprint((prev) =>
        prev ? { ...prev, items: [created, ...(prev.items ?? [])] } : prev
      );
    } catch (err) {
      setItemError(err instanceof Error ? err.message : "Failed to create sprint item.");
    } finally {
      setIsCreatingItem(false);
    }
  };

  const itemsByStatus = useMemo(() => {
    const grouped: Record<SprintItemStatus, SprintItem[]> = {
      todo: [],
      in_progress: [],
      blocked: [],
      done: [],
    };
    if (!selectedSprint?.items) return grouped;
    for (const item of selectedSprint.items) {
      grouped[item.status]?.push(item);
    }
    return grouped;
  }, [selectedSprint]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Sprint Board</h1>
        <p className="text-muted-foreground text-sm sm:text-base">
          Plan focused delivery cycles and track execution before pushing to Kanban.
        </p>
      </div>

      {error && (
        <Card>
          <CardContent className="text-destructive pt-6">{error}</CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Flag className="h-5 w-5" /> Active Sprints
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading sprints
                </div>
              ) : sprints.length === 0 ? (
                <p className="text-sm text-muted-foreground">No sprints yet. Create one below.</p>
              ) : (
                sprints.map((sprint) => (
                  <button
                    key={sprint.id}
                    type="button"
                    onClick={() => setSelectedSprintId(sprint.id)}
                    className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                      sprint.id === selectedSprintId
                        ? "border-primary bg-primary/5"
                        : "hover:border-primary/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold">{sprint.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(sprint.start_date)} → {formatDate(sprint.end_date)}
                        </p>
                      </div>
                      <Badge variant={statusBadgeVariant(sprint.status)}>
                        {STATUS_LABELS[sprint.status]}
                      </Badge>
                    </div>
                    {sprint.goal && (
                      <p className="mt-2 text-xs text-muted-foreground line-clamp-2">{sprint.goal}</p>
                    )}
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Plus className="h-5 w-5" /> New Sprint
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleCreateSprint}>
                <div className="space-y-2">
                  <Label htmlFor="sprint-name">Sprint name</Label>
                  <Input
                    id="sprint-name"
                    value={draftSprint.name}
                    onChange={(event) =>
                      setDraftSprint((prev) => ({ ...prev, name: event.target.value }))
                    }
                    placeholder="Sprint 01 - Agent parity"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sprint-goal">Sprint goal</Label>
                  <textarea
                    id="sprint-goal"
                    className="min-h-[90px] w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm"
                    value={draftSprint.goal || ""}
                    onChange={(event) =>
                      setDraftSprint((prev) => ({ ...prev, goal: event.target.value }))
                    }
                    placeholder="Focus on sprint board + agent workflows"
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="sprint-start">Start date</Label>
                    <Input
                      id="sprint-start"
                      type="date"
                      value={draftSprint.start_date || ""}
                      onChange={(event) =>
                        setDraftSprint((prev) => ({ ...prev, start_date: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sprint-end">End date</Label>
                    <Input
                      id="sprint-end"
                      type="date"
                      value={draftSprint.end_date || ""}
                      onChange={(event) =>
                        setDraftSprint((prev) => ({ ...prev, end_date: event.target.value }))
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sprint-status">Status</Label>
                  <select
                    id="sprint-status"
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                    value={draftSprint.status}
                    onChange={(event) =>
                      setDraftSprint((prev) => ({
                        ...prev,
                        status: event.target.value as SprintStatus,
                      }))
                    }
                  >
                    {Object.entries(STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                {createError && <p className="text-sm text-destructive">{createError}</p>}
                <Button type="submit" disabled={isCreating} className="w-full">
                  {isCreating ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> Creating
                    </span>
                  ) : (
                    "Create sprint"
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Target className="h-5 w-5" /> Sprint Focus
              </CardTitle>
            </CardHeader>
            <CardContent>
              {detailLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading sprint details
                </div>
              ) : selectedSprint ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold">{selectedSprint.name}</h2>
                    <Badge variant={statusBadgeVariant(selectedSprint.status)}>
                      {STATUS_LABELS[selectedSprint.status]}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {selectedSprint.goal || "No sprint goal set yet."}
                  </p>
                  <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span>Start: {formatDate(selectedSprint.start_date)}</span>
                    <span>End: {formatDate(selectedSprint.end_date)}</span>
                    <span>{selectedSprint.items?.length || 0} items</span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Select a sprint to see the backlog and status breakdown.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Plus className="h-5 w-5" /> Add Sprint Item
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleCreateItem}>
                <div className="space-y-2">
                  <Label htmlFor="item-title">Title</Label>
                  <Input
                    id="item-title"
                    value={draftItem.title}
                    onChange={(event) =>
                      setDraftItem((prev) => ({ ...prev, title: event.target.value }))
                    }
                    placeholder="Implement sprint dashboard"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="item-description">Description</Label>
                  <textarea
                    id="item-description"
                    className="min-h-[80px] w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm"
                    value={draftItem.description || ""}
                    onChange={(event) =>
                      setDraftItem((prev) => ({ ...prev, description: event.target.value }))
                    }
                    placeholder="Add filters, status badges, and summary metrics"
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="item-status">Status</Label>
                    <select
                      id="item-status"
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      value={draftItem.status}
                      onChange={(event) =>
                        setDraftItem((prev) => ({
                          ...prev,
                          status: event.target.value as SprintItemStatus,
                        }))
                      }
                    >
                      {ITEM_COLUMNS.map((column) => (
                        <option key={column.status} value={column.status}>
                          {column.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="item-priority">Priority</Label>
                    <select
                      id="item-priority"
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      value={draftItem.priority ?? 2}
                      onChange={(event) =>
                        setDraftItem((prev) => ({
                          ...prev,
                          priority: Number(event.target.value),
                        }))
                      }
                    >
                      <option value={1}>High</option>
                      <option value={2}>Medium</option>
                      <option value={3}>Low</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="item-points">Points</Label>
                    <Input
                      id="item-points"
                      type="number"
                      min={0}
                      value={draftItem.estimate_points ?? ""}
                      onChange={(event) => {
                        const value = event.target.value;
                        setDraftItem((prev) => ({
                          ...prev,
                          estimate_points: value === "" ? undefined : Number(value),
                        }));
                      }}
                      placeholder="3"
                    />
                  </div>
                </div>
                {itemError && <p className="text-sm text-destructive">{itemError}</p>}
                <Button type="submit" disabled={isCreatingItem || !selectedSprintId}>
                  {isCreatingItem ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> Adding
                    </span>
                  ) : (
                    "Add item"
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {ITEM_COLUMNS.map((column) => (
              <Card key={column.status}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center justify-between text-sm font-semibold">
                    <span>{column.label}</span>
                    <Badge variant={itemBadgeVariant(column.status)}>
                      {itemsByStatus[column.status].length}
                    </Badge>
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">{column.hint}</p>
                </CardHeader>
                <CardContent className="space-y-3">
                  {itemsByStatus[column.status].length === 0 ? (
                    <p className="text-xs text-muted-foreground">No items yet.</p>
                  ) : (
                    itemsByStatus[column.status].map((item) => (
                      <div key={item.id} className="rounded-lg border p-3">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                          <p className="text-sm font-medium">{item.title}</p>
                        </div>
                        {item.description && (
                          <p className="mt-2 text-xs text-muted-foreground line-clamp-3">
                            {item.description}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>Priority {item.priority}</span>
                          {item.estimate_points !== null && item.estimate_points !== undefined && (
                            <span>{item.estimate_points} pts</span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
