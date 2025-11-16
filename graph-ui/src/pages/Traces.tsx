import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, ExternalLink, Shield, AlertTriangle, CheckCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

interface TraceRun {
  id: string;
  name: string;
  run_type: string;
  start_time: string | null;
  end_time: string | null;
  latency: number | null;
  inputs: any;
  outputs: any;
  error: string | null;
  parent_run_id: string | null;
  child_run_ids: string[];
  status: string;
}

interface HallucinationResult {
  agent_name: string;
  roh_score: number;
  flagged: boolean;
  rationale: string;
}

interface ObservabilityReport {
  query_id: string;
  user_query: string;
  steps_completed: number;
  hallucination_detections: HallucinationResult[];
  audit_issues: string[];
}

interface TraceData {
  run_id: string;
  runs: TraceRun[];
  total_runs: number;
  observability_report?: ObservabilityReport;
}

const Traces = () => {
  const navigate = useNavigate();
  const [traceData, setTraceData] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLatestTrace = async () => {
      try {
        setLoading(true);
        const response = await axios.get('/api/traces/latest');
        if (response.data.success) {
          setTraceData(response.data.trace);
        } else {
          setError(response.data.error || "Failed to fetch trace");
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch trace data");
      } finally {
        setLoading(false);
      }
    };

    fetchLatestTrace();
  }, []);

  const buildTreeStructure = (runs: TraceRun[]) => {
    const runsById = new Map(runs.map(run => [run.id, run]));
    const rootRuns = runs.filter(run => !run.parent_run_id);

    const renderRun = (run: TraceRun, depth: number = 0) => {
      const hasError = run.status === "error";
      const children = runs.filter(r => r.parent_run_id === run.id);

      return (
        <div key={run.id} className="mb-2">
          <Card className={`p-4 ${hasError ? 'border-destructive' : 'border-border'}`} style={{ marginLeft: `${depth * 24}px` }}>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{run.name}</span>
                  <span className="ml-2 text-sm text-muted-foreground">({run.run_type})</span>
                </div>
                {run.latency && (
                  <span className="text-sm text-muted-foreground">{run.latency.toFixed(2)}s</span>
                )}
              </div>

              {run.inputs && Object.keys(run.inputs).length > 0 && (
                <details className="text-sm">
                  <summary className="cursor-pointer text-muted-foreground">Inputs</summary>
                  <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-40">
                    {JSON.stringify(run.inputs, null, 2)}
                  </pre>
                </details>
              )}

              {run.outputs && Object.keys(run.outputs).length > 0 && (
                <details className="text-sm">
                  <summary className="cursor-pointer text-muted-foreground">Outputs</summary>
                  <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-40">
                    {JSON.stringify(run.outputs, null, 2)}
                  </pre>
                </details>
              )}

              {run.error && (
                <div className="text-sm text-destructive">
                  <strong>Error:</strong> {run.error}
                </div>
              )}
            </div>
          </Card>

          {children.map(child => renderRun(child, depth + 1))}
        </div>
      );
    };

    return rootRuns.map(run => renderRun(run));
  };

  return (
    <div className="min-h-screen p-6 bg-background">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={() => navigate("/")}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <h1 className="text-3xl font-bold">Observability Dashboard</h1>
          </div>
          <Button
            variant="outline"
            onClick={() => window.open("https://smith.langchain.com", "_blank")}
          >
            Open in LangSmith
            <ExternalLink className="w-4 h-4 ml-2" />
          </Button>
        </div>

        {loading && (
          <Card className="p-8 text-center">
            <p className="text-muted-foreground">Loading latest trace...</p>
          </Card>
        )}

        {error && (
          <Card className="p-8 border-destructive">
            <p className="text-destructive">Error: {error}</p>
          </Card>
        )}

        {traceData && (
          <div className="space-y-6">
            <Card className="p-4 bg-muted">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">Trace ID: {traceData.run_id}</h2>
                  <p className="text-sm text-muted-foreground">Total Runs: {traceData.total_runs}</p>
                </div>
              </div>
            </Card>

            {/* Hallucination Detection Results */}
            {traceData.observability_report && (
              <div className="space-y-4">
                <h3 className="text-xl font-semibold flex items-center gap-2">
                  <Shield className="w-5 h-5 text-green-600" />
                  EDFL Hallucination Detection
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {traceData.observability_report.hallucination_detections?.map((detection, idx) => (
                    <Card key={idx} className={`p-4 ${detection.flagged ? 'border-yellow-600' : 'border-green-600'}`}>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">{detection.agent_name}</span>
                          {detection.flagged ? (
                            <AlertTriangle className="w-5 h-5 text-yellow-600" />
                          ) : (
                            <CheckCircle className="w-5 h-5 text-green-600" />
                          )}
                        </div>
                        <div className="text-sm">
                          <span className="text-muted-foreground">RoH Score: </span>
                          <span className={detection.roh_score > 0.5 ? 'text-yellow-600 font-medium' : 'text-green-600 font-medium'}>
                            {(detection.roh_score * 100).toFixed(1)}%
                          </span>
                        </div>
                        {detection.flagged && (
                          <div className="text-xs text-muted-foreground mt-2 p-2 bg-muted rounded">
                            {detection.rationale}
                          </div>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>

                {traceData.observability_report.audit_issues && traceData.observability_report.audit_issues.length > 0 && (
                  <Card className="p-4 border-yellow-600">
                    <h4 className="font-semibold mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-yellow-600" />
                      Audit Issues Detected
                    </h4>
                    <ul className="space-y-1 text-sm">
                      {traceData.observability_report.audit_issues.map((issue, idx) => (
                        <li key={idx} className="text-muted-foreground">• {issue}</li>
                      ))}
                    </ul>
                  </Card>
                )}
              </div>
            )}

            <div className="space-y-2">
              <h3 className="text-xl font-semibold">Execution Tree</h3>
              {buildTreeStructure(traceData.runs)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Traces;
