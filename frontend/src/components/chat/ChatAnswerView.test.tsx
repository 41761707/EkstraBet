import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ChatAnswerView } from "@/components/chat/ChatAnswerView";
import { ChatChartRenderer } from "@/components/chat/ChatChartRenderer";
import type { ChatAnswer, ChatChartSpec } from "@/types/api";

const sampleChart: ChatChartSpec = {
  type: "bar",
  title: "Strzały celne",
  yLabel: "SOT",
  seriesLabel: "Drużyna",
  points: [
    { label: "M1", value: 4 },
    { label: "M2", value: 7 },
  ],
};

const sampleAnswer: ChatAnswer = {
  answerText: "Argentyna miała średnio 5.5 strzału celnego.",
  chart: sampleChart,
  table: {
    title: "Tabela testowa",
    columns: ["Mecz", "SOT"],
    rows: [
      ["M1", 4],
      ["M2", 7],
    ],
  },
  dataSources: [
    {
      label: "Profil",
      endpoint: "GET /teams/1/profile",
      params: { limit: 5 },
    },
  ],
  warnings: ["Niejednoznaczna nazwa drużyny — wybrano najlepsze dopasowanie."],
};

describe("ChatChartRenderer", () => {
  it("renders bar chart title and values", () => {
    const html = renderToStaticMarkup(
      createElement(ChatChartRenderer, { chart: sampleChart }),
    );
    expect(html).toContain("Strzały celne");
    expect(html).toContain("M1");
    expect(html).toContain("7");
  });

  it("renders line chart svg path", () => {
    const html = renderToStaticMarkup(
      createElement(ChatChartRenderer, {
        chart: { ...sampleChart, type: "line" },
      }),
    );
    expect(html).toContain("<svg");
    expect(html).toContain("<path");
  });

  it("returns null for empty points", () => {
    const html = renderToStaticMarkup(
      createElement(ChatChartRenderer, {
        chart: { ...sampleChart, points: [] },
      }),
    );
    expect(html).toBe("");
  });
});

describe("ChatAnswerView", () => {
  it("renders text, chart, table, warning and sources", () => {
    const html = renderToStaticMarkup(
      createElement(ChatAnswerView, { answer: sampleAnswer }),
    );
    expect(html).toContain("Argentyna miała średnio");
    expect(html).toContain("Strzały celne");
    expect(html).toContain("Tabela testowa");
    expect(html).toContain("Niejednoznaczna nazwa drużyny");
    expect(html).toContain("Źródła danych");
    expect(html).toContain("/teams/1/profile");
  });

  it("renders text-only answer without chart section title", () => {
    const html = renderToStaticMarkup(
      createElement(ChatAnswerView, {
        answer: {
          answerText: "Brak danych do wykresu.",
          chart: null,
          table: null,
          dataSources: [],
          warnings: [],
        },
      }),
    );
    expect(html).toContain("Brak danych do wykresu.");
    expect(html).not.toContain("Strzały celne");
  });
});
