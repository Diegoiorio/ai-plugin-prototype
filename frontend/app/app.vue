<!--
  Pagina principale del prototipo frontend.

  Scopo:
  - Raccogliere un prompt utente per analisi CRM.
  - Chiamare il backend `/ai/query`.
  - Visualizzare risultato in formato tabella + grafico a barre configurabile.

  Dati principali:
  - `prompt`, `loading`, `error`, `result`, `selectedX`, `selectedY`.

  Interazioni gestite:
  - Submit form con richiesta HTTP POST.
  - Selezione dinamica assi X/Y per il grafico.

  Ruolo nel flusso frontend:
  - E il punto di ingresso UI che orchestra input utente, stato chiamata API e rendering output.
-->
<script setup lang="ts">
import { computed, ref } from "vue";

interface Column {
  key: string;
  label: string;
  type: "temporal" | "number" | "text";
}

interface AiQueryResponse {
  title: string;
  description: string;
  columns: Column[];
  rows: Record<string, string | number | null>[];
  chart: {
    x_field: string;
    y_field: string;
    reason: string;
    compatible_x_fields: Column[];
    compatible_y_fields: Column[];
  };
}

const API_BASE_URL = "http://localhost:8000";

const prompt = ref(
  "Voglio vedere quanto sono cresciute le vendite in base al numero di venditori assunti nel tempo",
);

const loading = ref(false);
const error = ref("");
const result = ref<AiQueryResponse | null>(null);

const selectedX = ref("");
const selectedY = ref("");

