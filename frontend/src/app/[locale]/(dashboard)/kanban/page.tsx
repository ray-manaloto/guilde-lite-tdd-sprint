import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { LayoutGrid } from "lucide-react";

export default function KanbanPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold sm:text-3xl">Kanban Board</h1>
          <Badge variant="outline">Optional</Badge>
        </div>
        <p className="text-muted-foreground text-sm sm:text-base">
          The Kanban view is planned as an optional complement to Sprint planning.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <LayoutGrid className="h-5 w-5" /> Coming soon
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Focus on the Sprint board for now. We will add Kanban once sprint execution flows are
          locked in.
        </CardContent>
      </Card>
    </div>
  );
}
