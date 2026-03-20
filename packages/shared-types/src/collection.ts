export enum IntType {
  SOCMINT = 'SOCMINT',
  GEOINT = 'GEOINT',
  SIGINT = 'SIGINT',
  CYBINT = 'CYBINT',
}

export enum AdmiraltyReliability {
  A = 'A', // Completely reliable
  B = 'B', // Usually reliable
  C = 'C', // Fairly reliable
  D = 'D', // Not usually reliable
  E = 'E', // Unreliable
  F = 'F', // Reliability cannot be judged
}

export enum AdmiraltyCredibility {
  One = '1',   // Confirmed by other sources
  Two = '2',   // Probably true
  Three = '3', // Possibly true
  Four = '4',  // Doubtful
  Five = '5',  // Improbable
  Six = '6',   // Truth cannot be judged
}

export interface CollectionJob {
  id: string;
  intType: IntType;
  query: string;
  scanType: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  resultCount: number;
  error: string | null;
  createdAt: string;
  completedAt: string | null;
}

export interface CollectionRequest {
  query: string;
  scanType: string;
  options?: Record<string, unknown>;
}
