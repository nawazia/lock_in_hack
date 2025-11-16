import { useState } from "react";
import Hero from "@/components/Hero";
import ChatInterface from "@/components/ChatInterface";

const Index = () => {
  const [showChat, setShowChat] = useState(false);

  const handleStartDemo = () => {
    setShowChat(true);
    // Smooth scroll to chat
    setTimeout(() => {
      document.getElementById("chat-section")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  return (
    <div className="min-h-screen">
      <Hero onStartDemo={handleStartDemo} />
      {showChat && (
        <div id="chat-section">
          <ChatInterface />
        </div>
      )}
    </div>
  );
};

export default Index;
