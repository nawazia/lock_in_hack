import { Button } from "@/components/ui/button";
import { ArrowRight, Plane, Shield, Zap } from "lucide-react";
import MatrixBackground from "./MatrixBackground";
import { useNavigate } from "react-router-dom";

const Hero = ({ onStartDemo }: { onStartDemo: () => void }) => {
  const navigate = useNavigate();
  return (
    <section className="relative min-h-screen flex items-center justify-center px-6 py-20 overflow-hidden">
      <MatrixBackground />
      
      {/* Subtle background gradient */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-1/3 left-1/3 w-[600px] h-[600px] bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 right-1/3 w-[500px] h-[500px] bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto text-center space-y-8">
        {/* Headline */}
        <h1 className="text-5xl md:text-7xl font-bold leading-tight">
          <span className="text-primary">
            AI-Powered Travel Planning
          </span>
          <br />
          <span className="text-foreground">with EDFL Hallucination Detection</span>
        </h1>

        {/* Subheadline */}
        <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
          Multi-agent system with hallucination detection. Plan your perfect trip with confidence and transparency.
        </p>

        {/* Feature highlights */}
        <div className="flex flex-wrap justify-center gap-6 py-8">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Plane className="w-5 h-5 text-primary" />
            <span>Smart Itinerary Planning</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Shield className="w-5 h-5 text-primary" />
            <span>EDFL Hallucination Detection</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Zap className="w-5 h-5 text-primary" />
            <span>Real-time Observability</span>
          </div>
        </div>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
          <Button
            size="lg"
            onClick={onStartDemo}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium px-8 py-6 text-lg transition-all"
          >
            Start Demo
            <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={() => navigate("/traces")}
            className="border-border hover:bg-muted px-8 py-6 text-lg"
          >
            Observability
          </Button>
        </div>

        {/* Architecture preview */}
        <div className="pt-12 space-y-4">
          <p className="text-sm text-muted-foreground uppercase tracking-wider">Agent Workflow</p>
          <div className="glass-card p-8 rounded-xl max-w-2xl mx-auto">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="text-center flex-1 min-w-[100px]">
                <div className="w-12 h-12 mx-auto mb-2 rounded-lg bg-primary/20 flex items-center justify-center">
                  <span className="text-primary font-bold">1</span>
                </div>
                <p className="text-xs text-muted-foreground">Parse Query</p>
              </div>
              <div className="text-primary">→</div>
              <div className="text-center flex-1 min-w-[100px]">
                <div className="w-12 h-12 mx-auto mb-2 rounded-lg bg-secondary/20 flex items-center justify-center">
                  <span className="text-secondary font-bold">2</span>
                </div>
                <p className="text-xs text-muted-foreground">Search Options</p>
              </div>
              <div className="text-secondary">→</div>
              <div className="text-center flex-1 min-w-[100px]">
                <div className="w-12 h-12 mx-auto mb-2 rounded-lg bg-accent/20 flex items-center justify-center">
                  <span className="text-accent font-bold">3</span>
                </div>
                <p className="text-xs text-muted-foreground">Plan Budget</p>
              </div>
              <div className="text-accent">→</div>
              <div className="text-center flex-1 min-w-[100px]">
                <div className="w-12 h-12 mx-auto mb-2 rounded-lg bg-primary/20 flex items-center justify-center">
                  <span className="text-primary font-bold">4</span>
                </div>
                <p className="text-xs text-muted-foreground">Create Itinerary</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
