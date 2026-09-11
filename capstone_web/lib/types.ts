export type ChatSummary = {
  id: string;
  title: string;
};

export type ChartSpec = {
  type: "bar" | "pie" | "line";
  title?: string;
  labels: string[];
  data: number[];
};

export type ChatMessageItem =
  | { role: "user" | "assistant"; content: string }
  | { role: "chart"; spec: ChartSpec };