async function submitPrompt() {
  // Avvia una nuova richiesta: resetta stato errore/risultato precedente.
  error.value = "";
  result.value = null;

  if (!prompt.value.trim()) {
    error.value = "Inserisci una richiesta da analizzare.";
    return;
  }

  loading.value = true;

  try {
    const response = await fetch(`${API_BASE_URL}/ai/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: prompt.value,
      }),
    });

    if (!response.ok) {
      const errorBody = await response.json();
      throw new Error(
        errorBody.detail || "Errore durante l’analisi della richiesta.",
      );
    }

    const data: AiQueryResponse = await response.json();

    result.value = data;
    selectedX.value = data.chart.x_field;
    selectedY.value = data.chart.y_field;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Errore imprevisto.";
  } finally {
    loading.value = false;
  }
}

// Deriva i punti del grafico dalla risposta tabellare usando gli assi selezionati.
const chartPoints = computed(() => {
  if (!result.value || !selectedX.value || !selectedY.value) {
    return [];
  }

  return result.value.rows
    .map((row) => ({
      x: row[selectedX.value],
      y: Number(row[selectedY.value] ?? 0),
      label: String(row[selectedX.value] ?? ""),
    }))
    .filter(
      (point) =>
        point.x !== null && point.x !== undefined && !Number.isNaN(point.y),
    );
});

// Calcola il massimo asse Y per normalizzare l'altezza delle barre.
const maxY = computed(() => {
  if (chartPoints.value.length === 0) return 0;
  return Math.max(...chartPoints.value.map((point) => point.y));
});

function getBarHeight(value: number) {
  // Mantiene una altezza minima visiva anche per valori piccoli o nulli.
  if (maxY.value === 0) return 0;
  return Math.max(8, (value / maxY.value) * 220);
}

function getColumnLabel(key: string) {
  // Risolve la label umana di una colonna usando i metadati backend.
  return (
    result.value?.columns.find((column) => column.key === key)?.label ?? key
  );
}

function formatValue(value: string | number | null) {
  // Uniforma il rendering dei valori in tabella e grafico.
  if (value === null || value === undefined) return "-";

  if (typeof value === "number") {
    return new Intl.NumberFormat("it-IT", {
      maximumFractionDigits: 0,
    }).format(value);
  }

  return value;
}
</script>

<template>
  <main class="page">
    <section class="card">
      <h1>AI Plugin Prototype</h1>

      <p class="muted">
        Scrivi una richiesta sui dati del CRM. Il sistema la interpreta e genera
        una tabella con grafico X/Y.
      </p>

      <form class="form" @submit.prevent="submitPrompt">
        <textarea
          v-model="prompt"
          rows="5"
          placeholder="Esempio: voglio vedere quanto sono cresciute le vendite in base al numero di venditori assunti nel tempo"
        />

        <button type="submit" :disabled="loading">
          {{ loading ? "Analisi in corso..." : "Analizza richiesta" }}
        </button>

        <p v-if="error" class="error">
          {{ error }}
        </p>
      </form>
    </section>

    <section v-if="result" class="card">
      <div class="result-header">
        <div>
          <h2>{{ result.title }}</h2>
          <p class="muted">{{ result.description }}</p>
        </div>
      </div>

      <div v-if="result.rows.length === 0" class="empty">
        Nessun dato trovato per questa richiesta.
      </div>

      <template v-else>
        <div class="chart-controls">
          <label>
            Asse X
            <select v-model="selectedX">
              <option
                v-for="field in result.chart.compatible_x_fields"
                :key="field.key"
                :value="field.key"
              >
                {{ field.label }}
              </option>
            </select>
          </label>

          <label>
            Asse Y
            <select v-model="selectedY">
              <option
                v-for="field in result.chart.compatible_y_fields"
                :key="field.key"
                :value="field.key"
              >
                {{ field.label }}
              </option>
            </select>
          </label>
        </div>

        <p class="reason">
          {{ result.chart.reason }}
        </p>

        <div class="chart">
          <div class="chart-title">
            {{ getColumnLabel(selectedX) }} / {{ getColumnLabel(selectedY) }}
          </div>

          <div class="bars">
            <div
              v-for="point in chartPoints"
              :key="point.label"
              class="bar-item"
            >
              <div class="bar-value">
                {{ formatValue(point.y) }}
              </div>

              <div
                class="bar"
                :style="{ height: `${getBarHeight(point.y)}px` }"
              />

              <div class="bar-label">
                {{ point.label }}
              </div>
            </div>
          </div>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th v-for="column in result.columns" :key="column.key">
                  {{ column.label }}
                </th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="(row, rowIndex) in result.rows" :key="rowIndex">
                <td v-for="column in result.columns" :key="column.key">
                  {{ formatValue(row[column.key]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>
  </main>
</template>

<style>
body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #f5f7fb;
  color: #111827;
}

.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 48px 24px;
}

.card {
  background: white;
  border-radius: 18px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08);
}

h1,
h2 {
  margin-top: 0;
}

.muted {
  color: #6b7280;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

textarea,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 14px;
  font-size: 15px;
  background: white;
}

button {
  align-self: flex-start;
  border: 0;
  border-radius: 999px;
  background: #2563eb;
  color: white;
  padding: 12px 22px;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #dc2626;
  font-weight: 600;
}

.empty {
  padding: 20px;
  background: #f9fafb;
  border-radius: 12px;
  color: #6b7280;
}

.result-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
}

.chart-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin: 28px 0 12px;
}

.chart-controls label {
  font-weight: 700;
  color: #374151;
}

.chart-controls select {
  margin-top: 8px;
}

.reason {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e3a8a;
  padding: 14px;
  border-radius: 12px;
}

.chart {
  margin-top: 24px;
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow-x: auto;
}

.chart-title {
  font-weight: 800;
  margin-bottom: 24px;
}

.bars {
  min-height: 300px;
  display: flex;
  align-items: end;
  gap: 16px;
}

.bar-item {
  min-width: 70px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: end;
}

.bar-value {
  font-size: 12px;
  color: #374151;
  margin-bottom: 8px;
}

.bar {
  width: 38px;
  background: #2563eb;
  border-radius: 10px 10px 0 0;
}

.bar-label {
  margin-top: 10px;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.table-wrapper {
  overflow-x: auto;
  margin-top: 32px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  text-align: left;
  background: #f9fafb;
  color: #374151;
}

th,
td {
  padding: 14px;
  border-bottom: 1px solid #e5e7eb;
}

@media (max-width: 700px) {
  .chart-controls {
    grid-template-columns: 1fr;
  }
}
</style>
