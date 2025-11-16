import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const ChatPanel = ({ isOpen, onClose, nodes, runMap }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState('');
  const [mentionPosition, setMentionPosition] = useState(0);
  const [selectedNodes, setSelectedNodes] = useState([]);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Get hierarchical path from root to node
  const getNodePath = (nodeId) => {
    const path = [];
    let currentId = nodeId;

    // Walk up the parent chain
    while (currentId) {
      const nodeData = runMap.get(currentId);
      if (!nodeData) break;

      path.unshift(nodeData.name);
      currentId = nodeData.parentRunId;
    }

    return path.join('/');
  };

  // Get relative path by removing common prefix across all nodes
  const getRelativePath = (nodeId) => {
    const fullPath = getNodePath(nodeId);

    // Find common prefix across all node paths
    if (filteredNodes.length === 0) return fullPath;

    const allPaths = filteredNodes.map(n => getNodePath(n.id));
    const pathParts = fullPath.split('/');

    // Find how many leading segments are common to all paths
    let commonPrefixLength = 0;
    for (let i = 0; i < pathParts.length; i++) {
      const segment = pathParts[i];
      const allHaveSegment = allPaths.every(p => {
        const parts = p.split('/');
        return parts.length > i && parts[i] === segment;
      });

      if (allHaveSegment) {
        commonPrefixLength = i + 1;
      } else {
        break;
      }
    }

    // Remove common prefix (keep at least one segment)
    const relativeParts = pathParts.slice(Math.max(0, commonPrefixLength - 1));
    return relativeParts.join('/');
  };

  // Filter nodes based on mention search
  const filteredNodes = nodes.filter(node =>
    node.data.name.toLowerCase().includes(mentionSearch.toLowerCase())
  );

  // Handle input change
  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);

    // Check if user is typing @ mention
    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPos);
    const lastAtSign = textBeforeCursor.lastIndexOf('@');

    if (lastAtSign !== -1) {
      const textAfterAt = textBeforeCursor.slice(lastAtSign + 1);
      // Show mentions if @ is the last character or followed by text without spaces
      if (!textAfterAt.includes(' ')) {
        setShowMentions(true);
        setMentionSearch(textAfterAt);
        setMentionPosition(lastAtSign);
        return;
      }
    }
    setShowMentions(false);
  };

  // Handle mention selection
  const selectMention = (node) => {
    const beforeMention = inputValue.slice(0, mentionPosition);
    const afterMention = inputValue.slice(inputRef.current.selectionStart);
    const newValue = `${beforeMention}@${node.data.name} ${afterMention}`;

    setInputValue(newValue);
    setShowMentions(false);
    setMentionSearch('');

    // Add to selected nodes if not already there
    if (!selectedNodes.find(n => n.id === node.id)) {
      setSelectedNodes([...selectedNodes, node]);
    }

    inputRef.current?.focus();
  };

  // Remove node tag
  const removeNodeTag = (nodeId) => {
    setSelectedNodes(selectedNodes.filter(n => n.id !== nodeId));
    // Also remove from input text
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setInputValue(inputValue.replace(`@${node.data.name}`, '').trim());
    }
  };

  // Handle keyboard navigation in mentions
  const handleKeyDown = (e) => {
    if (showMentions && filteredNodes.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        // Could implement arrow key navigation here
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
      } else if (e.key === 'Escape') {
        setShowMentions(false);
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Send message to backend
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage, nodes: [...selectedNodes] }]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Build context from selected nodes
      let nodeContext = '';
      if (selectedNodes.length > 0) {
        nodeContext = '\n\nHere is some relevant context for the nodes the user has asked about:\n\n. Use this to inform your response but by no means should you regurgitate all this information to the user. You should at most summarize/synthesize the relevant information from these nodes to answer the user query effectively.\n\n';
        selectedNodes.forEach(node => {
          const nodeData = node.data;
          nodeContext += `Node: ${nodeData.name}\n`;
          nodeContext += `Type: ${nodeData.runType}\n`;
          nodeContext += `Latency: ${nodeData.latencyFormatted}\n`;
          if (nodeData.totalTokens) {
            nodeContext += `Total Tokens: ${nodeData.totalTokens}\n`;
            nodeContext += `Prompt Tokens: ${nodeData.promptTokens}\n`;
            nodeContext += `Completion Tokens: ${nodeData.completionTokens}\n`;
          }
          nodeContext += `Status: ${nodeData.status}\n`;
          if (nodeData.error) {
            nodeContext += `Error: ${nodeData.error}\n`;
          }
          nodeContext += `Inputs: ${JSON.stringify(nodeData.inputs, null, 2)}\n`;
          nodeContext += `Outputs: ${JSON.stringify(nodeData.outputs, null, 2)}\n`;
          nodeContext += '\n---\n\n';
        });
      }

      // Send to backend
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: userMessage + nodeContext,
        history: messages.map(m => ({ role: m.role, content: m.content }))
      });

      // Add assistant response
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
      setSelectedNodes([]); // Clear selected nodes after sending

    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 999,
            transition: 'opacity 0.3s',
            opacity: isOpen ? 1 : 0
          }}
        />
      )}

      {/* Chat Panel */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '600px',
          height: '100vh',
          backgroundColor: '#1F2937',
          boxShadow: '2px 0 10px rgba(0, 0, 0, 0.3)',
          transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.3s ease-in-out',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '20px',
          borderBottom: '1px solid #374151',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <h2 style={{ margin: 0, color: 'white', fontSize: '18px', fontWeight: '600' }}>
            💬 Trace Assistant
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#9CA3AF',
              fontSize: '24px',
              cursor: 'pointer',
              padding: '0',
              lineHeight: '1'
            }}
          >
            ×
          </button>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          {messages.length === 0 && (
            <div style={{
              textAlign: 'center',
              color: '#9CA3AF',
              marginTop: '40px',
              fontSize: '14px'
            }}>
              <p>Ask questions about your trace!</p>
              <p style={{ marginTop: '8px', fontSize: '12px' }}>
                Use @ to mention specific nodes
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%'
            }}>
              {/* Show tagged nodes for user messages */}
              {msg.role === 'user' && msg.nodes && msg.nodes.length > 0 && (
                <div style={{
                  marginBottom: '4px',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '4px',
                  justifyContent: 'flex-end'
                }}>
                  {msg.nodes.map(node => (
                    <span key={node.id} style={{
                      fontSize: '11px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#374151',
                      color: '#9CA3AF'
                    }}>
                      @{node.data.name}
                    </span>
                  ))}
                </div>
              )}

              <div style={{
                padding: '12px 16px',
                borderRadius: '12px',
                backgroundColor: msg.role === 'user' ? '#3B82F6' : '#374151',
                color: 'white',
                fontSize: '14px',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {msg.content}
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{
              alignSelf: 'flex-start',
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: '#374151',
              color: '#9CA3AF',
              fontSize: '14px'
            }}>
              Thinking...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Selected Nodes Tags */}
        {selectedNodes.length > 0 && (
          <div style={{
            padding: '8px 20px',
            borderTop: '1px solid #374151',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
            backgroundColor: '#111827'
          }}>
            {selectedNodes.map(node => (
              <div key={node.id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                borderRadius: '6px',
                backgroundColor: node.data.color,
                fontSize: '12px',
                color: 'white'
              }}>
                <span>@{node.data.name}</span>
                <button
                  onClick={() => removeNodeTag(node.id)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer',
                    padding: '0',
                    fontSize: '16px',
                    lineHeight: '1'
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{
          padding: '20px',
          borderTop: '1px solid #374151',
          position: 'relative'
        }}>
          {/* Mentions dropdown */}
          {showMentions && filteredNodes.length > 0 && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: '20px',
              right: '20px',
              maxHeight: '200px',
              overflowY: 'auto',
              backgroundColor: '#374151',
              borderRadius: '8px',
              marginBottom: '8px',
              boxShadow: '0 -4px 6px rgba(0, 0, 0, 0.1)'
            }}>
              {filteredNodes.slice(0, 10).map(node => (
                <div
                  key={node.id}
                  onClick={() => selectMention(node)}
                  style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #4B5563',
                    color: 'white',
                    fontSize: '13px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'background-color 0.15s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#4B5563'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <div style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: node.data.color
                  }} />
                  <span style={{ fontWeight: '500' }}>{node.data.name}</span>
                  <span
                    style={{
                      color: '#9CA3AF',
                      fontSize: '11px',
                      marginLeft: 'auto',
                      maxWidth: '60%',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      textAlign: 'right'
                    }}
                    title={getNodePath(node.id)}
                  >
                    {getRelativePath(node.id)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '8px' }}>
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the trace... (use @ to mention nodes)"
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #4B5563',
                backgroundColor: '#111827',
                color: 'white',
                fontSize: '14px',
                resize: 'none',
                minHeight: '44px',
                maxHeight: '120px',
                fontFamily: 'inherit',
                outline: 'none'
              }}
              rows={1}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              style={{
                padding: '0 20px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: inputValue.trim() && !isLoading ? '#3B82F6' : '#4B5563',
                color: 'white',
                fontSize: '14px',
                fontWeight: '600',
                cursor: inputValue.trim() && !isLoading ? 'pointer' : 'not-allowed',
                transition: 'background-color 0.2s'
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatPanel;
