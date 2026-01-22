"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { useSprintWebSocket, type SprintPhaseInfo } from "@/hooks";
import type {
  PaginatedResponse,
  Spec,
  SpecPlanningQuestion,
  SpecPlanningResponse,
  Sprint,
  SprintCreate,
  SprintItem,
  SprintItemCreate,
  SprintItemStatus,
  SprintStatus,
  SprintWithItems,
} from "@/types";
import { CheckCircle2, Flag, Loader2, Plus, Target, Wifi, WifiOff } from "lucide-react";

const STATUS_LABELS: Record<SprintStatus, string> = {
  planned: "Planned",
  active: "Active",
  completed: "Completed",
  failed: "Failed",
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
  if (status === "failed") return "destructive";
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

  const [planningPrompt, setPlanningPrompt] = useState("");
  const [planningQuestions, setPlanningQuestions] = useState<SpecPlanningQuestion[]>([]);
  const [planningAnswers, setPlanningAnswers] = useState<string[]>([]);
  const [planningSpecId, setPlanningSpecId] = useState<string | null>(null);
  const [planningStatus, setPlanningStatus] = useState<"idle" | "questions" | "answered">("idle");
  const [planningError, setPlanningError] = useState<string | null>(null);
  const [planningMetadata, setPlanningMetadata] = useState<
    SpecPlanningResponse["planning"]["metadata"] | null
  >(null);
  const [specPlanningMetadata, setSpecPlanningMetadata] = useState<
    SpecPlanningResponse["planning"]["metadata"] | null
  >(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isSavingAnswers, setIsSavingAnswers] = useState(false);

  const [draftSprint, setDraftSprint] = useState<SprintCreate>({
    spec_id: null,
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

  const planningReady = planningStatus === "answered";
  const planningAnswersComplete =
    planningQuestions.length > 0 &&
    planningAnswers.length === planningQuestions.length &&
    planningAnswers.every((answer) => answer.trim().length > 0);
  const planningTelemetryMetadata = planningMetadata ?? specPlanningMetadata;
  const planningTelemetrySourceLabel = planningMetadata
    ? "Current interview"
    : specPlanningMetadata
      ? "Sprint history"
      : null;

  // WebSocket subscription for real-time sprint updates
  const handleStatusChange = useCallback(
    (newStatus: SprintStatus) => {
      // Update sprint in list
      setSprints((prev) =>
        prev.map((sprint) =>
          sprint.id === selectedSprintId ? { ...sprint, status: newStatus } : sprint
        )
      );
      // Update selected sprint detail
      setSelectedSprint((prev) => (prev ? { ...prev, status: newStatus } : prev));
    },
    [selectedSprintId]
  );

  const handlePhaseChange = useCallback((phase: SprintPhaseInfo) => {
    console.log(`[Sprint] Phase update: ${phase.phase} - ${phase.status}`, phase.details);
  }, []);

  const {
    isConnected: wsConnected,
    currentPhase,
    currentStatus: wsStatus,
    events: wsEvents,
  } = useSprintWebSocket({
    sprintId: selectedSprintId,
    onStatusChange: handleStatusChange,
    onPhaseChange: handlePhaseChange,
    autoConnect: true,
  });

  const renderTelemetryPanel = (
    metadata: SpecPlanningResponse["planning"]["metadata"] | null,
    options: {
      prefix: "planning" | "sprint";
      emptyMessage: string;
      sourceLabel?: string | null;
    }
  ) => {
    const telemetryCandidates = metadata?.candidates ?? [];
    const telemetryJudge = metadata?.judge;
    const selectedProvider = metadata?.selected_candidate?.provider ?? null;
    const hasTelemetryData = Boolean(
      metadata &&
        (telemetryCandidates.length ||
          telemetryJudge ||
          metadata.selected_candidate ||
          metadata.provider ||
          metadata.model_name ||
          metadata.trace_id ||
          metadata.trace_url)
    );
    const hasAnyTraceUrl = Boolean(
      metadata?.trace_url ||
        telemetryJudge?.trace_url ||
        telemetryCandidates.some((candidate) => Boolean(candidate.trace_url))
    );
    const hasAnyTraceId = Boolean(
      metadata?.trace_id ||
        telemetryJudge?.trace_id ||
        telemetryCandidates.some((candidate) => Boolean(candidate.trace_id))
    );
    const baseId = `${options.prefix}-telemetry`;
    return (
      <div
        className="space-y-3 rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground"
        data-testid={baseId}
      >
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Telemetry</p>
          {options.sourceLabel && (
            <span className="text-[10px] uppercase text-muted-foreground">
              {options.sourceLabel}
            </span>
          )}
        </div>
        {!metadata && (
          <p className="text-xs" data-testid={`${baseId}-empty`}>
            {options.emptyMessage}
          </p>
        )}
        {metadata && !hasTelemetryData && (
          <p className="text-xs">Telemetry is pending for this interview.</p>
        )}
        {metadata && hasTelemetryData && (
          <>
            {metadata.mode && (
              <p className="text-xs text-muted-foreground">
                Mode: {metadata.mode.replace("_", " ")}
              </p>
            )}
            {metadata.selected_candidate ? (
              <p className="text-sm" data-testid={`${baseId}-selected`}>
                Judge selected{" "}
                <span className="font-medium text-foreground">
                  {metadata.selected_candidate.provider || "agent"}
                  {metadata.selected_candidate.model_name
                    ? ` (${metadata.selected_candidate.model_name})`
                    : ""}
                </span>
              </p>
            ) : metadata.provider || metadata.model_name ? (
              <p className="text-sm" data-testid={`${baseId}-model`}>
                Model{" "}
                <span className="font-medium text-foreground">
                  {metadata.provider || "agent"}
                  {metadata.model_name ? ` (${metadata.model_name})` : ""}
                </span>
              </p>
            ) : null}
            {metadata.trace_url ? (
              <a
                className="underline decoration-dashed underline-offset-2 hover:text-foreground"
                href={metadata.trace_url}
                rel="noreferrer"
                target="_blank"
                data-testid={`${baseId}-trace-link`}
                data-trace-id={metadata.trace_id || undefined}
              >
                Planning trace
              </a>
            ) : metadata.trace_id ? (
              <span data-testid={`${baseId}-trace`} data-trace-id={metadata.trace_id}>
                Trace: {metadata.trace_id}
              </span>
            ) : null}
            {telemetryJudge && (
              <div className="flex flex-wrap items-center gap-2">
                <span>
                  Judge {telemetryJudge.provider ? `${telemetryJudge.provider} ` : ""}
                  {telemetryJudge.model_name ? `(${telemetryJudge.model_name})` : ""}
                </span>
                {telemetryJudge.trace_url ? (
                  <a
                    className="underline decoration-dashed underline-offset-2 hover:text-foreground"
                    href={telemetryJudge.trace_url}
                    rel="noreferrer"
                    target="_blank"
                    data-testid={`${baseId}-judge-link`}
                    data-trace-id={telemetryJudge.trace_id || undefined}
                  >
                    Logfire
                  </a>
                ) : telemetryJudge.trace_id ? (
                  <span
                    data-testid={`${baseId}-judge-trace`}
                    data-trace-id={telemetryJudge.trace_id}
                  >
                    Trace: {telemetryJudge.trace_id}
                  </span>
                ) : null}
              </div>
            )}
            {telemetryCandidates.length ? (
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase text-muted-foreground">Subagents</p>
                {telemetryCandidates.map((candidate, index) => {
                  const candidateKey = candidate.provider || `agent-${index}`;
                  const isSelected = Boolean(
                    selectedProvider && candidate.provider === selectedProvider
                  );
                  return (
                    <div
                      key={`${candidateKey}-${index}`}
                      className="flex flex-wrap items-center gap-2"
                    >
                      <span>
                        {candidate.provider || "agent"}
                        {candidate.model_name ? ` (${candidate.model_name})` : ""}
                      </span>
                      {isSelected && <Badge variant="secondary">Selected</Badge>}
                      {candidate.trace_url ? (
                        <a
                          className="underline decoration-dashed underline-offset-2 hover:text-foreground"
                          href={candidate.trace_url}
                          rel="noreferrer"
                          target="_blank"
                          data-testid={`${baseId}-agent-${candidateKey}-link`}
                          data-trace-id={candidate.trace_id || undefined}
                        >
                          Logfire
                        </a>
                      ) : candidate.trace_id ? (
                        <span
                          data-testid={`${baseId}-agent-${candidateKey}-trace`}
                          data-trace-id={candidate.trace_id}
                        >
                          Trace: {candidate.trace_id}
                        </span>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : null}
          </>
        )}
        {metadata && hasAnyTraceId && !hasAnyTraceUrl && (
          <p className="text-[10px] text-muted-foreground">
            Add LOGFIRE_TRACE_URL_TEMPLATE in the backend .env to render clickable links.
          </p>
        )}
      </div>
    );
  };

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

  const extractPlanningMetadata = (spec: Spec | null) => {
    const artifacts = spec?.artifacts;
    if (!artifacts || typeof artifacts !== "object") return null;
    const planning = (
      artifacts as { planning?: { metadata?: SpecPlanningResponse["planning"]["metadata"] } }
    ).planning;
    return planning?.metadata ?? null;
  };

  const loadSpecPlanning = async (specId: string) => {
    try {
      const spec = await apiClient.get<Spec>(`/specs/${specId}`);
      setSpecPlanningMetadata(extractPlanningMetadata(spec));
    } catch (err) {
      setSpecPlanningMetadata(null);
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

  useEffect(() => {
    if (!selectedSprint?.spec_id) {
      setSpecPlanningMetadata(null);
      return;
    }
    loadSpecPlanning(selectedSprint.spec_id);
  }, [selectedSprint?.spec_id]);

  const handleCreateSprint = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError(null);

    if (!planningReady) {
      setCreateError("Complete the planning interview before creating a sprint.");
      return;
    }

    if (!draftSprint.name?.trim()) {
      setCreateError("Sprint name is required.");
      return;
    }

    setIsCreating(true);
    try {
      const payload: SprintCreate = {
        name: draftSprint.name.trim(),
        goal: draftSprint.goal?.trim() || undefined,
        spec_id: draftSprint.spec_id || undefined,
        status: draftSprint.status,
        start_date: draftSprint.start_date || undefined,
        end_date: draftSprint.end_date || undefined,
      };
      const created = await apiClient.post<SprintWithItems>("/sprints", payload);
      setDraftSprint({ spec_id: null, name: "", goal: "", status: "planned", start_date: "", end_date: "" });
      setSprints((prev) => [created, ...prev]);
      setSelectedSprintId(created.id);
      setPlanningPrompt("");
      setPlanningQuestions([]);
      setPlanningAnswers([]);
      setPlanningSpecId(null);
      setPlanningStatus("idle");
      setPlanningMetadata(null);
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

  const handleStartPlanning = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPlanningError(null);

    if (!planningPrompt.trim()) {
      setPlanningError("Provide a sprint prompt to start the interview.");
      return;
    }

    setIsPlanning(true);
    try {
      const data = await apiClient.post<SpecPlanningResponse>("/specs/planning", {
        task: planningPrompt.trim(),
      });
      setPlanningSpecId(data.spec.id);
      setPlanningQuestions(data.planning.questions || []);
      setPlanningMetadata(data.planning.metadata || null);
      setPlanningAnswers(new Array(data.planning.questions.length).fill(""));
      setPlanningStatus("questions");
      setDraftSprint((prev) => ({
        ...prev,
        goal: prev.goal?.trim() ? prev.goal : planningPrompt.trim(),
        spec_id: data.spec.id,
      }));
    } catch (err) {
      setPlanningError(err instanceof Error ? err.message : "Failed to start planning interview.");
    } finally {
      setIsPlanning(false);
    }
  };

  const handleSaveAnswers = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPlanningError(null);

    if (!planningSpecId) {
      setPlanningError("Start the planning interview first.");
      return;
    }

    if (!planningAnswersComplete) {
      setPlanningError("Answer every planning question before saving.");
      return;
    }

    setIsSavingAnswers(true);
    try {
      const answersPayload = planningQuestions.map((question, index) => ({
        question: question.question,
        answer: planningAnswers[index].trim(),
      }));
      const data = await apiClient.post<SpecPlanningResponse>(
        `/specs/${planningSpecId}/planning/answers`,
        { answers: answersPayload }
      );
      setPlanningStatus("answered");
      setPlanningQuestions(data.planning.questions || planningQuestions);
      setPlanningMetadata(data.planning.metadata || planningMetadata);
    } catch (err) {
      setPlanningError(err instanceof Error ? err.message : "Failed to save planning answers.");
    } finally {
      setIsSavingAnswers(false);
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
                <Target className="h-5 w-5" /> Sprint planning interview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <form className="space-y-4" onSubmit={handleStartPlanning}>
                <div className="space-y-2">
                  <Label htmlFor="planning-prompt">Sprint prompt</Label>
                  <textarea
                    id="planning-prompt"
                    className="min-h-[90px] w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm"
                    value={planningPrompt}
                    onChange={(event) => setPlanningPrompt(event.target.value)}
                    placeholder="Describe the sprint outcomes you want to achieve..."
                  />
                </div>
                <Button type="submit" disabled={isPlanning}>
                  {isPlanning ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> Starting interview
                    </span>
                  ) : (
                    "Start planning interview"
                  )}
                </Button>
              </form>

              {planningQuestions.length > 0 && (
                <form className="space-y-4" onSubmit={handleSaveAnswers}>
                  <div className="space-y-3">
                    <p className="text-xs font-medium uppercase text-muted-foreground">
                      Clarifying questions
                    </p>
                    {planningQuestions.map((question, index) => (
                      <div key={`${question.question}-${index}`} className="space-y-2">
                        <p className="text-sm font-medium">{question.question}</p>
                        {question.rationale && (
                          <p className="text-xs text-muted-foreground">{question.rationale}</p>
                        )}
                        <Input
                          id={`planning-answer-${index}`}
                          value={planningAnswers[index] || ""}
                          onChange={(event) =>
                            setPlanningAnswers((prev) => {
                              const next = [...prev];
                              next[index] = event.target.value;
                              return next;
                            })
                          }
                          placeholder="Your answer"
                        />
                      </div>
                    ))}
                  </div>
                  <Button type="submit" disabled={isSavingAnswers || !planningAnswersComplete}>
                    {isSavingAnswers ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" /> Saving answers
                      </span>
                    ) : (
                      "Save answers"
                    )}
                  </Button>
                </form>
              )}

              {renderTelemetryPanel(planningTelemetryMetadata, {
                prefix: "planning",
                emptyMessage: "Start the planning interview to capture model and Logfire telemetry.",
                sourceLabel: planningTelemetrySourceLabel,
              })}

              {planningStatus === "answered" && (
                <p className="text-sm text-muted-foreground">
                  Planning interview complete. You can create the sprint now.
                </p>
              )}

              {planningError && <p className="text-sm text-destructive">{planningError}</p>}
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
                {!planningReady && (
                  <p className="text-xs text-muted-foreground">
                    Complete the planning interview before creating this sprint.
                  </p>
                )}
                {createError && <p className="text-sm text-destructive">{createError}</p>}
                <Button type="submit" disabled={isCreating || !planningReady} className="w-full">
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
                    {/* WebSocket connection indicator */}
                    <span
                      className="flex items-center gap-1 text-xs"
                      title={wsConnected ? "Live updates active" : "Connecting..."}
                    >
                      {wsConnected ? (
                        <Wifi className="h-3 w-3 text-green-500" />
                      ) : (
                        <WifiOff className="h-3 w-3 text-muted-foreground" />
                      )}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {selectedSprint.goal || "No sprint goal set yet."}
                  </p>
                  {/* Real-time phase status */}
                  {currentPhase && selectedSprint.status === "active" && (
                    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        <span className="text-sm font-medium capitalize">
                          {currentPhase.phase}
                          {currentPhase.attempt ? ` (Attempt ${currentPhase.attempt})` : ""}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {currentPhase.status}
                        </Badge>
                      </div>
                      {currentPhase.details && (
                        <p className="mt-1 text-xs text-muted-foreground">{currentPhase.details}</p>
                      )}
                      {currentPhase.duration_ms && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Duration: {(currentPhase.duration_ms / 1000).toFixed(1)}s
                        </p>
                      )}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span>Start: {formatDate(selectedSprint.start_date)}</span>
                    <span>End: {formatDate(selectedSprint.end_date)}</span>
                    <span>{selectedSprint.items?.length || 0} items</span>
                  </div>
                  {renderTelemetryPanel(specPlanningMetadata, {
                    prefix: "sprint",
                    emptyMessage:
                      "No telemetry recorded for this sprint yet. Run the planning interview to capture it.",
                    sourceLabel: specPlanningMetadata ? "Sprint history" : null,
                  })}
                  {/* Recent WebSocket events for debugging */}
                  {wsEvents.length > 0 && (
                    <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        Live Events ({wsEvents.length})
                      </p>
                      <div className="max-h-32 space-y-1 overflow-y-auto">
                        {wsEvents.slice(-5).map((event, idx) => (
                          <div
                            key={`${event.type}-${idx}`}
                            className="text-xs text-muted-foreground"
                          >
                            <span className="font-mono">{event.type}</span>
                            {"phase" in event && event.phase && (
                              <span className="ml-1">({event.phase})</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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
