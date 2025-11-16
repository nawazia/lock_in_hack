import { Card } from "@/components/ui/card";
import { Search, DollarSign, Plane, Map } from "lucide-react";

const agents = [
  {
    name: "Query Parser",
    icon: Search,
    description: "Extracts travel requirements",
    color: "text-primary",
    bgColor: "bg-primary/10",
  },
  {
    name: "Search Agent",
    icon: Plane,
    description: "Finds flights & hotels",
    color: "text-secondary",
    bgColor: "bg-secondary/10",
  },
  {
    name: "Budget Planner",
    icon: DollarSign,
    description: "Optimizes costs & options",
    color: "text-accent",
    bgColor: "bg-accent/10",
  },
  {
    name: "Itinerary Builder",
    icon: Map,
    description: "Creates final plan",
    color: "text-primary",
    bgColor: "bg-primary/10",
  },
];

const AgentPipeline = ({ isActive }: { isActive: boolean }) => {
  return (
    <Card className="glass-card border-primary/30 p-6">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse-glow" />
          Agent Pipeline
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {agents.map((agent, index) => {
            const Icon = agent.icon;
            return (
              <div
                key={agent.name}
                className={`text-center space-y-2 p-4 rounded-lg transition-all ${
                  isActive
                    ? `${agent.bgColor} border border-current ${agent.color}`
                    : "opacity-50"
                }`}
              >
                <div className={`w-10 h-10 mx-auto rounded-lg ${agent.bgColor} flex items-center justify-center ${
                  isActive ? "animate-pulse" : ""
                }`}>
                  <Icon className={`w-5 h-5 ${agent.color}`} />
                </div>
                <div>
                  <p className="font-semibold text-sm">{agent.name}</p>
                  <p className="text-xs text-muted-foreground">{agent.description}</p>
                </div>
              </div>
            );
          })}
        </div>
        {isActive && (
          <div className="pt-4 border-t border-border/50">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse-glow" />
              <span>Planning your perfect trip...</span>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};

export default AgentPipeline;
