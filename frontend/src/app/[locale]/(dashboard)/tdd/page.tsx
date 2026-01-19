"use client";

import { useMemo, useState, type FormEvent } from "react";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import type {
  AgentCandidate,
  AgentTddRunCreate,
  AgentTddRunResult,
  TddProvider,
} from "@/types";
import { Loader2 } from "lucide-react";

const PROVIDER_OPTIONS: Array<{
  id: TddProvider;
  label: string;
  description: string;
}> = [
  {
    id: "openai",
    label: "OpenAI",
    description: "Great general reasoning and fast iterations.",
  },
  {
    id: "anthropic",
    label: "Anthropic",
    description: "Strong planning and critique for complex tasks.",
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    description: "Brokered access to multiple hosted models.",
  },
];

type ProviderSelection = Record<TddProvider, boolean>;
type ProviderOverrides = Record<TddProvider, string>;

const DEFAULT_SELECTION: ProviderSelection = {
  openai: true,
  anthropic: true,
  openrouter: false,
};

const DEFAULT_OVERRIDES: ProviderOverrides = {
  openai: "",
  anthropic: "",
  openrouter: "",
};

export default function TddRunsPage() {
  const [message, setMessage] = useState("");
  const [selection, setSelection] = useState<ProviderSelection>(DEFAULT_SELECTION);
  const [overrides, setOverrides] = useState<ProviderOverrides>(DEFAULT_OVERRIDES);
  const [temperature, setTemperature] = useState("");
  const [result, setResult] = useState<AgentTddRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedProviders = useMemo(
    () => Object.entries(selection).filter(([, enabled]) => enabled).map(([provider]) => provider as TddProvider),
    [selection]
  );

  const parsedTemperature = useMemo(() => {
    if (!temperature.trim()) {
      return undefined;
    }
    const value = Number.parseFloat(temperature);
    return Number.isFinite(value) ? value : undefined;
  }, [temperature]);

  const handleProviderToggle = (provider: TddProvider) => {
    setSelection((prev) => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleOverrideChange = (provider: TddProvider, value: string) => {
    setOverrides((prev) => ({ ...prev, [provider]: value }));
  };

  const buildPayload = (): AgentTddRunCreate => {
    const subagents = selectedProviders.map((provider) => ({
      name: provider,
      provider,
      model_name: overrides[provider].trim() || undefined,
      temperature: parsedTemperature,
    }));

    return {
      message: message.trim(),
      history: [],
      subagents,
    };
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResult(null);

    if (!message.trim()) {
      setError("Provide a prompt to run the TDD workflow.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = buildPayload();
      const data = await apiClient.post<AgentTddRunResult>("/tdd-runs", payload);
      setResult(data);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to run the TDD workflow.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderCandidate = (candidate: AgentCandidate) => (
    <Card key={candidate.id}>
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          {candidate.agent_name}
          <Badge variant="secondary">{candidate.provider || "unknown"}</Badge>
          {candidate.model_name && <Badge variant="outline">{candidate.model_name}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="rounded-lg border bg-muted/30 p-3">
          <p className="text-xs font-medium uppercase text-muted-foreground">Output</p>
          <p className="mt-2 whitespace-pre-wrap">{candidate.output || "No output returned."}</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">Metrics</p>
            <pre className="mt-2 overflow-auto text-xs">
              {JSON.stringify(candidate.metrics, null, 2)}
            </pre>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">Tool Calls</p>
            <pre className="mt-2 overflow-auto text-xs">
              {JSON.stringify(candidate.tool_calls, null, 2)}
            </pre>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">TDD Runs</h1>
        <p className="text-muted-foreground text-sm sm:text-base">
          Run multi-provider subagents, pick the best candidate, and capture checkpoints.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Run configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="tdd-message">Prompt</Label>
              <textarea
                id="tdd-message"
                className="min-h-[120px] w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Describe the task you want the subagents to solve..."
                value={message}
                onChange={(event) => setMessage(event.target.value)}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              {PROVIDER_OPTIONS.map((provider) => {
                const enabled = selection[provider.id];
                return (
                  <div
                    key={provider.id}
                    className="rounded-lg border p-3 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <input
                        id={`provider-${provider.id}`}
                        type="checkbox"
                        className="mt-1 h-4 w-4"
                        checked={enabled}
                        onChange={() => handleProviderToggle(provider.id)}
                      />
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Label htmlFor={`provider-${provider.id}`}>{provider.label}</Label>
                          <Badge variant={enabled ? "default" : "secondary"}>
                            {enabled ? "Enabled" : "Disabled"}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{provider.description}</p>
                        <div className="space-y-1">
                          <Label htmlFor={`model-${provider.id}`} className="text-xs">
                            Model override
                          </Label>
                          <Input
                            id={`model-${provider.id}`}
                            placeholder="Optional model name"
                            value={overrides[provider.id]}
                            onChange={(event) => handleOverrideChange(provider.id, event.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="grid gap-4 sm:grid-cols-2 sm:items-end">
              <div className="space-y-1">
                <Label htmlFor="temperature">Temperature (optional)</Label>
                <Input
                  id="temperature"
                  inputMode="decimal"
                  placeholder="e.g. 0.2"
                  value={temperature}
                  onChange={(event) => setTemperature(event.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Applies to all selected subagents for this run.
                </p>
              </div>
              <div className="flex justify-end">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    "Run TDD"
                  )}
                </Button>
              </div>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2 text-lg">
                Run summary
                <Badge variant="secondary">{result.run.status}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">Run ID</p>
                  <p className="mt-1 break-all font-mono text-xs">{result.run.id}</p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">Workspace</p>
                  <p className="mt-1">{result.run.workspace_ref || "None"}</p>
                </div>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <p className="text-xs font-medium uppercase text-muted-foreground">Model Config</p>
                <pre className="mt-2 overflow-auto text-xs">
                  {JSON.stringify(result.run.model_config || {}, null, 2)}
                </pre>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <p className="text-xs font-medium uppercase text-muted-foreground">Input Payload</p>
                <pre className="mt-2 overflow-auto text-xs">
                  {JSON.stringify(result.run.input_payload || {}, null, 2)}
                </pre>
              </div>
            </CardContent>
          </Card>

          {result.candidates.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Candidates</h2>
              {result.candidates.map(renderCandidate)}
            </div>
          )}

          {result.decision && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Judge decision</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="default">Selected</Badge>
                  <span className="font-mono text-xs">{result.decision.candidate_id}</span>
                </div>
                {result.decision.score !== null && result.decision.score !== undefined && (
                  <p>Score: {result.decision.score}</p>
                )}
                {result.decision.rationale && (
                  <div className="rounded-lg border bg-muted/30 p-3">
                    <p className="text-xs font-medium uppercase text-muted-foreground">Rationale</p>
                    <p className="mt-2 whitespace-pre-wrap">{result.decision.rationale}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {result.checkpoints.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Checkpoints</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {result.checkpoints.map((checkpoint) => (
                  <div key={checkpoint.id} className="rounded-lg border p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">#{checkpoint.sequence}</Badge>
                      <span className="font-medium">{checkpoint.label || "checkpoint"}</span>
                    </div>
                    <pre className="mt-2 overflow-auto text-xs">
                      {JSON.stringify(checkpoint.state, null, 2)}
                    </pre>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {result.errors.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Errors</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {result.errors.map((errorItem) => (
                  <div key={`${errorItem.agent_name}-${errorItem.provider}`} className="rounded-lg border p-3">
                    <p className="font-medium">
                      {errorItem.agent_name} ({errorItem.provider})
                    </p>
                    <p className="mt-1 text-destructive">{errorItem.error}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
