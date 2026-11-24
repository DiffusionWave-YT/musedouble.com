export type Counts = { queued: number; running: number; succeeded: number; failed: number; canceled: number };

export type Member = {
  id: string;
  username: string;
  email: string | null;
  name: string;
  role: "admin" | "member";
  active: boolean;
  can_generate: boolean;
  credits: number;
  created_at: string;
  last_generation: string | null;
  generations: Counts;
};

export type MemberDetail = Member & { ledger: { id: number; delta: number; reason: string; created_at: string }[] };

export type Generation = {
  id: string;
  user: { id: string; username: string; name: string };
  model_name: string;
  workflow_id: string;
  mode: string;
  status: string;
  progress: number;
  cost: number;
  attempts: number;
  gpu: string | null;
  error: string | null;
  prompt: string;
  ratio: string | null;
  batch: number | null;
  seed: number | null;
  has_reference: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  outputs: { id: string; mime: string; bytes: number }[];
};

export type GenerationPage = { items: Generation[]; total: number; next_offset: number | null };

export type WorkflowSlot = {
  mode: string;
  label: string;
  workflow: { id: string; name: string; cost: number; enabled: boolean; version: number; sha256: string; updated_at: string } | null;
};

export const when = (value: string | null) => (value ? new Date(value).toLocaleString("es", { dateStyle: "medium", timeStyle: "short" }) : "—");

export const reasons: Record<string, string> = { admin_grant: "Asignación del administrador", job: "Generación", refund: "Reembolso" };
