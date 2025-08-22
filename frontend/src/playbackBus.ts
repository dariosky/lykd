// Simple pub/sub bus to push immediate playback updates to MiniPlayer
// Events: 'played' when a track is explicitly started from UI

export type PlayedEvent = {
  id: string;
  name: string;
  artists: string[];
  albumImage: string | null;
  durationMs: number;
};

export type PlaybackEventMap = {
  played: PlayedEvent;
};

type Handler<T> = (payload: T) => void;

const handlers: {
  [K in keyof PlaybackEventMap]: Handler<PlaybackEventMap[K]>[];
} = {
  played: [],
};

export function on<K extends keyof PlaybackEventMap>(
  evt: K,
  handler: Handler<PlaybackEventMap[K]>,
): () => void {
  const list = handlers[evt];
  list.push(handler as any);
  return () => {
    const idx = list.indexOf(handler as any);
    if (idx >= 0) list.splice(idx, 1);
  };
}

export function emit<K extends keyof PlaybackEventMap>(
  evt: K,
  payload: PlaybackEventMap[K],
) {
  handlers[evt].forEach((h) => h(payload as any));
}
