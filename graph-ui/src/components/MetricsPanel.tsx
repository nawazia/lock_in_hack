import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Shield, TrendingUp, Zap, Eye } from "lucide-react";

const MetricsPanel = () => {
  const metrics = [
    {
      label: "Reliability Score",
      value: 94,
      icon: Shield,
      color: "text-primary",
      description: "Source credibility & fact-checking",
    },
    {
      label: "Hallucination Risk",
      value: 8,
      icon: Eye,
      color: "text-destructive",
      description: "Confidence in factual accuracy",
      inverse: true,
    },
    {
      label: "Response Latency",
      value: 85,
      icon: Zap,
      color: "text-accent",
      description: "Processing speed optimization",
    },
    {
      label: "Cost Efficiency",
      value: 92,
      icon: TrendingUp,
      color: "text-secondary",
      description: "Token usage & API costs",
    },
  ];

  return (
    <Card className="glass-card border-primary/30 p-6 h-fit sticky top-6">
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold mb-1">System Metrics</h3>
          <p className="text-sm text-muted-foreground">Real-time observability</p>
        </div>

        <div className="space-y-6">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            const displayValue = metric.inverse ? 100 - metric.value : metric.value;
            
            return (
              <div key={metric.label} className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${metric.color}`} />
                    <div>
                      <p className="text-sm font-medium">{metric.label}</p>
                      <p className="text-xs text-muted-foreground">{metric.description}</p>
                    </div>
                  </div>
                  <span className={`text-lg font-bold ${metric.color}`}>
                    {metric.value}%
                  </span>
                </div>
                <Progress
                  value={displayValue}
                  className="h-2"
                  indicatorClassName={metric.inverse ? "bg-destructive" : "bg-primary"}
                />
              </div>
            );
          })}
        </div>

        <div className="pt-4 border-t border-border/50 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Articles Analyzed</span>
            <span className="font-semibold">247</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Avg. Processing Time</span>
            <span className="font-semibold">2.3s</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Carbon Footprint</span>
            <span className="font-semibold text-primary">Low</span>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default MetricsPanel;
