/**
 * Mock trace data for testing the visualization without LangSmith
 *
 * This represents a typical multi-agent news query trace
 */

export const mockTraceData = {
  run_id: "mock-run-123",
  runs: [
    // Root: process_query
    {
      id: "run-1",
      name: "process_query",
      run_type: "chain",
      start_time: "2025-01-15T10:00:00.000Z",
      end_time: "2025-01-15T10:00:08.500Z",
      inputs: { query: "What are the latest developments in AI?" },
      outputs: {
        summary: "Latest AI developments include...",
        analysis: "Key trends identified...",
        search_results_count: 5,
        rag_results_count: 3
      },
      error: null,
      tags: ["orchestrator", "main"],
      extra: { metadata: { version: "1.0" } },
      parent_run_id: null,
      child_run_ids: ["run-2", "run-6", "run-10", "run-13"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },

    // Branch 1: search_node
    {
      id: "run-2",
      name: "search_node",
      run_type: "chain",
      start_time: "2025-01-15T10:00:00.100Z",
      end_time: "2025-01-15T10:00:02.800Z",
      inputs: { user_query: "What are the latest developments in AI?" },
      outputs: { search_results: ["article1", "article2", "article3", "article4", "article5"] },
      error: null,
      tags: ["search"],
      extra: {},
      parent_run_id: "run-1",
      child_run_ids: ["run-3"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-3",
      name: "news_search_agent_run",
      run_type: "chain",
      start_time: "2025-01-15T10:00:00.150Z",
      end_time: "2025-01-15T10:00:02.750Z",
      inputs: { state: { user_query: "What are the latest developments in AI?" } },
      outputs: { articles: 5 },
      error: null,
      tags: [],
      extra: {},
      parent_run_id: "run-2",
      child_run_ids: ["run-4"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-4",
      name: "news_search",
      run_type: "chain",
      start_time: "2025-01-15T10:00:00.200Z",
      end_time: "2025-01-15T10:00:02.700Z",
      inputs: { query: "What are the latest developments in AI?" },
      outputs: { articles: ["..."] },
      error: null,
      tags: [],
      extra: {},
      parent_run_id: "run-3",
      child_run_ids: ["run-5"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-5",
      name: "valyu_search_tool",
      run_type: "tool",
      start_time: "2025-01-15T10:00:00.250Z",
      end_time: "2025-01-15T10:00:02.650Z",
      inputs: { query: "What are the latest developments in AI?" },
      outputs: "Found 5 articles about AI developments...",
      error: null,
      tags: ["tool", "search"],
      extra: {},
      parent_run_id: "run-4",
      child_run_ids: [],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },

    // Branch 2: rag_node
    {
      id: "run-6",
      name: "rag_node",
      run_type: "chain",
      start_time: "2025-01-15T10:00:02.900Z",
      end_time: "2025-01-15T10:00:04.200Z",
      inputs: { search_results: 5 },
      outputs: { rag_results: 3, stored: 5 },
      error: null,
      tags: ["rag"],
      extra: {},
      parent_run_id: "run-1",
      child_run_ids: ["run-7"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-7",
      name: "rag_agent_run",
      run_type: "chain",
      start_time: "2025-01-15T10:00:02.950Z",
      end_time: "2025-01-15T10:00:04.150Z",
      inputs: { state: { search_results: ["..."] } },
      outputs: { rag_results: ["..."] },
      error: null,
      tags: [],
      extra: {},
      parent_run_id: "run-6",
      child_run_ids: ["run-8", "run-9"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-8",
      name: "rag_store_articles",
      run_type: "chain",
      start_time: "2025-01-15T10:00:03.000Z",
      end_time: "2025-01-15T10:00:03.500Z",
      inputs: { articles: 5 },
      outputs: { stored: 5 },
      error: null,
      tags: ["storage"],
      extra: {},
      parent_run_id: "run-7",
      child_run_ids: [],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-9",
      name: "rag_retrieve_articles",
      run_type: "retriever",
      start_time: "2025-01-15T10:00:03.550Z",
      end_time: "2025-01-15T10:00:04.100Z",
      inputs: { query: "What are the latest developments in AI?" },
      outputs: { articles: 3 },
      error: null,
      tags: ["retrieval"],
      extra: {},
      parent_run_id: "run-7",
      child_run_ids: [],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },

    // Branch 3: analysis_node
    {
      id: "run-10",
      name: "analysis_node",
      run_type: "chain",
      start_time: "2025-01-15T10:00:04.300Z",
      end_time: "2025-01-15T10:00:06.100Z",
      inputs: { search_results: 5, rag_results: 3 },
      outputs: { analysis: "Identified 3 key topics..." },
      error: null,
      tags: ["analysis"],
      extra: {},
      parent_run_id: "run-1",
      child_run_ids: ["run-11"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-11",
      name: "analysis_agent_run",
      run_type: "chain",
      start_time: "2025-01-15T10:00:04.350Z",
      end_time: "2025-01-15T10:00:06.050Z",
      inputs: { state: { search_results: ["..."], rag_results: ["..."] } },
      outputs: { analysis: "..." },
      error: null,
      tags: [],
      extra: {},
      parent_run_id: "run-10",
      child_run_ids: ["run-12"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-12",
      name: "ChatOpenAI",
      run_type: "llm",
      start_time: "2025-01-15T10:00:04.400Z",
      end_time: "2025-01-15T10:00:06.000Z",
      inputs: {
        messages: [
          { role: "system", content: "You are an expert analyst..." },
          { role: "user", content: "Analyze these articles..." }
        ]
      },
      outputs: {
        content: "Based on the articles, I've identified three key developments in AI: 1) Large Language Models, 2) Computer Vision, 3) Robotics..."
      },
      error: null,
      tags: ["llm", "gpt-4"],
      extra: { metadata: { model: "gpt-4o-mini" } },
      parent_run_id: "run-11",
      child_run_ids: [],
      feedback_stats: {},
      total_tokens: 2847,
      prompt_tokens: 2234,
      completion_tokens: 613,
      events: []
    },

    // Branch 4: summary_node
    {
      id: "run-13",
      name: "summary_node",
      run_type: "chain",
      start_time: "2025-01-15T10:00:06.200Z",
      end_time: "2025-01-15T10:00:08.400Z",
      inputs: { analysis: "Identified 3 key topics..." },
      outputs: { summary: "Complete summary with context..." },
      error: null,
      tags: ["summary"],
      extra: {},
      parent_run_id: "run-1",
      child_run_ids: ["run-14"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-14",
      name: "summary_agent_run",
      run_type: "chain",
      start_time: "2025-01-15T10:00:06.250Z",
      end_time: "2025-01-15T10:00:08.350Z",
      inputs: { state: { analysis: "..." } },
      outputs: { summary: "..." },
      error: null,
      tags: [],
      extra: {},
      parent_run_id: "run-13",
      child_run_ids: ["run-15"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "run-15",
      name: "ChatOpenAI",
      run_type: "llm",
      start_time: "2025-01-15T10:00:06.300Z",
      end_time: "2025-01-15T10:00:08.300Z",
      inputs: {
        messages: [
          { role: "system", content: "You are a summarization expert..." },
          { role: "user", content: "Generate a comprehensive summary..." }
        ]
      },
      outputs: {
        content: "# AI Developments Summary\n\n## Executive Summary\nThe latest developments in AI showcase remarkable progress across multiple domains...\n\n## Key Points\n1. Large Language Models continue to advance\n2. Computer Vision reaches new milestones\n3. Robotics integration improves\n\n..."
      },
      error: null,
      tags: ["llm", "gpt-4"],
      extra: { metadata: { model: "gpt-4o-mini" } },
      parent_run_id: "run-14",
      child_run_ids: [],
      feedback_stats: { thumbs_up: 1 },
      total_tokens: 3521,
      prompt_tokens: 2891,
      completion_tokens: 630,
      events: []
    }
  ]
};

/**
 * Mock trace with an error for testing error visualization
 */
export const mockTraceWithError = {
  run_id: "mock-error-run-456",
  runs: [
    {
      id: "err-1",
      name: "process_query",
      run_type: "chain",
      start_time: "2025-01-15T11:00:00.000Z",
      end_time: "2025-01-15T11:00:03.000Z",
      inputs: { query: "Test query" },
      outputs: null,
      error: "Failed to complete workflow",
      tags: [],
      extra: {},
      parent_run_id: null,
      child_run_ids: ["err-2"],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    },
    {
      id: "err-2",
      name: "failing_tool",
      run_type: "tool",
      start_time: "2025-01-15T11:00:00.100Z",
      end_time: "2025-01-15T11:00:03.000Z",
      inputs: { query: "Test" },
      outputs: null,
      error: "ConnectionError: Failed to connect to external API",
      tags: ["error"],
      extra: {},
      parent_run_id: "err-1",
      child_run_ids: [],
      feedback_stats: {},
      total_tokens: null,
      prompt_tokens: null,
      completion_tokens: null,
      events: []
    }
  ]
};
