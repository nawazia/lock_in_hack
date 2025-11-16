import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Send, Bot, User, Plane, Zap, Leaf } from "lucide-react";
import AgentPipeline from "./AgentPipeline";
import MetricsPanel from "./MetricsPanel";
import axios from "axios";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [speedValue, setSpeedValue] = useState<number>(50); // 0=slow/cheap, 100=fast/expensive
  const [carbonValue, setCarbonValue] = useState<number>(50); // 0=low priority, 100=high priority

  // Determine optimization preference based on both sliders
  const getOptimizationPreference = (): string => {
    // High speed priority (>60) -> latency
    if (speedValue > 60) return "latency";
    // High carbon priority (>60) -> carbon
    if (carbonValue > 60) return "carbon";
    // Low speed (<40) or balanced -> cost
    if (speedValue < 40) return "cost";
    // Otherwise balanced
    return "default";
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Call the travel planning API with session and optimization preference
      const response = await axios.post('/api/query', {
        query: input,
        session_id: sessionId,
        optimization_preference: getOptimizationPreference()
      });

      const data = response.data;

      // Store session ID for subsequent requests
      if (data.session_id) {
        setSessionId(data.session_id);
      }
      let assistantContent = "";

      // Check if needs clarification
      if (data.needs_user_input && data.clarifying_questions?.length > 0) {
        assistantContent = "I need some more information to plan your perfect trip:\n\n";
        data.clarifying_questions.forEach((q: string, i: number) => {
          assistantContent += `${i + 1}. ${q}\n`;
        });
      }
      // Check if we have an itinerary
      else if (data.final_itinerary) {
        const itinerary = data.final_itinerary;
        assistantContent = `🎉 **${itinerary.title}**\n\n`;
        assistantContent += `📅 ${itinerary.start_date} to ${itinerary.end_date} (${itinerary.total_days} days)\n`;
        assistantContent += `📍 ${itinerary.destinations?.join(', ')}\n`;
        assistantContent += `💰 Total: $${itinerary.total_estimated_cost?.toFixed(2)}\n\n`;

        // Flight info
        const flight = itinerary.budget_option?.flight_outbound;
        if (flight) {
          assistantContent += `✈️ **Flight**\n`;
          assistantContent += `   ${flight.airline} ${flight.flight_number}\n`;
          assistantContent += `   ${flight.departure_airport} → ${flight.arrival_airport}\n`;
          assistantContent += `   $${flight.price.toFixed(2)}\n\n`;
        }

        // Hotel info
        const hotel = itinerary.budget_option?.hotel;
        if (hotel) {
          assistantContent += `🏨 **Hotel**\n`;
          assistantContent += `   ${hotel.name}\n`;
          assistantContent += `   ${hotel.location}\n`;
          assistantContent += `   $${hotel.price_per_night.toFixed(2)}/night\n\n`;
        }
      }
      // Fallback to summary
      else if (data.summary) {
        assistantContent = data.summary;
      } else {
        assistantContent = "I'm working on your travel plan. Please tell me more about your preferences!";
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: assistantContent,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error calling API:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Sorry, I encountered an error. Please try again!`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="min-h-screen px-6 py-12">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="text-center space-y-4">
          <h2 className="text-3xl md:text-4xl font-bold">
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Plan Your Dream Trip
            </span>
          </h2>
          <p className="text-muted-foreground">
            Tell me where you want to go, and I'll plan the perfect itinerary
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Chat Area */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="glass-card border-primary/30 overflow-hidden">
              <div className="h-[500px] overflow-y-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                    <div className="text-center space-y-2">
                      <Plane className="w-12 h-12 mx-auto text-primary/50" />
                      <p>Start planning your next adventure</p>
                      <p className="text-sm">Example: "I want to visit Paris for 5 days with a $3000 budget"</p>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${
                        message.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {message.role === "assistant" && (
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                          <Bot className="w-4 h-4 text-primary" />
                        </div>
                      )}
                      <div
                        className={`max-w-[80%] p-4 rounded-lg ${
                          message.role === "user"
                            ? "bg-primary text-background"
                            : "bg-muted"
                        }`}
                      >
                        <p className="text-sm leading-relaxed">{message.content}</p>
                      </div>
                      {message.role === "user" && (
                        <div className="w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center flex-shrink-0">
                          <User className="w-4 h-4 text-secondary" />
                        </div>
                      )}
                    </div>
                  ))
                )}
                {isLoading && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-primary animate-pulse" />
                    </div>
                    <div className="bg-muted p-4 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce animation-delay-200" />
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce animation-delay-400" />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>Thinking safely with EDFL verification</span>
                          <span className="text-green-600 font-medium">✓</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="p-4 border-t border-border/50 space-y-3">
                {/* Compact Optimization Controls */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  {/* Speed Slider */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        Speed
                      </span>
                      <span className="text-primary font-medium">{speedValue}%</span>
                    </div>
                    <Slider
                      value={[speedValue]}
                      onValueChange={(value) => setSpeedValue(value[0])}
                      max={100}
                      min={0}
                      step={10}
                      className="w-full"
                    />
                  </div>

                  {/* Carbon Slider */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Leaf className="w-3 h-3" />
                        Eco
                      </span>
                      <span className="text-emerald-600 font-medium">{carbonValue}%</span>
                    </div>
                    <Slider
                      value={[carbonValue]}
                      onValueChange={(value) => setCarbonValue(value[0])}
                      max={100}
                      min={0}
                      step={10}
                      className="w-full"
                    />
                  </div>
                </div>

                {/* Message Input */}
                <div className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    placeholder="I want to visit Paris for 5 days with a $2000 budget..."
                    className="bg-background/50 border-border/50"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="bg-primary hover:bg-primary/90 text-background"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>

            <AgentPipeline isActive={isLoading} />
          </div>

          {/* Metrics Panel */}
          <div className="lg:col-span-1">
            <MetricsPanel />
          </div>
        </div>
      </div>
    </section>
  );
};

export default ChatInterface;
